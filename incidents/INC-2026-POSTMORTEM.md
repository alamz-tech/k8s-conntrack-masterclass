# Incident Post-Mortem: INC-2026-1024
## Silent Checkout Transaction Drop During Cyber Monday Traffic Surge

| Field | Details |
| :--- | :--- |
| **Incident ID** | `INC-2026-1024` |
| **Severity** | **SEV-1 (Critical Revenue-Impacting)** |
| **Impacted Service** | `checkout-service`, Payment Gateway Ingress |
| **Duration** | 42 minutes (02:14 UTC – 02:56 UTC) |
| **Incident Commander** | Lead Site Reliability Engineer |
| **Root Cause** | Linux Netfilter Conntrack Table Saturation via Kubernetes `ndots:5` DNS Amplification |

---

## Executive Summary

On October 24, 2026, at 02:14 UTC, a Cyber Monday promotional flash-sale triggered an automated Horizontal Pod Autoscaling (HPA) event, scaling `checkout-service` from 10 to 80 pods. Within 90 seconds of scaling, customer payment transactions began failing intermittently with connection timeouts.

The incident was exacerbated by a **silent failure mode**: Kubernetes dashboards, Datadog cluster health, and CoreDNS metrics remained **100% green**. Kubelet liveness probes continued to pass because health checks targeted `127.0.0.1:8080` over TCP loopback, which bypassed connection tracking allocation.

At 02:34 UTC, the on-call SRE identified that the worker nodes hosting the checkout pods had saturated their Linux Netfilter connection tracking table (`nf_conntrack`), causing the Linux kernel to silently drop outgoing UDP DNS queries before they ever left the node.

An emergency node-level kernel expansion mitigated the drops at 02:41 UTC. Permanent remediation via Helm `values-patched.yaml` (trailing dots and `ndots:2`) and fleet-wide **NodeLocal DNSCache** deployment resolved the incident completely.

---

## Detailed Timeline (UTC)

- **02:00**: Marketing campaign launches. Incoming checkout traffic increases by 650%.
- **02:14**: HPA scales `checkout-service` to 80 pods. Approximately 25 pods land on worker node `ip-10-0-4-12.ec2.internal`.
- **02:16**: PagerDuty alert fires: `PaymentGatewaySuccessRateDropped (< 85%)`.
- **02:19**: On-Call SRE inspects Kubernetes dashboard:
  - Pods are `1/1 Running`, 0 restarts.
  - CoreDNS CPU utilization is low (~7%).
  - CoreDNS query rate shows normal throughput.
- **02:24**: SRE executes `kubectl logs` on checkout pods, finding thousands of `socket.gaierror: [Errno -3] Temporary failure in name resolution (EAI_AGAIN)` errors attempting to reach `api.stripe.com` and `postgres.internal`.
- **02:29**: SRE runs `tcpdump` on the worker node and observes parallel A and AAAA queries traversing all 4 cluster search domains for every checkout transaction (10 UDP queries per attempt).
- **02:34**: SRE inspects `/proc/sys/net/netfilter/nf_conntrack_count` on the worker node. Table is at **100% capacity** (262,144 / 262,144).
- **02:36**: `dmesg -T` on the node confirms: `nf_conntrack: table full, dropping packet`.
- **02:41 (Mitigation 1)**: Emergency hotfix applied via privileged node session: `sysctl -w net.netfilter.nf_conntrack_max=1048576` and `conntrack -F`. Conntrack saturation drops to 24%; checkout error rates plummet to zero.
- **03:15 (Mitigation 2)**: SRE deploys PR #1402: Adds trailing dot (`api.stripe.com.`), sets `dnsConfig.options.ndots: 2`, and enables socket connection pooling.
- **03:50 (Strategic Fix)**: Platform team deploys `NodeLocal DNSCache` across all production node pools.
- **04:00**: All alerts cleared. Incident officially closed.

---

## Technical Root Cause Analysis (5 Whys)

1. **Why did checkout transactions fail?**  
   The application could not resolve DNS for `api.stripe.com` and `postgres.internal`, timing out during connection setup.

2. **Why was DNS failing if CoreDNS was healthy?**  
   The DNS queries were dropped by the **worker node's Linux kernel** before reaching the network interface. CoreDNS never received them.

3. **Why did the worker node kernel drop DNS queries?**  
   The node's `nf_conntrack` table exceeded its maximum limit. Netfilter's `nf_conntrack_alloc()` failed, and the kernel dropped all new UDP packets.

4. **Why was the conntrack table flooded with UDP entries?**  
   Because the checkout service used short hostnames (`api.stripe.com` has 2 dots; `postgres.internal` has 1 dot). Under default Kubernetes `ndots:5`, `glibc` sent parallel A and AAAA queries to 4 search domains sequentially, generating 10 UDP queries per checkout. With 80 pods unpooled and retrying without backoff, the node generated >25,000 UDP state entries per second, while Linux retained UDP tuples for 30 seconds.

5. **Why did Kubernetes health checks fail to detect this?**  
   The liveness probe queried `http://localhost:8080/healthz` over TCP loopback. Loopback and established TCP connections bypassed connection tracking table allocation, so the pods stayed green.

---

## Action Items & Preventive Measures

| Item | Description | Type | Owner | Status |
| :--- | :--- | :--- | :--- | :--- |
| **ACT-1** | Deploy NodeLocal DNSCache across all Kubernetes clusters (`169.254.20.10`) with `force_tcp` upstream. | Platform / Infra | Platform Team | **Done** |
| **ACT-2** | Update base Helm chart templates to set `dnsConfig.options.ndots: 2` and `single-request-reopen`. | Architecture | Platform Team | **Done** |
| **ACT-3** | Audit all microservice configurations to enforce trailing dots (`.`) on external endpoints. | Application | App Teams | In Progress |
| **ACT-4** | Deploy Prometheus alerting rule `NodeConntrackTableNearlyFull` (>85%) with PagerDuty integration. | Monitoring | SRE Team | **Done** |
| **ACT-5** | Refactor application HTTP/DB clients to enforce connection pooling and Full Jitter exponential backoff. | Architecture | Core Services | In Progress |
