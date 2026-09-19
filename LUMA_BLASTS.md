# Luma Notification Blasts (Copy & Paste Ready)

Use these templates to send email/SMS blasts to registered participants via Luma.

---

## 📢 Blast 1: T-minus 2 Hours

**Subject:** `[Starting in 2 Hours] The 3 AM incident where Kubelet was 100% green but payments failed`  
**Preview Text:** `Live Incident Triage: Linux Conntrack Exhaustion & Kubernetes DNS Loops`

```markdown
Hey everyone,

We are kicking off our live systems triage masterclass in exactly 2 hours!

Here is the scenario we will be debugging live on screen:
It’s 02:15 AM on Cyber Monday. A flash sale triggers an auto-scaling spike. Customer checkout transactions start failing with mysterious network timeouts. 

You check your dashboards:
• Pods are 1/1 Running with 0 restarts.
• CoreDNS CPU is sitting comfortably at 6%.
• Kubelet liveness checks are 100% green.

Why is money failing to enter the bank while monitoring says everything is pristine?

Today, we are skipping the theoretical slides. We’re jumping straight into the terminal to:
1. Trigger live Linux Netfilter conntrack table exhaustion.
2. Sniff the 10x DNS query amplification loop on the wire with tcpdump.
3. Show why Kubelet loopback healthchecks lied to us.
4. Execute the 02:30 AM emergency on-call hotfix.
5. Deploy the permanent platform architectural fix (NodeLocal DNSCache).

🗓 When: Today in 2 Hours
📍 Join Link: [Click Here to Join the Stream / Zoom]

Grab a coffee, have your terminal ready, and see you in 2 hours!

Best,
[Your Name / Title]
```

---

## 📢 Blast 2: T-minus 1 Hour

**Subject:** `[1 Hour to Go] Terminal setup, repo link & our 3-pane live screen`  
**Preview Text:** `Live in 60 mins: Sniffing DNS packets & kernel drops in real time`

```markdown
Hey folks,

We go live in 60 minutes! 

If you want to follow along with the code or review the architecture ahead of time, here is what you need:

💻 Code & Artifacts:
The complete reproduction lab, telemetry scripts, and SRE post-mortem are available here:
👉 [Insert GitHub / Repo Link]

🖥 Screen Recommendation:
If you have a dual-monitor setup, keep the stream on one screen and your terminal on the other. We will be using a 3-pane terminal layout:
• Top Left: Real-time Linux Netfilter conntrack saturation meter
• Bottom Left: Live DNS packet sniffer tracing parallel A/AAAA lookups
• Right Pane: Operator shell executing drills, hotfixes, and GitOps PRs

🗓 When: In 60 Minutes (Top of the hour)
📍 Join Link: [Click Here to Join the Masterclass]

See you in the room shortly!

Best,
[Your Name / Title]
```

---

## 🔴 Blast 3: Starting Now (We Are Live!)

**Subject:** `🔴 WE ARE LIVE: Incident Triage: Conntrack Exhaustion & Kubernetes DNS Loops`  
**Preview Text:** `Join now — jumping straight into the terminal to debug the SEV-1 outage`

```markdown
We are officially live! 

We're bypassing the slides and diving straight into the terminal to reproduce the Cyber Monday SEV-1 conntrack outage.

👉 JOIN LIVE NOW: [Click Here to Join the Room]

In the next 60 minutes:
• The mystery of the "deceptive green" Kubelet status
• Watching the Linux Netfilter table hit 100% saturation in real time
• Inspecting the 10x UDP DNS search path explosion with tcpdump
• The 02:30 AM on-call emergency hotfix
• Merging the GitOps PR and deploying NodeLocal DNSCache

Jump in now — the session is starting!
```
