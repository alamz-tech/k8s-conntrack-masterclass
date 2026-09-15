# Speaker Guide & Runbook: Live Incident Triage
## "Linux Conntrack Exhaustion & Kubernetes DNS Loops"

**Audience:** Senior & Staff Infrastructure Engineers, SREs, Platform Architects  
**Format:** Live 60-Minute Interactive Systems Engineering Masterclass & Incident Drill  
**Scenario:** SEV-1 Outage on Cyber Monday: Silent checkout payment failures under auto-scaling surge while Kubernetes dashboards remain deceptively 100% green.

---

## 1. Terminal Layout Setup (3-Pane View)

Set up a 3-pane terminal (or tmux session) before presenting:

```
+------------------------------------------+------------------------------------------+
| PANE 1 (Top-Left): Telemetry Gauge       | PANE 3 (Right): SRE Operator / Control   |
| $ bash telemetry/watch-conntrack.sh      |                                          |
|                                          | $ bash incidents/drills/01-baseline...   |
| [Conntrack Saturation Bar & Drops]       | $ bash incidents/drills/02-flash-sale... |
+------------------------------------------+ $ kubectl logs ...                       |
| PANE 2 (Bottom-Left): Packet Inspector   | $ diff -u deploy/helm/checkout-service/  |
| $ bash telemetry/capture-dns-amplification.sh                                       |
|                                          | $ kubectl apply -f ...                   |
| [10x DNS Query Multiplier Stream]        |                                          |
+------------------------------------------+------------------------------------------+
```

### Quick tmux Session Launcher
```bash
tmux new-session -s masterclass \; \
  split-window -h \; \
  split-window -v -t 0 \; \
  select-pane -t 2
```

---

## 2. Minute-by-Minute Masterclass Script

### [00:00 – 08:00] Act I: The PagerDuty Storm & The Deceptive Green Dashboard

#### Speaker Narrative
> "It's 02:15 AM on Cyber Monday. Marketing just initiated a massive flash-sale push.
> PagerDuty rings: `PaymentGatewaySuccessRateDropped (< 85%)`. Customers are screaming on social media that checkouts are timing out.
>
> You jump onto the Kubernetes dashboard. What do you see?
> - `checkout-service` pods are **1/1 Running** with 0 restarts.
> - Kubelet liveness probes are **100% green**.
> - CoreDNS CPU is sitting calmly at **6%**.
> - Datadog says our node memory and CPU are completely fine.
>
> Why is money failing to enter our bank account while our monitoring says the cluster is pristine? Welcome to the silent killer: **Linux Netfilter Conntrack Exhaustion**."

#### Live Terminal Actions (Pane 3)
```bash
# Verify cluster status
kubectl get nodes -o wide

# Ensure node kernel limit is primed to local lab ratio (2048 entries)
bash setup/set-kernel-limits.sh 2048

# Establish normal morning baseline
bash incidents/drills/01-baseline-traffic.sh
```

---

### [08:00 – 18:00] Act II: Triggering the Blast Radius (The Flash Sale)

#### Speaker Narrative
> "Notice our checkout service in Pane 3. At 2 replicas, traffic is steady, latency is sub-10ms, and conntrack in Pane 1 is sitting at a comfortable 140 / 2048 entries (7%).
> 
> Now, let's trigger the Cyber Monday traffic surge. Our Horizontal Pod Autoscaler detects queue depth and scales the deployment from 2 to 6 replicas."

#### Live Terminal Actions (Pane 3)
```bash
# In Pane 1 (Top Left):
bash telemetry/watch-conntrack.sh

# In Pane 2 (Bottom Left):
bash telemetry/capture-dns-amplification.sh

# In Pane 3 (Right): Trigger the surge drill
bash incidents/drills/02-flash-sale-surge.sh

# Follow application logs
kubectl logs -n checkout-prod -l app=checkout-service -f --tail=30
```

#### What Audience Sees
- Checkout logs start printing:
  ```
  TRANSACTION ABORTED (DNS FAILURE): [Errno -3] Temporary failure in name resolution -> Tight loop retry
  ```
- Yet `kubectl get pods -n checkout-prod` remains **1/1 Running**!
- In Pane 1, the conntrack gauge hits **100% SATURATED (2048/2048)** with rising `drop=` counters!

#### Teaching Moment: Why Did Kubelet Stay Green?
Point out that the liveness probe queries `127.0.0.1:8080/healthz` over TCP loopback. Loopback and established TCP connections bypass the netfilter table allocation. The pod's application logic is dead, but Kubernetes considers it healthy!

---

### [18:00 – 32:00] Act III: The Forensic Triage (Kernel & Network Layer)

#### Speaker Narrative
> "Let's diagnose why the table saturated with only 6 pods.
> Look at Pane 2. Our checkout service connects to:
> 1. Internal PostgreSQL: `postgres.internal` (1 dot)
> 2. Stripe Payment Gateway: `api.stripe.com` (2 dots)
>
> In Kubernetes, `/etc/resolv.conf` defaults to `options ndots:5`.
> Because both hostnames have fewer than 5 dots, glibc sequentially walks:
>   1. `<host>.checkout-prod.svc.cluster.local.` -> [A query] + [AAAA query] (NXDOMAIN)
>   2. `<host>.svc.cluster.local.`              -> [A query] + [AAAA query] (NXDOMAIN)
>   3. `<host>.cluster.local.`                  -> [A query] + [AAAA query] (NXDOMAIN)
>   4. `<host>.`                                -> [A query] + [AAAA query] (Resolved)
>
> That's **10 UDP transactions per connection attempt**!
> And because developers used standard socket calls without connection pooling, every single transaction opens new sockets.
>
> In Linux, UDP is connectionless, so the kernel keeps each tuple alive for 30 seconds (`nf_conntrack_udp_timeout=30`).
> 120 worker threads $\times$ 10 queries $\times$ 30 seconds = **36,000 concurrent state entries needed**.
> Once the table is full, the Linux kernel drops all new UDP packets right here on the worker node!"

#### Verify Kernel Drops (Pane 3)
```bash
bash telemetry/monitor-kernel-drops.sh
```
Audience sees:
```
🚨 KERNEL DROP DETECTED: [nf_conntrack: table full, dropping packet]
```

---

### [32:00 – 42:00] Act IV: The 02:30 AM On-Call Emergency Hotfix

#### Speaker Narrative
> "It's 02:30 AM. You are the on-call SRE. You cannot tell your VP of Engineering: 'Wait 45 minutes while I write code, submit a PR, run tests, and do a canary deploy.'
> 
> You need to **stop the bleeding immediately**.
> What do you do? You execute the 02:30 AM hotfix."

#### Live Terminal Actions (Pane 3)
```bash
bash incidents/drills/03-emergency-hotfix.sh
```

#### What Audience Sees
- Dynamically expands `net.netfilter.nf_conntrack_max` to 65536 and flushes stale entries (`conntrack -F`).
- Instantly, Pane 1 drops to 4% saturation.
- Checkout logs immediately recover: `0 DNS errors`, transactions succeed!
- Explain: *"This is a temporary bandage that buys us time to implement the real platform fixes."*

---

### [42:00 – 52:00] Act V: The GitOps Pull Request & Platform Strategic Fix

#### 1. The Workload Pull Request (PR #1402)
Show the diff between standard and remediated configuration:
```bash
diff -u deploy/helm/checkout-service/values.yaml deploy/helm/checkout-service/values-patched.yaml
```

Walk through the 3 fixes:
1. **Trailing Dots (`api.stripe.com.` & `postgres.internal.`):** Tells glibc this is an absolute FQDN, skipping all 4 search paths immediately (multiplier drops from 10x to 1x).
2. **`dnsConfig` Override:** Lower `ndots: 2` and enable `single-request-reopen`.
3. **Resilient Application Mode:** Persistent connection pooling + Full Jitter exponential backoff.

Apply the patched workload:
```bash
kubectl apply -f deploy/checkout-service-patched.yaml
kubectl rollout status deployment/checkout-service -n checkout-prod
```

#### 2. The Platform Strategic Guardrail (NodeLocal DNSCache)
Deploy NodeLocal DNSCache across the cluster:
```bash
kubectl apply -f platform/nodelocaldns/nodelocaldns.yaml
kubectl rollout status daemonset/node-local-dns -n kube-system --timeout=60s
```

Explain:
> "NodeLocal DNSCache runs on link-local IP `169.254.20.10`. It terminates UDP locally on the node interface, caches responses, and forwards cache misses over **persistent TCP streams** (`force_tcp`) to CoreDNS.
> Netfilter UDP connection tracking churn is completely eliminated across the entire cluster."

---

### [52:00 – 60:00] Act VI: Post-Mortem & Audience Q&A

Review the formal incident post-mortem:
```bash
cat incidents/INC-2026-POSTMORTEM.md
```

#### Key Architecture Takeaways for SREs
1. **Never rely solely on loopback `/healthz` probes:** Combine them with synthetic network probes.
2. **Always append trailing dots to external hostnames in high-throughput services.**
3. **Set `ndots: 2` in your base Helm charts.**
4. **Deploy NodeLocal DNSCache as a mandatory platform standard on all clusters > 50 nodes.**
5. **Set up Prometheus alerts on `(node_nf_conntrack_entries / node_nf_conntrack_entries_limit) > 0.85`.**
