# Live Incident Triage: Linux Conntrack Exhaustion & Kubernetes DNS Loops

> **A production-grade, immediately executable simulation repository for SRE and Platform Engineering technical masterclasses.**

![Architecture Diagram](https://img.shields.io/badge/Kubernetes-Kind-326CE5?logo=kubernetes&logoColor=white)
![Linux Kernel](https://img.shields.io/badge/Linux_Kernel-Netfilter-FCC624?logo=linux&logoColor=black)
![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)

---

## Table of Contents
1. [Incident Background & Architecture](#incident-background--architecture)
2. [The Anatomy of the Silent Drop](#the-anatomy-of-the-silent-drop)
3. [Repository Structure](#repository-structure)
4. [Prerequisites](#prerequisites)
5. [Quickstart Reproduction Guide](#quickstart-reproduction-guide)
6. [Telemetry & Observation](#telemetry--observation)
7. [Remediation & Verification](#remediation--verification)
8. [Cleanup & Teardown](#cleanup--teardown)
9. [Speaker Masterclass Runbook](#speaker-masterclass-runbook)

---

## Incident Background & Architecture

When workloads scale rapidly (such as Tinder's famous 2019 migration involving 1,000 nodes and 15,000 pods, or flash-sale e-commerce workloads), Kubernetes clusters face **silent network drops** while dashboards remain deceptive green:

```
                      +---------------------------------------+
                      |   Default Pod /etc/resolv.conf        |
                      |   nameserver 10.96.0.10               |
                      |   search triage-lab.svc.cluster.local |
                      |          svc.cluster.local            |
                      |          cluster.local                |
                      |   options ndots:5                     |
                      +-------------------+-------------------+
                                          |
                                          | Query: "db.internal" (< 5 dots)
                                          v
+-----------------------------------------------------------------------------------------+
| WORKER NODE (Linux Kernel)                                                              |
|                                                                                         |
|   glibc resolver fires parallel A (IPv4) & AAAA (IPv6) queries sequentially:            |
|                                                                                         |
|   [Query 1 & 2]:   db.internal.triage-lab.svc.cluster.local  ->  NXDOMAIN               |
|   [Query 3 & 4]:   db.internal.svc.cluster.local             ->  NXDOMAIN               |
|   [Query 5 & 6]:   db.internal.cluster.local                 ->  NXDOMAIN               |
|   [Query 7 & 8]:   db.internal.                              ->  10.96.100.100          |
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

## The Anatomy of the Silent Drop

### 1. The `ndots:5` glibc Multiplier
- Kubernetes defaults to `options ndots:5` in every pod's `/etc/resolv.conf`.
- If a queried domain contains fewer than 5 dots (e.g. `db.internal` has 1 dot; `api.stripe.com` has 2 dots), `glibc` will walk through **all search domains in order** before attempting the query as an absolute FQDN.
- Modern `glibc` issues `A` (IPv4) and `AAAA` (IPv6) queries in parallel over separate UDP sockets.
- As a result, a single resolution attempt creates **up to 10 UDP datagrams**.

### 2. The Netfilter Connection Tracking Bottleneck
- Linux Netfilter tracks every UDP conversation in its connection state table (`nf_conntrack`).
- Because UDP has no `SYN`/`FIN`/`RST` state packets, the kernel must keep an entry alive for `nf_conntrack_udp_timeout` (typically 30 seconds).
- Under retry storms without exponential backoff and jitter, client threads burst thousands of UDP queries.
- Once the table reaches `nf_conntrack_max`, the kernel executes `nf_conntrack_alloc()` which fails, and calls `net_warn_ratelimited("nf_conntrack: table full, dropping packet\n")`. All further UDP packets are silently discarded.

### 3. The Deceptive Green Kubelet
- Kubelet liveness and readiness probes commonly query `127.0.0.1:8080/healthz` over TCP or loopback.
- Established TCP connections and local loopback traffic bypass connection tracking allocation.
- **The Result:** Kubernetes dashboards show pods as `1/1 Running`, CoreDNS pod metrics show normal low CPU (since dropped packets never reached CoreDNS), while application business logic fails 100%.

---

## Repository Structure

```
.
├── README.md                                # Architectural documentation & quickstart
├── RUNBOOK.md                               # 60-Minute Speaker masterclass presentation guide
├── setup/
│   ├── kind-config.yaml                     # Two-node Kind cluster configuration
│   ├── start-cluster.sh                     # Idempotent cluster bootstrap & tool installer
│   └── set-kernel-limits.sh                 # Worker node netfilter constraint script
├── src/
│   └── client.py                            # Production-grade Payment Worker simulator
├── manifests/
│   ├── broken/
│   │   ├── 01-mock-upstream.yaml            # Mock DB pod, service & CoreDNS hosts patch
│   │   └── 02-broken-client.yaml            # Broken client deployment (ndots:5, 0-jitter)
│   └── fixed/
│       ├── 01-patched-client.yaml           # Git diff target (ndots:2, trailing dot, jitter)
│       └── 02-nodelocaldns.yaml             # NodeLocal DNSCache DaemonSet for Kind
└── telemetry/
    ├── watch-conntrack.sh                   # Real-time ASCII conntrack saturation gauge
    ├── capture-dns-amplification.sh         # tcpdump inspector highlighting 10x DNS walk
    └── monitor-kernel-drops.sh              # Kernel ring buffer (dmesg) drop follower
```

---

## Prerequisites

Before running the lab, ensure the following utilities are installed:
- **Docker** / Docker Desktop (macOS) or Docker Engine (Ubuntu 22.04)
- **Kind** (Kubernetes in Docker) `v0.20+`
- **Kubectl** `v1.26+`

Verify your installation:
```bash
docker version
kind version
kubectl version --client
```

---

## Quickstart Reproduction Guide

### Step 1: Provision the Kind Cluster
Bootstrap the two-node cluster and automatically install diagnostic utilities (`conntrack`, `tcpdump`, `procps`, `iproute2`) onto the worker node:
```bash
bash setup/start-cluster.sh
```

### Step 2: Constrain Worker Node Kernel Netfilter Limits
Reduce `nf_conntrack_max` on `conntrack-lab-worker` down to **2048** and set UDP retention to 30s:
```bash
bash setup/set-kernel-limits.sh 2048
```

### Step 3: Deploy the Mock Upstream Database
Deploys `mock-db` in the `triage-lab` namespace and patches CoreDNS to resolve `db.internal.` to its ClusterIP at the end of the search path:
```bash
kubectl apply -f manifests/broken/01-mock-upstream.yaml
kubectl rollout status deployment/mock-db -n triage-lab
```

### Step 4: Launch the Broken Workload
Launches 4 replicas of the payment worker with unjittered retry loops and default `ndots:5`:
```bash
kubectl apply -f manifests/broken/02-broken-client.yaml
```

---

## Telemetry & Observation

Open three terminal windows (or a 3-pane tmux session as described in [RUNBOOK.md](RUNBOOK.md)):

### Terminal 1: Watch Conntrack Table Saturation
```bash
bash telemetry/watch-conntrack.sh
```
Observe the ASCII meter surge from green (<50%) to red (100% SATURATED):
```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  LIVE TELEMETRY: LINUX NETFILTER CONNECTION TRACKING (CONNTRACK) MONITOR         ║
╚══════════════════════════════════════════════════════════════════════════════════╝
 Target Node Container: conntrack-lab-worker    Time:  14:32:10 

 Table Capacity Status:
   Current Entries:     2048 / 2048
   Saturation Level:     [██████████████████████████████] 100% SATURATED 

 🚨 CRITICAL ALERT: Table saturation exceeds 85%! Kernel dropping new UDP packets!
```

### Terminal 2: Watch DNS Amplification on the Wire
```bash
bash telemetry/capture-dns-amplification.sh
```
Observe the 10x DNS query multiplier in action:
```
[SEARCH-1: ns]  [A-RECORD IPv4]     IP 10.244.1.5.42103 > 10.96.0.10.53: 1234+ A? db.internal.triage-lab.svc.cluster.local. [NXDOMAIN - 404]
[SEARCH-1: ns]  [AAAA-RECORD IPv6]  IP 10.244.1.5.42104 > 10.96.0.10.53: 1235+ AAAA? db.internal.triage-lab.svc.cluster.local. [NXDOMAIN - 404]
[SEARCH-2: svc] [A-RECORD IPv4]     IP 10.244.1.5.42105 > 10.96.0.10.53: 1236+ A? db.internal.svc.cluster.local. [NXDOMAIN - 404]
[SEARCH-2: svc] [AAAA-RECORD IPv6]  IP 10.244.1.5.42106 > 10.96.0.10.53: 1237+ AAAA? db.internal.svc.cluster.local. [NXDOMAIN - 404]
[SEARCH-3: cl]  [A-RECORD IPv4]     IP 10.244.1.5.42107 > 10.96.0.10.53: 1238+ A? db.internal.cluster.local. [NXDOMAIN - 404]
[SEARCH-3: cl]  [AAAA-RECORD IPv6]  IP 10.244.1.5.42108 > 10.96.0.10.53: 1239+ AAAA? db.internal.cluster.local. [NXDOMAIN - 404]
[FINAL-ROOT]    [A-RECORD IPv4]     IP 10.244.1.5.42109 > 10.96.0.10.53: 1240+ A? db.internal. [NOERROR]
```

### Terminal 3: Monitor Kernel Drops
```bash
bash telemetry/monitor-kernel-drops.sh
```
Watch the kernel ring buffer output:
```
🚨 KERNEL DROP DETECTED  [142.948210] nf_conntrack: table full, dropping packet
```

---

## Remediation & Verification

### Solution 1: Workload-Level Optimization (The 3-Tier Fix)
Review the exact changes:
```bash
diff -u manifests/broken/02-broken-client.yaml manifests/fixed/01-patched-client.yaml
```

Apply the patched client:
```bash
kubectl apply -f manifests/fixed/01-patched-client.yaml
kubectl rollout status deployment/payment-worker -n triage-lab
```

**Verification:**
- Watch `telemetry/watch-conntrack.sh`: Count instantly drops from 2048 (100%) to **~150 (7%)**.
- Client pod logs show `0 DNS Failures` and p99 DNS latencies below 1ms.

### Solution 2: Cluster-Level Architecture (NodeLocal DNSCache)
Deploy NodeLocal DNSCache DaemonSet to cache DNS queries locally on node IP `169.254.20.10` and proxy cache misses to CoreDNS over **persistent TCP streams**:
```bash
kubectl apply -f manifests/fixed/02-nodelocaldns.yaml
kubectl rollout status daemonset/node-local-dns -n kube-system
```

**Verification:**
NodeLocal DNS terminates UDP locally on the node interface, bypassing netfilter conntrack churn entirely for upstream traffic.

---

## Cleanup & Teardown

To destroy the Kind cluster and all lab resources:
```bash
kind delete cluster --name conntrack-lab
```

---

## Speaker Masterclass Runbook

For a full minute-by-minute live presentation guide, audience narrative cues, and emergency recovery tips, see **[RUNBOOK.md](RUNBOOK.md)**.
