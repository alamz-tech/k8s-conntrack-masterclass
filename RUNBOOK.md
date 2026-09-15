# Speaker Guide & Runbook: Live Incident Triage
## "Linux Conntrack Exhaustion & Kubernetes DNS Loops"

**Audience:** Staff Infrastructure Engineers, SREs, Platform Architects  
**Format:** Live 60-Minute Interactive Systems Engineering Masterclass  
**Objective:** Reproduce, diagnose, and permanently remediate silent network packet loss caused by Kubernetes `ndots:5` DNS amplification and Linux Netfilter connection tracking table saturation.

---

## 1. Terminal Layout Setup (tmux / 3-Pane View)

Set up your screen with 3 panes before going live:

```
+------------------------------------------+------------------------------------------+
| PANE 1 (Top-Left): Telemetry Gauge       | PANE 3 (Right): SRE Shell / Control      |
| $ bash telemetry/watch-conntrack.sh      |                                          |
|                                          | $ kubectl get pods -n triage-lab -w      |
| [Conntrack Saturation Bar & Drops]       | $ kubectl logs ...                       |
+------------------------------------------+ $ git diff ...                           |
| PANE 2 (Bottom-Left): Packet Inspector   | $ kubectl apply -f ...                   |
| $ bash telemetry/capture-dns-amplification.sh                                       |
|                                          |                                          |
| [10x DNS Query Multiplier Stream]        |                                          |
+------------------------------------------+------------------------------------------+
```

### Fast tmux Setup Command
```bash
tmux new-session -s masterclass \; \
  split-window -h \; \
  split-window -v -t 0 \; \
  select-pane -t 2
```

---

## 2. Minute-by-Minute Masterclass Timeline

### [00:00 – 08:00] Act I: The PagerDuty Storm & The Deceptive Green Dashboard

#### Speaker Narrative
> "It's 2:15 AM on Cyber Monday. Our payment gateway batch processors are throwing intermittent connection timeouts to the internal PostgreSQL cluster (`db.internal`). Customers are reporting aborted transactions.
> 
> You jump into the Kubernetes dashboard. What do you see?
> - The pods are **1/1 Running**.
> - Kubelet liveness probes are **100% green**.
> - CoreDNS pod CPU is sitting calmly at **6%**.
> - Datadog shows healthy nodes.
> 
> Why are customer transactions dropping on the floor while our monitoring says everything is perfectly healthy? Welcome to the silent killer: **Linux Netfilter Conntrack Exhaustion**."

#### Live Terminal Actions (Pane 3)
```bash
# Verify cluster baseline
kubectl get nodes -o wide
kubectl get pods -A

# Check that netfilter limit was primed down to 2048
bash setup/set-kernel-limits.sh 2048
```

---

### [08:00 – 18:00] Act II: Triggering the Blast Radius

#### Speaker Narrative
> "Let's bring up our mock database service and start our high-throughput payment worker deployment. Notice how the worker makes calls to `db.internal`.
> 
> Watch Pane 1 closely. As soon as the workers start, observe the netfilter conntrack counter."

#### Live Terminal Actions (Pane 3)
```bash
# 1. Deploy the mock upstream database and configure CoreDNS hosts entry
kubectl apply -f manifests/broken/01-mock-upstream.yaml

# Wait for mock-db to become ready
kubectl wait --for=condition=Available deployment/mock-db -n triage-lab --timeout=30s

# 2. Start the broken client deployment
kubectl apply -f manifests/broken/02-broken-client.yaml

# 3. Follow the client pod logs
kubectl logs -n triage-lab -l app=payment-worker --tail=50 -f
```

#### What Audience Sees
- Client logs start screaming:
  ```
  DNS RESOLUTION FAILURE for 'db.internal': [Errno -3] Temporary failure in name resolution
  ```
- Yet `kubectl get pods -n triage-lab` shows:
  ```
  NAME                              READY   STATUS    RESTARTS   AGE
  payment-worker-7df947c66d-abcde   1/1     Running   0          45s
  ```

#### Teaching Moment: Why is Kubelet Green?
Explain that the liveness probe hits `127.0.0.1:8080` over TCP loopback. Loopback traffic does not enter the netfilter conntrack table in this configuration, and TCP established connections bypass connection table allocation! The pod's application logic is blind and dead, but Kubernetes considers it healthy.

---

### [18:00 – 32:00] Act III: The Forensic Triage (Kernel & Network Layer)

#### Live Terminal Actions (Panes 1 & 2)
```bash
# In Pane 1 (Top Left):
bash telemetry/watch-conntrack.sh

# In Pane 2 (Bottom Left):
bash telemetry/capture-dns-amplification.sh
```

#### Speaker Narrative & Packet Breakdown
> "Look at Pane 1. Our conntrack table count skyrocketed from 84 entries to **2048 / 2048 (100% SATURATED)**.
> 
> Look at the counters at the bottom: `drop=1492`, `insert_failed=1492`. The Linux kernel is literally throwing UDP packets into the void.
> 
> Now look at Pane 2. Why are we exhausting 2,048 state entries so fast with only 4 client pods?
> Watch the packet inspector. For every single payment connection attempt to `db.internal`, count the queries:
> 
> 1. `db.internal.triage-lab.svc.cluster.local.` -> [A query] + [AAAA query] (NXDOMAIN)
> 2. `db.internal.svc.cluster.local.` -> [A query] + [AAAA query] (NXDOMAIN)
> 3. `db.internal.cluster.local.` -> [A query] + [AAAA query] (NXDOMAIN)
> 4. `db.internal.` -> [A query] + [AAAA query] (NOERROR)
> 
> That is **8 to 10 UDP packets** for a SINGLE connection attempt!
> Because glibc resolves A and AAAA in parallel without waiting, and Kubernetes injects `options ndots:5` by default!"

#### Inspect Kernel Ring Buffer (Pane 3)
```bash
bash telemetry/monitor-kernel-drops.sh
```
Audience sees:
```
🚨 KERNEL DROP DETECTED: [nf_conntrack: table full, dropping packet]
```

#### Deep Dive Concept Slide / Blackboard Notes
- **`nf_conntrack` memory allocation:** Each UDP connection creates a `struct nf_conn` in kernel memory.
- **UDP Timeout:** UDP is stateless. The kernel must keep an entry alive for `nf_conntrack_udp_timeout=30s` just in case a reply packet arrives.
- **The Math:** `100 threads * 10 queries/attempt * (1 retry / 500ms) = 2,000 UDP conntrack tuples every second!`
- Within 1.5 seconds, any worker node conntrack table is completely saturated.

---

### [32:00 – 46:00] Act IV: Tactical Workload Remediation (The 3-Tier Fix)

#### Speaker Narrative
> "Many teams respond to this by scaling up CoreDNS from 2 replicas to 20 replicas. Does that help?
> **No.** CoreDNS isn't dropping the packets. The packets never leave the worker node! The worker node's kernel dropped them at netfilter ingress before they ever touched the wire.
> 
> Let's look at the proper three-tier application fix."

#### Live Terminal Actions (Pane 3)
```bash
# Compare the broken manifest against the patched manifest
diff -u manifests/broken/02-broken-client.yaml manifests/fixed/01-patched-client.yaml
```

Walk the audience through the 3 modifications:
1. **Trailing Dot (`TARGET_HOST: "db.internal."`):** Tells `glibc` this is an absolute FQDN. It skips all 4 search paths and queries root immediately. Query multiplier drops from 10x to 1x.
2. **`dnsConfig` override:**
   ```yaml
   dnsConfig:
     options:
       - name: ndots
         value: "2"
       - name: single-request-reopen
   ```
   Lowers `ndots` to 2. Prevents domain search walking for non-cluster hosts. `single-request-reopen` prevents glibc UDP port reuse races.
3. **Application Layer Resilience (`MODE="patched"`):**
   Connection pooling + Full Jitter exponential backoff.

#### Apply the Patched Workload (Pane 3)
```bash
kubectl apply -f manifests/fixed/01-patched-client.yaml
kubectl rollout status deployment/payment-worker -n triage-lab
```

#### What Audience Sees in Telemetry (Pane 1 & Pane 2)
- In Pane 1: Conntrack count immediately plummets from 2048 (100%) down to **120 - 180 entries (6%)**.
- In Pane 2: The packet storm halts; only occasional clean, single-query FQDN lookups appear.
- In Pane 3: Pod logs show **0 DNS errors**, sub-millisecond lookups, and steady transaction throughput!

---

### [46:00 – 55:00] Act V: Strategic Cluster Architecture: NodeLocal DNSCache

#### Speaker Narrative
> "Patching individual application manifests is great, but in an organization with 400 microservices, you cannot rely on every software engineer to remember trailing dots and custom `dnsConfig`.
> 
> As Staff Engineers, we need an **infrastructure-level structural guardrail**.
> That guardrail is **NodeLocal DNSCache**."

#### How NodeLocal DNS Fixes the Kernel Bottleneck
1. Runs as a DaemonSet on link-local IP `169.254.20.10`.
2. Pods talk to the local daemon over the local node interface.
3. Cache hits never leave the node.
4. Cache misses are forwarded upstream to CoreDNS over **persistent TCP connections** (`force_tcp`).
5. **Netfilter conntrack is completely bypassed** for upstream cluster DNS traffic!

#### Deploy NodeLocal DNS (Pane 3)
```bash
kubectl apply -f manifests/fixed/02-nodelocaldns.yaml
kubectl rollout status daemonset/node-local-dns -n kube-system --timeout=60s
```

Verify NodeLocal DNS is listening on the worker node:
```bash
docker exec conntrack-lab-worker ss -lunp | grep ":53"
```

---

### [55:00 – 60:00] Act VI: Wrap-Up & Post-Mortem Action Items

#### The Golden Rules for Production Kubernetes
1. **Never trust local loopback probes alone:** Combine TCP liveness with end-to-end synthetic network health.
2. **Qualify your external hostnames:** Always use a trailing dot (e.g. `api.stripe.com.` or `db.internal.`) in high-throughput backend services.
3. **Tune `ndots` to 2:** In production helm charts, set `ndots: 2` unless your architecture relies heavily on cross-namespace unqualified lookups.
4. **Deploy NodeLocal DNSCache everywhere:** Mandatory on any cluster running >50 nodes or high-concurrency workloads.
5. **Monitor Netfilter Conntrack in Prometheus:**
   Alert on `node_nf_conntrack_entries / node_nf_conntrack_entries_limit > 0.75`.

---

## 3. Emergency Rescue & Live Demo Reset Guide

If the cluster or demo stalls unexpectedly during the live presentation:

### 1. Instant Conntrack Table Flush
If worker node drops packets and you need an instant reset without restarting:
```bash
docker exec conntrack-lab-worker conntrack -F
```

### 2. Reset Worker Node Kernel Limit
If you want to restore standard high limits immediately:
```bash
docker exec conntrack-lab-worker sysctl -w net.netfilter.nf_conntrack_max=262144
```

### 3. Quick Namespace Nuke & Re-apply
```bash
kubectl delete namespace triage-lab --wait=false
kubectl create namespace triage-lab
kubectl apply -f manifests/broken/01-mock-upstream.yaml
```

### 4. Full Hard Reset (Takes ~45 seconds)
```bash
bash setup/start-cluster.sh
bash setup/set-kernel-limits.sh 2048
```
