# Live Incident Triage: Linux Conntrack Exhaustion & Kubernetes DNS Loops

> **A production-grade SRE incident reproduction and interactive triage masterclass for senior and staff systems engineers.**

[![Kubernetes](https://img.shields.io/badge/Kubernetes-Kind-326CE5?logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Linux Netfilter](https://img.shields.io/badge/Linux_Kernel-Netfilter_Conntrack-FCC624?logo=linux&logoColor=black)](https://netfilter.org/)
[![Helm 3](https://img.shields.io/badge/Package_Manager-Helm_3-0F1689?logo=helm&logoColor=white)](https://helm.sh/)
[![Prometheus](https://img.shields.io/badge/Monitoring-Prometheus_Alerts-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io/)

---

## 1. Incident Background: The Cyber Monday Outage

When cloud workloads scale rapidly (such as [Tinder's 2019 migration involving 1,000 nodes and 15,000 pods](https://medium.com/tinder-engineering/tinders-move-to-kubernetes-cda2a6372f44) — see their [KubeCon NA 2019 talk](https://www.youtube.com/watch?v=kY-F3R9_Z7o) — or flash-sale retail events), Kubernetes clusters face **silent network packet drops** while dashboards remain deceptively green:

```
                    +--------------------------------------------+
                    |  checkout-service Pod /etc/resolv.conf     |
                    |  nameserver 10.96.0.10                     |
                    |  search checkout-prod.svc.cluster.local    |
                    |         svc.cluster.local                  |
                    |         cluster.local                      |
                    |  options ndots:5                           |
                    +--------------------+-----------------------+
                                         |
                                         | Unqualified Query: "api.stripe.com" (< 5 dots)
                                         v
+-----------------------------------------------------------------------------------------+
| WORKER NODE (Linux Kernel)                                                              |
|                                                                                         |
|   glibc resolver issues parallel A (IPv4) & AAAA (IPv6) queries sequentially:           |
|                                                                                         |
|   [Query 1 & 2]:   api.stripe.com.checkout-prod.svc.cluster.local  ->  NXDOMAIN         |
|   [Query 3 & 4]:   api.stripe.com.svc.cluster.local              ->  NXDOMAIN         |
|   [Query 5 & 6]:   api.stripe.com.cluster.local                  ->  NXDOMAIN         |
|   [Query 7 & 8]:   api.stripe.com.                               ->  10.96.100.200    |
|                                                                                         |
|   = 8 to 10 UDP Transactions per single connection attempt!                             |
|                                                                                         |
|   +---------------------------------------------------------------------------------+   |
|   | Linux Netfilter Connection Tracking Table (nf_conntrack)                        |   |
|   | Capacity: 2048 tuples | UDP Timeout: 30s                                        |   |
|   |                                                                                 |   |
|   | [Tuple 1] src: 10.244.1.5:41201 dst: 10.96.0.10:53 (UNREPLIED, lingers 30s)    |   |
|   | [Tuple 2] src: 10.244.1.5:41202 dst: 10.96.0.10:53 (UNREPLIED, lingers 30s)    |   |
|   | ...                                                                             |   |
|   | [Tuple 2048] === TABLE FULL ===                                                 |   |
|   +---------------------------------------------------------------------------------+   |
|                                     |                                                   |
|                                     v                                                   |
|        🚨 [dmesg: "nf_conntrack: table full, dropping packet"]                          |
|        Subsequent UDP packets dropped silently by kernel at ingress/egress!             |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Production Realities vs. Local Simulation Scaling Math

In production clusters on AWS/GCP, a standard worker node (e.g. `m5.4xlarge`) has 64 GB of RAM, and `nf_conntrack_max` is automatically calculated as:
$$\text{Max Entries} = \frac{\text{RAM (Bytes)}}{16384} = 262,144 \text{ or } 1,048,576$$

To reproduce this live within a 60-minute presentation on a single laptop without burning $5,000 in cloud bills or crashing Docker Desktop, we preserve the exact **mathematical ratio**:

| Metric | Real Production (m5.4xlarge) | Masterclass Lab Simulation (Kind) |
| :--- | :--- | :--- |
| **Node RAM** | 64 GB – 128 GB | 8 GB – 16 GB |
| **`nf_conntrack_max`** | 262,144 entries | 2,048 entries |
| **Pod Workload** | 40 – 80 high-concurrency pods | 4 – 6 pods |
| **Total Concurrency** | 2,000 – 4,000 threads | 80 – 120 threads |
| **Saturation Window** | ~15–30 seconds | ~3–5 seconds |
| **Kernel Error** | `nf_conntrack: table full, dropping packet` | `nf_conntrack: table full, dropping packet` |

---

## 3. Production Repository Architecture

```
k8s-conntrack-dns-masterclass/
├── README.md                                # Architectural documentation & quickstart
├── RUNBOOK.md                               # Live 60-Minute Speaker presentation guide
├── setup/
│   ├── kind-config.yaml                     # Two-node Kind cluster configuration
│   ├── start-cluster.sh                     # Idempotent cluster bootstrap & node tool installer
│   └── set-kernel-limits.sh                 # Worker node netfilter constraint script
├── services/
│   └── checkout-service/                    # Realistic e-commerce payment microservice
│       ├── app.py                           # Calls Stripe API & internal Postgres
│       ├── Dockerfile
│       └── requirements.txt
├── deploy/
│   ├── helm/checkout-service/               # Production Helm chart
│   │   ├── Chart.yaml
│   │   ├── values.yaml                      # Prod defaults (unqualified hostnames, ndots:5)
│   │   └── templates/
│   │       ├── deployment.yaml              # Deployment with localhost liveness probe
│   │       ├── service.yaml
│   │       ├── configmap.yaml
│   │       └── _helpers.tpl
│   ├── checkout-service.yaml                # Pre-rendered manifest for non-Helm workflows
│   └── mock-external/                       # Realistic external & internal stubs (Stripe + RDS)
│       └── upstream-services.yaml
├── platform/
│   ├── monitoring/
│   │   └── prometheus-rules.yaml            # PromQL alerts (NodeConntrackSaturation, DNSLatency)
│   └── nodelocaldns/
│       └── nodelocaldns.yaml                # NodeLocal DNSCache DaemonSet for Kind (169.254.20.10)
├── incidents/
│   ├── INC-2026-POSTMORTEM.md               # Authentic SRE Incident Post-Mortem
│   └── drills/
│       ├── 01-baseline-traffic.sh           # Morning baseline (healthy state)
│       ├── 02-flash-sale-surge.sh           # Black Friday scaling surge (triggers conntrack drop)
│       └── 03-emergency-hotfix.sh           # 02:30 AM live kernel workaround to stop the bleeding
└── telemetry/
    ├── watch-conntrack.sh                   # Real-time ASCII conntrack saturation gauge
    ├── capture-dns-amplification.sh         # tcpdump inspector highlighting ndots:5 search domain walk
    └── monitor-kernel-drops.sh              # Kernel ring buffer (dmesg) drop follower
```

---

## 4. Git Branches

The repository uses an authentic Git branch workflow to model production incident resolution:
- **`main`**: The running production state with default configurations (short hostnames `api.stripe.com`, `postgres.internal`, default `ndots:5`).
- **`hotfix/conntrack-remediation`**: The SRE Pull Request branch (adds trailing dots, sets `ndots: 2` with `single-request-reopen`, and enables connection pooling).

To review what the SRE team changed:
```bash
git checkout hotfix/conntrack-remediation
git diff main deploy/helm/checkout-service/values.yaml
```

---

## 5. Live Masterclass Reproduction Sequence

### Step 1: Provision the Cluster
Bootstrap the two-node cluster and automatically install diagnostic utilities into the worker node container:
```bash
bash setup/start-cluster.sh
```

### Step 2: Set the Netfilter Lab Ratio
Constrain `nf_conntrack_max` on the target worker node to **2048** entries:
```bash
bash setup/set-kernel-limits.sh 2048
```

### Step 3: Open Telemetry Terminals (3-Pane Layout)
In your 3-pane terminal layout (see [RUNBOOK.md](RUNBOOK.md)):
- **Pane 1 (Top Left)**: Start the live conntrack gauge:
  ```bash
  bash telemetry/watch-conntrack.sh
  ```
- **Pane 2 (Bottom Left)**: Start the DNS packet sniffer:
  ```bash
  bash telemetry/capture-dns-amplification.sh
  ```
- **Pane 3 (Right)**: Execute the drills and triage commands.

---

### Step 4: Run the Incident Drills

#### Drill 01: Establish Baseline Morning Traffic
```bash
bash incidents/drills/01-baseline-traffic.sh
```
*Observation:* Conntrack table utilization is healthy (< 10%). Checkout transactions succeed with sub-10ms latency.

#### Drill 02: Trigger Flash-Sale Traffic Surge (Cyber Monday)
```bash
bash incidents/drills/02-flash-sale-surge.sh
```
*Observation:*
- HPA scales `checkout-service` to 6 replicas.
- Conntrack table surges to **100% SATURATED (2048/2048)** within 3 seconds.
- Netfilter drops all new UDP packets (`drop=` counter increments).
- In Pane 2, `tcpdump` shows parallel A/AAAA queries across 4 search paths for every transaction.
- In Pane 3, pod logs scream `EAI_AGAIN` (temporary failure in name resolution), while `kubectl get pods` remains **1/1 Running**!

#### Drill 03: Execute the 02:30 AM On-Call Hotfix (Stop the Bleeding)
```bash
bash incidents/drills/03-emergency-hotfix.sh
```
*Observation:* Dynamically expands `nf_conntrack_max` to 65,536 and flushes stale UDP entries. Table saturation drops instantly to 4%, and customer transactions recover immediately.

---

### Step 5: Implement Permanent Production Remediation

#### 1. The Workload Pull Request (Branch: `hotfix/conntrack-remediation`)
Switch to the hotfix branch:
```bash
git checkout hotfix/conntrack-remediation
git diff main deploy/helm/checkout-service/values.yaml
```

Preview against the live running cluster:
```bash
kubectl diff -f deploy/checkout-service.yaml
```

Apply the patched workload:
```bash
kubectl apply -f deploy/checkout-service.yaml
kubectl rollout status deployment/checkout-service -n checkout-prod
```
*Fixes Applied:*
1. **Trailing Dots (`api.stripe.com.`, `postgres.internal.`):** Tells glibc this is an absolute FQDN; skips all 4 search paths immediately.
2. **`dnsConfig` Override:** Sets `ndots: 2` and enables `single-request-reopen`.
3. **Resilient Client:** Connection pooling + Full Jitter exponential backoff.

#### 2. Fleet-Wide Platform Guardrail: NodeLocal DNSCache
Deploy NodeLocal DNSCache across the cluster:
```bash
kubectl apply -f platform/nodelocaldns/nodelocaldns.yaml
kubectl rollout status daemonset/node-local-dns -n kube-system
```
*Impact:* Pods query `169.254.20.10` locally. Cache misses are proxied upstream to CoreDNS over **persistent TCP streams**, permanently eliminating UDP connection tracking table churn.

---

## 6. Teardown & Reset

To delete the cluster and clean up all resources:
```bash
kind delete cluster --name conntrack-lab
```

---

## 7. Speaker Guide & Incident Post-Mortem
- For the full 60-minute presentation guide and narrative cues, see **[RUNBOOK.md](RUNBOOK.md)**.
- For the executive post-mortem review, see **[incidents/INC-2026-POSTMORTEM.md](incidents/INC-2026-POSTMORTEM.md)**.
