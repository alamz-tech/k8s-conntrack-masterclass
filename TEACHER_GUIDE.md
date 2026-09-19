# Host & Teacher Guide: 60-Minute Masterclass
## "Live Incident Triage: Linux Conntrack Exhaustion & Kubernetes DNS Loops"

**Target Audience:** Senior & Staff SREs, DevOps Engineers, Platform Architects, Backend Leads  
**Session Style:** Live interactive incident response (No boring 50-slide deck; real terminal triage, live packet sniffing, kernel metrics)  
**Host Persona:** Staff Infrastructure Engineer walking the room through a realistic SEV-1 outage triage.

---

## 0. Pre-Flight Checklist (T-minus 15 Minutes)

- [ ] **Terminal Setup (3 Panes):**
  - Pane 1 (Top Left): Ready for `bash telemetry/watch-conntrack.sh`
  - Pane 2 (Bottom Left): Ready for `bash telemetry/capture-dns-amplification.sh`
  - Pane 3 (Right, full height): Active shell for running drills and inspecting pods
- [ ] **Font Size:** Increase terminal font to at least **18pt - 20pt** so mobile and low-res viewers can read clearly.
- [ ] **Cluster State:**
  ```bash
  cd /Users/husseinalamutu/.gemini/antigravity/scratch/k8s-conntrack-dns-masterclass
  bash setup/start-cluster.sh
  bash setup/set-kernel-limits.sh 2048
  ```
- [ ] **Notifications:** Do Not Disturb enabled on macOS/Linux.

---

## 1. Minute-by-Minute Masterclass Script

### [00:00 – 05:00] Phase 1: The Cold Open & The Hook
* **On Screen:** Title slide or blank clean terminal.
* **Host Talking Points:**
  > "Welcome, everyone. Today we are not looking at slides about theoretical architecture. We are debugging a live SEV-1 production outage.
  > 
  > The scenario: It's 2:15 AM on Cyber Monday. Marketing just launched a 50% flash sale. Traffic surges by 600%. Within two minutes, PagerDuty goes off: 35% of customer checkout transactions are failing with network timeouts.
  > 
  > You jump on the call. The junior on-call says: *'I looked at Datadog. CoreDNS CPU is sitting at 6%. Pods are 1/1 Running. Kubelet says healthy. It must be an external AWS outage.'*
  > 
  > But it's not AWS. It’s an architectural blind spot baked into the default configuration of almost every Kubernetes cluster in the world: the interaction between `ndots:5`, parallel `glibc` lookups, and the Linux kernel's Netfilter connection tracking table.
  > 
  > Over the next 50 minutes, we are going to reproduce this failure on screen, sniff the packets in real time, see why Kubelet lied to us, and apply both the 3 AM emergency hotfix and the permanent platform cure."

* **Audience Engagement Prompt:**
  > *"Quick pulse check in the chat: Type '1' if you've ever had a Kubernetes incident where the pods showed 1/1 Running, but customer requests were completely failing. Type '2' if you've ever scaled CoreDNS replicas hoping it would fix random DNS timeouts."*

---

### [05:00 – 15:00] Phase 2: Establishing the Baseline & Setting the Trap
* **On Screen:** Pane 3 (Operator Shell).
* **Action:**
  ```bash
  # Step 1: Show the cluster nodes
  kubectl get nodes -o wide

  # Step 2: Establish the normal morning baseline
  bash incidents/drills/01-baseline-traffic.sh
  ```
* **Host Talking Points:**
  > "Notice what we just deployed. We have a microservice called `checkout-service`. It talks to two services:
  > 1. An internal PostgreSQL database (`postgres.internal`) for inventory checks.
  > 2. The Stripe API (`api.stripe.com`) for payment capture.
  > 
  > Right now, at 2 replicas, everything looks like paradise. Look at the terminal output: latency is under 8 milliseconds, zero dropped packets, and our conntrack table is only using ~140 entries out of 2,048 (7% capacity)."

* **Action:** Launch the live gauges in the other panes:
  - In Pane 1 (Top Left): `bash telemetry/watch-conntrack.sh`
  - In Pane 2 (Bottom Left): `bash telemetry/capture-dns-amplification.sh`
* **Host Talking Points:**
  > "Take a look at Pane 1 on the top left. That green bar is our Linux Netfilter Connection Tracking table meter. In a moment, you are going to see that meter turn violently red."

---

### [15:00 – 25:00] Phase 3: The Flash Sale Surge (Triggering the Blast Radius)
* **On Screen:** Full 3-pane view.
* **Action (Pane 3):**
  ```bash
  bash incidents/drills/02-flash-sale-surge.sh
  kubectl logs -n checkout-prod -l app=checkout-service -f --tail=30
  ```
* **Host Talking Points:**
  > "Watch Pane 1! Watch the counter!
  > 300 entries... 800 entries... 1,600 entries... **2,048 entries: 100% SATURATED!**
  > 
  > And look at the counter underneath: `drop=840`, `insert_failed=840`.
  > Now look at Pane 3 at the application logs. Look at those red error messages:
  > `TRANSACTION ABORTED: [Errno -3] Temporary failure in name resolution (EAI_AGAIN)`.
  > Customers are getting checkout failure screens right now."

* **Action (Pane 3):** Run `kubectl get pods -n checkout-prod`
* **The Dramatic Pause:**
  > "Look at the screen right now.
  > `NAME: checkout-service-xxxx  READY: 1/1  STATUS: Running  RESTARTS: 0`.
  > 
  > Why is Kubernetes telling us the pod is 100% healthy when customer transactions are failing?
  > 
  > Because the developer configured the liveness probe to hit `http://127.0.0.1:8080/healthz`.
  > Localhost traffic over loopback does NOT allocate entries in the Netfilter connection tracking table! Kubelet is happily pinging loopback over TCP while all external UDP traffic is being thrown into the digital garbage can by the Linux kernel!"

---

### [25:00 – 38:00] Phase 4: Forensic Investigation (Packet Sniffing & The Math)
* **On Screen:** Focus on Pane 2 (Packet Inspector).
* **Host Talking Points:**
  > "Now let's ask the Staff Engineer question: *Why did only 6 pods with 20 threads each exhaust 2,048 conntrack entries in less than 3 seconds?*
  > 
  > Look at Pane 2. Let's trace a SINGLE checkout transaction trying to resolve `api.stripe.com`:
  > 
  > Notice the four search paths glibc queries in order:
  > 1. `api.stripe.com.checkout-prod.svc.cluster.local.` -> [Query A] and [Query AAAA] -> NXDOMAIN!
  > 2. `api.stripe.com.svc.cluster.local.`              -> [Query A] and [Query AAAA] -> NXDOMAIN!
  > 3. `api.stripe.com.cluster.local.`                  -> [Query A] and [Query AAAA] -> NXDOMAIN!
  > 4. `api.stripe.com.`                                -> [Query A] and [Query AAAA] -> SUCCESS!
  > 
  > That is **8 to 10 UDP packets for a single DNS lookup!**
  > 
  > Why? Because Kubernetes injects `options ndots:5` into `/etc/resolv.conf`. If your domain has fewer than 5 dots—and `api.stripe.com` only has 2—glibc assumes it might be an internal cluster service and walks the entire cluster search path first.
  > 
  > Combine that with parallel IPv4 and IPv6 lookups, and unpooled HTTP connections, and the math becomes terrifying:
  > 120 threads $\times$ 10 queries $\times$ 30-second UDP conntrack retention = **36,000 concurrent state tuples**.
  > The table overflows, and the kernel drops the packets."

* **Action (Pane 3):**
  ```bash
  bash telemetry/monitor-kernel-drops.sh
  ```
* **Host Point:** Point to the kernel log: `🚨 KERNEL DROP DETECTED: nf_conntrack: table full, dropping packet`.

---

### [38:00 – 46:00] Phase 5: The 02:30 AM On-Call Bandage (Stop the Bleeding)
* **On Screen:** Pane 3.
* **Host Talking Points:**
  > "You are the on-call engineer at 2:30 AM. You cannot tell your VP of Engineering: *'Wait 45 minutes while I write code, submit a PR, wait for CI/CD, and deploy a canary.'*
  > You need to stop the bleeding immediately.
  > 
  > Here is what an experienced SRE does live on the node:"
* **Action (Pane 3):**
  ```bash
  bash incidents/drills/03-emergency-hotfix.sh
  ```
* **Host Talking Points:**
  > "Look at Pane 1! The conntrack meter dropped from 100% to **4%** instantly!
  > And look at the checkout logs: DNS errors stopped immediately. Transactions are flowing again.
  > 
  > We dynamically tuned `sysctl -w net.netfilter.nf_conntrack_max=65536` and flushed stale dead UDP tuples.
  > But this is just a bandage. If traffic triples again tomorrow, the table will fill up again. Now we implement the real engineering fixes."

---

### [46:00 – 54:00] Phase 6: The Permanent Fixes (Workload PR + NodeLocal DNS)
* **On Screen:** Pane 3.
* **Host Talking Points:**
  > "Next morning, we submit our Pull Request. Let's inspect the hotfix branch:"
* **Action (Pane 3):**
  ```bash
  git checkout hotfix/conntrack-remediation
  git diff main deploy/helm/checkout-service/values.yaml
  ```
* **Host Talking Points:**
  > "Look at these three lines in the PR diff:
  > 
  > 1. **Trailing Dots:** `api.stripe.com.` and `postgres.internal.`. That single trailing dot tells glibc: *'This is an absolute domain name. Do NOT walk cluster search domains.'* Query multiplier drops from 10x to 1x instantly!
  > 2. **`ndots: 2`:** Overrides the Kubernetes default so external domains aren't penalized.
  > 3. **Connection Pooling + Full Jitter:** Prevents retry storms when network blips occur."

* **Action (Pane 3):**
  ```bash
  kubectl apply -f deploy/checkout-service.yaml
  kubectl rollout status deployment/checkout-service -n checkout-prod
  ```

* **The Platform Strategic Fix:**
  > "As Platform Engineers, we can't inspect every developer's HTTP client or trailing dots. We need an infrastructure guardrail.
  > That guardrail is **NodeLocal DNSCache**."
* **Action (Pane 3):**
  ```bash
  kubectl apply -f platform/nodelocaldns/nodelocaldns.yaml
  ```
* **Host Talking Points:**
  > "NodeLocal DNSCache runs a DNS caching agent on link-local IP `169.254.20.10` on every single node.
  > All pod DNS queries stay inside the local node interface.
  > Cache misses are forwarded upstream to CoreDNS over **persistent TCP connections (`force_tcp`)**.
  > Conntrack UDP table churn drops to **ZERO**."

---

### [54:00 – 60:00] Phase 7: Post-Mortem & Audience Q&A
* **On Screen:** Summary slide or `incidents/INC-2026-POSTMORTEM.md`.
* **Host Wrap-Up:**
  > "Let's summarize the 5 Golden Rules every Platform and SRE team should take away:
  > 1. **Never trust localhost liveness probes alone:** Pair them with synthetic egress tests.
  > 2. **Put trailing dots on external endpoints in backend services** (`api.stripe.com.`).
  > 3. **Override `ndots: 2` in your default Helm chart templates.**
  > 4. **Deploy NodeLocal DNSCache as a mandatory platform addon on every cluster over 50 nodes.**
  > 5. **Set up a Prometheus alert on `(node_nf_conntrack_entries / node_nf_conntrack_entries_limit) > 0.85`.**
  > 
  > Let's open the floor to questions!"

---

## 2. Emergency Presenter Troubleshooting ("Oh Shit" Cheat Sheet)

| Glitch / Problem | Instant Presenter Rescue Command |
| :--- | :--- |
| **Docker or Kind is lagging/stuck** | `docker exec conntrack-lab-worker conntrack -F` |
| **Need to reset conntrack table to zero instantly** | `docker exec conntrack-lab-worker conntrack -F` |
| **Want to remove all pods and restart fresh** | `kubectl delete namespace checkout-prod external-systems --wait=false` |
| **Hard reset cluster (takes ~45 seconds)** | `bash setup/start-cluster.sh && bash setup/set-kernel-limits.sh 2048` |
| **Accidentally on wrong git branch** | `git checkout main` |
