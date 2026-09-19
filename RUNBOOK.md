# SRE Incident Runbook: Linux Netfilter Conntrack Exhaustion

**Alert Name:** `NodeConntrackTableNearlyFull` / `NodeConntrackTableFillingFast`  
**Severity:** SEV-1 (Critical) / SEV-2 (High)  
**PromQL Expression:** `(node_nf_conntrack_entries / node_nf_conntrack_entries_limit) > 0.85`  
**Service Impact:** Silent UDP packet drops, sporadic DNS timeouts (`EAI_AGAIN`), payment/egress request failures.

---

## 1. Overview & Failure Mode

When a worker node's Linux Netfilter connection tracking table (`nf_conntrack`) reaches capacity, the kernel fails `nf_conntrack_alloc()` and **silently drops subsequent UDP packets**. 

### ⚠️ Deceptive Green Health Signal
* **Kubelet Status Lies:** Pods remain `1/1 Running`. Kubelet liveness probes hitting `127.0.0.1:8080/healthz` over TCP loopback bypass connection tracking allocation.
* **CoreDNS Looks Healthy:** CoreDNS CPU and query metrics remain low because dropped queries are discarded at the worker node's network layer before ever reaching the wire or CoreDNS pods.

---

## 2. Immediate Triage (0 - 5 Minutes)

### Step 2.1: Identify Affected Worker Nodes
```bash
# Find nodes reporting conntrack saturation via Prometheus / kubectl
kubectl get nodes -o wide
```

### Step 2.2: Inspect Conntrack Table Capacity on the Degraded Node
Access the degraded worker node (via SSH, node admin session, or debug container) and inspect table utilization:
```bash
# Check current entries vs maximum capacity
echo "Current: $(cat /proc/sys/net/netfilter/nf_conntrack_count)"
echo "Limit:   $(cat /proc/sys/net/netfilter/nf_conntrack_max)"

# Inspect drop and failure counters
conntrack -S
```
*If `drop=` or `insert_failed=` counters are incrementing, the kernel is actively dropping packets.*

### Step 2.3: Confirm Kernel Ring Buffer Drops
```bash
dmesg -T | grep -E "nf_conntrack: table full, dropping packet|conntrack"
```

---

## 3. Emergency Mitigation (Stop the Bleeding)

When customer traffic is dropping, **do not wait for code changes or CI/CD pipelines**. Apply immediate node-level mitigation.

### Action 3.1: Dynamically Expand the Conntrack Table Limit
Double or quadruple the table capacity in runtime:
```bash
# Expand limit to 1,048,576 (or 65,536 in constrained/lab environments)
sysctl -w net.netfilter.nf_conntrack_max=1048576
```

### Action 3.2: Flush Dead / Stale UDP Tracking Tuples
Linux retains unreplied UDP tracking state for 30 seconds (`nf_conntrack_udp_timeout=30`). Flush stale entries to recover table space instantly:
```bash
conntrack -F
```

### Action 3.3: Verify Immediate Recovery
```bash
# Confirm saturation percentage dropped below 50%
echo "$(( $(cat /proc/sys/net/netfilter/nf_conntrack_count) * 100 / $(cat /proc/sys/net/netfilter/nf_conntrack_max) ))% utilized"
```
*Check application APM / logs to verify `EAI_AGAIN` error rates return to zero.*

---

## 4. Root Cause Forensics (5 - 20 Minutes)

Once the incident is stabilized, identify what flooded the connection tracking table:

### Step 4.1: Sniff DNS UDP Traffic on the Degraded Node
Run `tcpdump` to detect DNS amplification loops:
```bash
tcpdump -nn -l -i any udp port 53
```
*Check for the **Kubernetes `ndots:5` search domain walk**:*
1. `<host>.<namespace>.svc.cluster.local.` (A + AAAA) $\rightarrow$ NXDOMAIN
2. `<host>.svc.cluster.local.` (A + AAAA) $\rightarrow$ NXDOMAIN
3. `<host>.cluster.local.` (A + AAAA) $\rightarrow$ NXDOMAIN
4. `<host>.` (A + AAAA) $\rightarrow$ Resolved

*If external or non-cluster domains (e.g. `api.stripe.com`, `postgres.internal`) are querying cluster search paths, the application is suffering from `ndots:5` amplification (10 UDP queries per connection).*

### Step 4.2: Inspect Application Socket Lifecycle
Check if client workloads are creating fresh sockets per request instead of reusing pooled connections:
```bash
# Check open sockets by pod namespace
ss -s
ss -tuna | grep ":53\|:5432\|:443" | wc -l
```

---

## 5. Permanent Remediation

### Tier 1: Workload Level (Application Pull Request)
1. **Append Trailing Dots to External Endpoints:**
   Update application config to treat external endpoints as absolute FQDNs:
   ```yaml
   # deploy/helm/checkout-service/values.yaml
   config:
     stripeHost: "api.stripe.com."       # Trailing dot skips 4 cluster search domains
     postgresHost: "postgres.internal."  # Trailing dot skips 4 cluster search domains
   ```
2. **Override `ndots: 2` in Pod Spec:**
   ```yaml
   dnsPolicy: ClusterFirst
   dnsConfig:
     options:
       - name: ndots
         value: "2"
       - name: single-request-reopen
       - name: timeout
         value: "1"
       - name: attempts
         value: "2"
   ```
3. **Enforce Connection Pooling & Jitter:**
   Ensure client HTTP/DB clients reuse sockets (e.g. `requests.Session()`, connection pools) and implement exponential backoff with Full Jitter.

### Tier 2: Platform Level (Fleet-Wide Guardrail)
Deploy **NodeLocal DNSCache** as a mandatory DaemonSet across all node pools:
```bash
kubectl apply -f platform/nodelocaldns/nodelocaldns.yaml
```
* **Architecture:** Pods query the node-local link IP `169.254.20.10:53`.
* **Conntrack Bypass:** Upstream cache misses are forwarded to CoreDNS over **persistent TCP connections (`force_tcp`)**, completely eliminating Netfilter UDP connection tracking churn across worker nodes.

---

## 6. Verification Checklist

- [ ] Node conntrack utilization is stable under 50%: `(node_nf_conntrack_entries / node_nf_conntrack_entries_limit) < 0.50`
- [ ] Kernel drop counters stopped incrementing: `conntrack -S | grep "drop=0"`
- [ ] Application DNS resolution latency p99 is under 5ms
- [ ] NodeLocal DNSCache DaemonSet is running `Ready` on all nodes
- [ ] Prometheus alert `NodeConntrackTableNearlyFull` is resolved
