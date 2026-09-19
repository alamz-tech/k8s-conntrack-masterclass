#!/usr/bin/env python3
"""
generate_docx.py
Generates a beautifully formatted Microsoft Word (.docx) document for the Teacher Guide.
Features:
  - Professional typography (Calibri / Consolas)
  - Color-coded hierarchy (Executive Navy, Slate Blue, Charcoal)
  - Styled code blocks, callout boxes, and tables
  - Zero emojis (clean enterprise documentation)
  - Detailed Tinder case study and minute-by-minute instructor script
"""

import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders(table, color="D0D7DE", sz="4", val="single"):
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideV w:val="none"/>'
            f'<w:left w:val="none"/>'
            f'<w:right w:val="none"/>'
            f'</w:tblBorders>'
        )
        tblPr[0].append(borders)

def add_callout(doc, text, title="INSTRUCTOR TALKING POINT", bg_hex="F0F4F8", border_hex="1B365D"):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, bg_hex)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    # Left border only
    tcPr = cell._element.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{border_hex}"/>'
        f'<w:top w:val="none"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    
    if title:
        r_title = p.add_run(f"[{title}]\n")
        r_title.bold = True
        r_title.font.name = "Calibri"
        r_title.font.size = Pt(9.5)
        r_title.font.color.rgb = RGBColor(0x1B, 0x36, 0x5D)
        
    r_body = p.add_run(text)
    r_body.italic = True
    r_body.font.name = "Calibri"
    r_body.font.size = Pt(10)
    r_body.font.color.rgb = RGBColor(0x22, 0x22, 0x22)
    
    # Empty space after table
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(4)

def add_code_block(doc, code_text):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    
    cell = table.cell(0, 0)
    cell.width = Inches(6.5)
    set_cell_background(cell, "F6F8FA")
    set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
    
    tcPr = cell._element.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="6" w:space="0" w:color="D0D7DE"/>'
        f'<w:bottom w:val="single" w:sz="6" w:space="0" w:color="D0D7DE"/>'
        f'<w:left w:val="single" w:sz="6" w:space="0" w:color="D0D7DE"/>'
        f'<w:right w:val="single" w:sz="6" w:space="0" w:color="D0D7DE"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.05
    
    lines = code_text.strip().split("\n")
    for i, line in enumerate(lines):
        r = p.add_run(line)
        r.font.name = "Consolas"
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(0x1F, 0x23, 0x28)
        if i < len(lines) - 1:
            p.add_run("\n")
            
    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_before = Pt(0)
    p_after.paragraph_format.space_after = Pt(4)

def build_document(output_path):
    doc = Document()
    
    # Page setup - Margins 1 inch
    for s in doc.sections:
        s.top_margin = Inches(0.9)
        s.bottom_margin = Inches(0.9)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)
        
    # Styles configuration
    COLOR_PRIMARY = RGBColor(0x0A, 0x25, 0x40)      # Deep Navy
    COLOR_SECONDARY = RGBColor(0x20, 0x54, 0x93)    # Steel Blue
    COLOR_TEXT = RGBColor(0x2D, 0x37, 0x48)         # Charcoal Dark
    COLOR_MUTED = RGBColor(0x5A, 0x65, 0x78)        # Cool Slate Muted
    
    # Document Header / Pre-Title
    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_before = Pt(0)
    p_meta.paragraph_format.space_after = Pt(2)
    r_meta = p_meta.add_run("TECHNICAL INSTRUCTOR GUIDE  |  MASTERCLASS RUNBOOK")
    r_meta.font.name = "Calibri"
    r_meta.font.size = Pt(9)
    r_meta.font.bold = True
    r_meta.font.color.rgb = COLOR_SECONDARY
    
    # Document Title
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(2)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("Live Incident Triage:\nLinux Conntrack Exhaustion & Kubernetes DNS Loops")
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(22)
    r_title.font.bold = True
    r_title.font.color.rgb = COLOR_PRIMARY
    
    # Document Subtitle & Metadata
    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(2)
    p_sub.paragraph_format.space_after = Pt(16)
    r_sub = p_sub.add_run(
        "Target Audience: Senior & Staff SREs, DevOps Engineers, Platform Architects\n"
        "Session Format: 60-Minute Interactive SEV-1 Incident Simulation (Zero Slides; Terminal & Kernel Metrics)\n"
        "Presenter Persona: Staff Infrastructure Engineer leading real-time triage and platform remediation."
    )
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(10)
    r_sub.font.color.rgb = COLOR_MUTED
    
    # Horizontal Divider
    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_before = Pt(0)
    p_div.paragraph_format.space_after = Pt(14)
    p_div_border = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="12" w:space="1" w:color="0A2540"/></w:pBdr>')
    p_div._element.get_or_add_pPr().append(p_div_border)
    
    # =========================================================================
    # SECTION 1: EXECUTIVE CONTEXT & THE TINDER CASE STUDY
    # =========================================================================
    h1 = doc.add_heading("1. Executive Context: The Tinder Outage and Why This Class Exists", level=1)
    h1.paragraph_format.space_before = Pt(14)
    h1.paragraph_format.space_after = Pt(6)
    for r in h1.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(15)
        r.font.color.rgb = COLOR_PRIMARY
        r.font.bold = True

    # 1.1 The Story
    h2 = doc.add_heading("1.1 The Migration: Tinder at Massive Scale", level=2)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(4)
    for r in h2.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(12)
        r.font.color.rgb = COLOR_SECONDARY
        r.font.bold = True
        
    p = doc.add_paragraph(
        "In 2018–2019, Tinder executed one of the largest production migrations in cloud-native history: "
        "moving over 200 microservices from legacy EC2 instances into a Kubernetes cluster spanning 1,000 EC2 worker nodes, "
        "15,000 pods, and 48,000 running containers. "
        "The primary goal was operational agility: replacing slow EC2 instance provisioning (which took several minutes during traffic spikes) "
        "with sub-second container scheduling, immutable infrastructure, and declarative configuration as code."
    )
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(8)

    # 1.2 The Crisis
    h2 = doc.add_heading("1.2 The Crisis: 250,000 Queries Per Second and the CoreDNS Scaling Trap", level=2)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(4)
    for r in h2.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(12)
        r.font.color.rgb = COLOR_SECONDARY
        r.font.bold = True

    p = doc.add_paragraph(
        "As traffic cut over to the new platform, Tinder experienced widespread, intermittent network timeouts. "
        "Customer checkouts, swipe transactions, and recommendation queries failed randomly with 1-second to 5-second connection stalls. "
        "Telemetry revealed that Tinder's internal DNS was answering over 250,000 requests per second. "
        "This query tsunami was driven by low Time-To-Live (TTL) settings on Route53 records and internal endpoints, combined with "
        "unpooled Node.js and Java HTTP clients opening fresh sockets per request."
    )
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(6)

    p = doc.add_paragraph(
        "Assuming this was a capacity limit in CoreDNS, Tinder scaled their DNS deployment aggressively: "
        "reaching 1,000 CoreDNS pods consuming 120 dedicated CPU cores. "
        "Yet, CoreDNS CPU utilization sat comfortably below 10%, while customer timeouts and dropped packets persisted unabated. "
        "Scaling CoreDNS was treating a symptom while actively aggravating the root architectural flaw."
    )
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(8)

    # 1.3 The Root Cause
    h2 = doc.add_heading("1.3 The Root Cause: Linux Netfilter, Conntrack, and NAT Race Conditions", level=2)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(4)
    for r in h2.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(12)
        r.font.color.rgb = COLOR_SECONDARY
        r.font.bold = True

    p = doc.add_paragraph(
        "Tinder's infrastructure engineering team discovered that the bottleneck was not application or DNS server compute, "
        "but the Linux kernel's Netfilter subsystem and the connection tracking table (nf_conntrack):"
    )
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(4)

    bullet_points = [
        ("SNAT and DNAT Overhead: ", "Every outbound UDP query directed at cluster DNS (10.96.0.10:53) must undergo Destination NAT (DNAT) to pick an individual CoreDNS pod, followed by Source NAT (SNAT)."),
        ("State Tuple Allocation: ", "Every UDP query allocates an ephemeral state tuple inside the node kernel's nf_conntrack table."),
        ("Netfilter Insert Contention: ", "Under high concurrency, when glibc sends parallel A (IPv4) and AAAA (IPv6) queries from multiple worker threads, concurrent kernel threads attempt to insert conntrack entries into the same hash bucket. This triggers an internal race condition, incrementing the insert_failed counter and resulting in silent kernel packet drops."),
        ("UDP Silence & 5-Second Stalls: ", "Because UDP lacks transmission control and acknowledgment headers, dropped packets are completely invisible to TCP windowing. The application runtime (glibc) is forced to block until its hardcoded resolver timeout expires (1 to 5 seconds) before attempting a retry.")
    ]
    for b_title, b_desc in bullet_points:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_before = Pt(2)
        bp.paragraph_format.space_after = Pt(2)
        bp.paragraph_format.line_spacing = 1.15
        r_bt = bp.add_run(b_title)
        r_bt.bold = True
        r_bt.font.name = "Calibri"
        r_bt.font.color.rgb = COLOR_TEXT
        r_bd = bp.add_run(b_desc)
        r_bd.font.name = "Calibri"
        r_bd.font.color.rgb = COLOR_TEXT

    # 1.4 The Engineering Solution
    h2 = doc.add_heading("1.4 The Solution: Moving DNS Link-Local", level=2)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(4)
    for r in h2.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(12)
        r.font.color.rgb = COLOR_SECONDARY
        r.font.bold = True

    p = doc.add_paragraph(
        "Tinder realized that routing DNS over the network was fundamentally flawed. "
        "They pioneered deploying a DNS caching agent on every single worker node as a DaemonSet—the architectural foundation "
        "of what is now Kubernetes NodeLocal DNSCache:"
    )
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(4)

    sol_points = [
        ("Zero SNAT / Zero DNAT: ", "Queries remain strictly link-local on the node (169.254.20.10). Netfilter NAT is completely bypassed."),
        ("Persistent TCP Multiplexing: ", "Cache misses are forwarded upstream to CoreDNS over persistent TCP connections (force_tcp), eliminating UDP connection tracking churn entirely."),
        ("Client Connection Pooling: ", "Application HTTP and database clients were updated with connection managers, reducing per-request socket initialization by over 95%.")
    ]
    for s_title, s_desc in sol_points:
        sp = doc.add_paragraph(style='List Bullet')
        sp.paragraph_format.space_before = Pt(2)
        sp.paragraph_format.space_after = Pt(2)
        sp.paragraph_format.line_spacing = 1.15
        r_st = sp.add_run(s_title)
        r_st.bold = True
        r_st.font.name = "Calibri"
        r_st.font.color.rgb = COLOR_TEXT
        r_sd = sp.add_run(s_desc)
        r_sd.font.name = "Calibri"
        r_sd.font.color.rgb = COLOR_TEXT

    # 1.5 Connection to Masterclass
    h2 = doc.add_heading("1.5 Connecting Tinder's Learnings to This Masterclass", level=2)
    h2.paragraph_format.space_before = Pt(10)
    h2.paragraph_format.space_after = Pt(4)
    for r in h2.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(12)
        r.font.color.rgb = COLOR_SECONDARY
        r.font.bold = True

    p = doc.add_paragraph(
        "Every engineer in your audience manages clusters built with the exact defaults that triggered Tinder's outage. "
        "When traffic surges, standard Kubernetes ndots:5 configurations force external domains (like api.stripe.com) "
        "to walk 4 consecutive search domains. Combined with parallel glibc lookups and unpooled connections, "
        "the Netfilter table saturates, dropping UDP packets while Kubelet healthchecks falsely report 1/1 Running.\n\n"
        "This masterclass takes the audience on a live journey: reproducing this failure in minutes, sniffing the packets in real time, "
        "applying the 2:30 AM on-call emergency sysctl bandage, and implementing the permanent architectural cure pioneered by Tinder."
    )
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(12)

    # =========================================================================
    # SECTION 2: PRE-FLIGHT PREPARATION & RUNBOOK COMMANDS
    # =========================================================================
    h1 = doc.add_heading("2. Pre-Flight Preparation: Instructor Environment", level=1)
    h1.paragraph_format.space_before = Pt(14)
    h1.paragraph_format.space_after = Pt(6)
    for r in h1.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(15)
        r.font.color.rgb = COLOR_PRIMARY
        r.font.bold = True

    p = doc.add_paragraph(
        "[CRITICAL ORDER OF OPERATIONS REQUIREMENT]\n"
        "Do not run telemetry scripts (telemetry/watch-conntrack.sh or telemetry/capture-dns-amplification.sh) "
        "before the cluster is provisioned. The telemetry scripts attach to the worker node container (conntrack-lab-worker). "
        "Always execute Step 1 (Cluster Provisioning) and Step 2 (Kernel Tuning) first."
    )
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(8)

    # Step 1
    doc.add_heading("Step 1: Verify Docker Desktop", level=3)
    p = doc.add_paragraph("Ensure Docker Desktop is running with at least 4 GB RAM and 4 CPUs allocated.")
    p.paragraph_format.space_after = Pt(2)
    add_code_block(doc, "docker ps")

    # Step 2
    doc.add_heading("Step 2: Clean Cluster Spin-Up", level=3)
    p = doc.add_paragraph(
        "Provisions the 2-node Kind cluster (conntrack-lab-control-plane and conntrack-lab-worker). "
        "Installs diagnostic tooling (conntrack, tcpdump, procps, iproute2) and pre-caches platform images."
    )
    p.paragraph_format.space_after = Pt(2)
    add_code_block(doc, "bash setup/start-cluster.sh")

    # Step 3
    doc.add_heading("Step 3: Tune Kernel Netfilter Limit", level=3)
    p = doc.add_paragraph("Constrains the Netfilter table to 2,048 entries to set up the saturation trap.")
    p.paragraph_format.space_after = Pt(2)
    add_code_block(doc, "bash setup/set-kernel-limits.sh 2048")

    # Layout
    doc.add_heading("Step 4: Prepare 3-Pane Instructor Layout", level=3)
    p = doc.add_paragraph("Configure your terminal into a 3-pane layout for live telemetry monitoring:")
    p.paragraph_format.space_after = Pt(2)
    add_code_block(doc, 
        "+---------------------------------------+---------------------------------------+\n"
        "| Pane 1 (Top Left)                     | Pane 3 (Right Full Height)            |\n"
        "| bash telemetry/watch-conntrack.sh     | Instructor Shell                      |\n"
        "| (Live Netfilter Saturation Meter)     | - Run drills live                     |\n"
        "+---------------------------------------+ - Execute kubectl commands            |\n"
        "| Pane 2 (Bottom Left)                  | - Inspect application logs            |\n"
        "| bash telemetry/capture-dns-amplif...  | - Apply platform hotfixes             |\n"
        "| (Live DNS Packet Inspector)           |                                       |\n"
        "+---------------------------------------+---------------------------------------+"
    )

    # Checklist
    p_chk = doc.add_paragraph()
    p_chk.paragraph_format.space_before = Pt(4)
    p_chk.paragraph_format.space_after = Pt(12)
    p_chk.add_run(
        "Screen-Share Verification Checklist:\n"
        "[  ] Font Size: Set terminal font to 18pt–20pt (Cmd + +) for streaming visibility.\n"
        "[  ] Focus Mode: Enable macOS Do Not Disturb.\n"
        "[  ] Git Branch: Confirm active branch is main: git checkout main.\n"
        "[  ] Git Working Tree: Confirm working tree is clean: git status."
    )

    # =========================================================================
    # SECTION 3: MINUTE-BY-MINUTE MASTERCLASS SCRIPT
    # =========================================================================
    h1 = doc.add_heading("3. Minute-by-Minute Masterclass Execution Script", level=1)
    h1.paragraph_format.space_before = Pt(14)
    h1.paragraph_format.space_after = Pt(6)
    for r in h1.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(15)
        r.font.color.rgb = COLOR_PRIMARY
        r.font.bold = True

    # Phase 1
    doc.add_heading("[00:00 - 05:00] Phase 1: The Cold Open & The Hook", level=2)
    p = doc.add_paragraph("Visual: Title slide or clean terminal window.")
    p.paragraph_format.space_after = Pt(4)
    add_callout(doc, 
        "Welcome, everyone. Today we are not reviewing theoretical slides. We are debugging a live SEV-1 production outage.\n\n"
        "The scenario: It is 2:15 AM on Cyber Monday. Marketing just launched a 50% flash sale. Inbound checkout traffic surges by 600%. "
        "Within ninety seconds, PagerDuty alerts fire: 35% of customer checkout transactions are failing with network timeouts.\n\n"
        "You jump on the bridge. The junior engineer says: 'I checked Datadog. CoreDNS CPU is sitting at 6%. Pods are 1/1 Running. "
        "Kubelet says healthy. It must be an external AWS outage.'\n\n"
        "But it is not AWS. In 2019, Tinder hit this exact wall during their migration to Kubernetes across 1,000 nodes. "
        "They scaled CoreDNS to 1,000 pods and 120 CPU cores, yet DNS timeouts persisted. "
        "Because the bottleneck was never CoreDNS CPU. It is an architectural interaction between default ndots:5, parallel glibc lookups, "
        "and the Linux kernel's Netfilter connection tracking table.\n\n"
        "Over the next 50 minutes, we will reproduce this failure live on screen, sniff the packets in real time, see why Kubelet deceived us, "
        "apply the 2:30 AM emergency hotfix, and deploy the permanent platform cure.",
        title="PHASE 1 TALKING POINTS"
    )

    # Phase 2
    doc.add_heading("[05:00 - 15:00] Phase 2: Establishing the Baseline & Setting the Trap", level=2)
    p = doc.add_paragraph("Visual: Pane 3 (Instructor Shell). Deploy upstream mocks and checkout baseline.")
    p.paragraph_format.space_after = Pt(4)
    add_code_block(doc,
        "# Step 1: Inspect cluster node topology\n"
        "kubectl get nodes -o wide\n\n"
        "# Step 2: Establish normal morning baseline\n"
        "bash incidents/drills/01-baseline-traffic.sh"
    )
    add_callout(doc,
        "Notice what we just deployed: a microservice called checkout-service talking to an internal PostgreSQL database (postgres.internal) "
        "and the Stripe API (api.stripe.com). At 2 replicas, everything is pristine: latency is under 8ms, zero dropped packets, and our conntrack "
        "table is using only ~140 entries out of 2,048 (7% capacity).",
        title="PHASE 2 TALKING POINTS"
    )
    p = doc.add_paragraph("Launch live telemetry monitors in Pane 1 and Pane 2:")
    p.paragraph_format.space_after = Pt(2)
    add_code_block(doc,
        "# Pane 1 (Top Left):\n"
        "bash telemetry/watch-conntrack.sh\n\n"
        "# Pane 2 (Bottom Left):\n"
        "bash telemetry/capture-dns-amplification.sh"
    )

    # Phase 3
    doc.add_heading("[15:00 - 25:00] Phase 3: The Flash Sale Surge (Triggering the Blast Radius)", level=2)
    p = doc.add_paragraph("Visual: Full 3-pane layout. Scale checkout service to 6 replicas and stream errors.")
    p.paragraph_format.space_after = Pt(4)
    add_code_block(doc,
        "bash incidents/drills/02-flash-sale-surge.sh\n"
        "kubectl logs -n checkout-prod -l app=checkout-service -f --tail=30"
    )
    add_callout(doc,
        "Watch Pane 1! Watch the counter: 300... 800... 1,600... 2,048: 100% SATURATED!\n"
        "Look at the counter underneath: drop=350, drop=420 per CPU core. Over 3,000 packets dropped.\n"
        "Look at the application logs: TRANSACTION ABORTED (DNS FAILURE): Temporary failure in name resolution (EAI_AGAIN).\n"
        "Customers are getting checkout failure screens right now.",
        title="PHASE 3 TALKING POINTS"
    )
    p = doc.add_paragraph("Examine pod health report in Pane 3:")
    p.paragraph_format.space_after = Pt(2)
    add_code_block(doc, "kubectl get pods -n checkout-prod")
    add_callout(doc,
        "Look at the screen: NAME: checkout-service-xxxx  READY: 1/1  STATUS: Running  RESTARTS: 0.\n"
        "Why is Kubernetes reporting that the pod is 100% healthy when customer checkouts are failing?\n"
        "Because the developer configured the liveness probe to hit http://127.0.0.1:8080/healthz.\n"
        "Localhost traffic over loopback does NOT allocate entries in the Netfilter connection tracking table! "
        "Kubelet is happily pinging loopback over TCP while external UDP traffic is being silently discarded by the Linux kernel!",
        title="THE DRAMATIC PAUSE: WHY KUBELET LIED"
    )

    # Phase 4
    doc.add_heading("[25:00 - 38:00] Phase 4: Forensic Investigation (Packet Sniffing & The Math)", level=2)
    p = doc.add_paragraph("Visual: Focus on Pane 2 (Packet Inspector). Trace a single lookup to api.stripe.com.")
    p.paragraph_format.space_after = Pt(4)
    add_callout(doc,
        "Why did 6 pods with 20 threads each exhaust 2,048 conntrack entries in less than 3 seconds?\n\n"
        "Look at Pane 2. Let's trace a single checkout transaction resolving api.stripe.com:\n"
        "1. api.stripe.com.checkout-prod.svc.cluster.local. -> [Query A] & [Query AAAA] -> NXDOMAIN\n"
        "2. api.stripe.com.svc.cluster.local.              -> [Query A] & [Query AAAA] -> NXDOMAIN\n"
        "3. api.stripe.com.cluster.local.                  -> [Query A] & [Query AAAA] -> NXDOMAIN\n"
        "4. api.stripe.com.                                -> [Query A] & [Query AAAA] -> SUCCESS\n\n"
        "That is 8 to 10 UDP packets for a single DNS lookup! Kubernetes injects options ndots:5 into /etc/resolv.conf. "
        "Because api.stripe.com only has 2 dots, glibc assumes it might be an internal service and walks the entire cluster search path first.\n\n"
        "120 threads x 10 queries x 30-second UDP conntrack retention = 36,000 concurrent state tuples! "
        "The table overflows, and the kernel drops the packets.",
        title="THE MATH BEHIND THE EXPLOSION"
    )
    p = doc.add_paragraph("Inspect kernel ring buffer drops in Pane 3:")
    p.paragraph_format.space_after = Pt(2)
    add_code_block(doc, "bash telemetry/monitor-kernel-drops.sh")

    # Phase 5
    doc.add_heading("[38:00 - 46:00] Phase 5: The 02:30 AM On-Call Bandage (Stop the Bleeding)", level=2)
    p = doc.add_paragraph("Visual: Pane 3. Execute dynamic sysctl expansion and conntrack flush.")
    p.paragraph_format.space_after = Pt(4)
    add_code_block(doc, "bash incidents/drills/03-emergency-hotfix.sh")
    add_callout(doc,
        "Look at Pane 1! The conntrack meter dropped from 100% to under 5% instantly!\n"
        "Look at the checkout logs: DNS errors stopped immediately. Throughput recovered to > 370 tx/sec with 0 DNS failures.\n"
        "We dynamically tuned sysctl -w net.netfilter.nf_conntrack_max=65536 and flushed stale dead UDP tuples.\n"
        "This bought us time. Now we submit the GitOps PR for the permanent cure.",
        title="PHASE 5 TALKING POINTS"
    )

    # Phase 6
    doc.add_heading("[46:00 - 54:00] Phase 6: The Permanent Fixes (Workload PR + NodeLocal DNS)", level=2)
    p = doc.add_paragraph("Visual: Pane 3. Inspect PR diff and deploy workload and platform fixes.")
    p.paragraph_format.space_after = Pt(4)
    add_code_block(doc,
        "# Step 1: Switch to remediation branch & inspect PR diff\n"
        "git checkout hotfix/conntrack-remediation\n"
        "git diff main deploy/helm/checkout-service/values.yaml"
    )
    add_callout(doc,
        "Examine the 3 lines in this PR diff:\n"
        "1. Trailing Dots: api.stripe.com. and postgres.internal. Tells glibc this is a root FQDN; query multiplier drops from 10x to 1x instantly!\n"
        "2. ndots: 2: Overrides Kubernetes defaults so external domains aren't penalized.\n"
        "3. Connection Pooling + Full Jitter: Prevents retry storms.",
        title="WORKLOAD PR EXPLANATION"
    )
    p = doc.add_paragraph("Apply workload fix and deploy NodeLocal DNSCache:")
    p.paragraph_format.space_after = Pt(2)
    add_code_block(doc,
        "# Apply Workload Fix\n"
        "kubectl apply -f deploy/checkout-service.yaml\n"
        "kubectl rollout status deployment/checkout-service -n checkout-prod\n\n"
        "# Deploy Strategic Platform Fix: NodeLocal DNSCache\n"
        "kubectl apply -f platform/nodelocaldns/nodelocaldns.yaml\n"
        "kubectl rollout status daemonset/node-local-dns -n kube-system\n\n"
        "# Verify Conntrack table drops to minimal baseline under full load\n"
        "docker exec conntrack-lab-worker conntrack -F\n"
        "sleep 3\n"
        "docker exec conntrack-lab-worker cat /proc/sys/net/netfilter/nf_conntrack_count"
    )
    add_callout(doc,
        "NodeLocal DNSCache runs a DNS caching agent on link-local IP 169.254.20.10 on every node. "
        "All pod queries stay inside the local node interface. Cache misses forward upstream to CoreDNS over persistent TCP connections (force_tcp). "
        "Conntrack UDP table churn drops to less than 1.5% (< 1,000 entries) even under continuous peak checkout load!",
        title="THE PLATFORM CURE"
    )

    # Phase 7
    doc.add_heading("[54:00 - 60:00] Phase 7: Post-Mortem & Audience Q&A", level=2)
    p = doc.add_paragraph("Visual: Post-mortem summary slide or documentation.")
    p.paragraph_format.space_after = Pt(4)
    add_callout(doc,
        "Summary of the 5 Golden Rules for every Platform and SRE team:\n"
        "1. Never trust localhost liveness probes alone: Pair them with synthetic egress tests.\n"
        "2. Put trailing dots on external endpoints in backend services: api.stripe.com.\n"
        "3. Override ndots: 2 in default Helm chart templates.\n"
        "4. Deploy NodeLocal DNSCache as a mandatory platform addon on all clusters.\n"
        "5. Alert proactively when (node_nf_conntrack_entries / node_nf_conntrack_entries_limit) > 0.80.",
        title="POST-MORTEM GOLDEN RULES"
    )

    # =========================================================================
    # SECTION 4: EMERGENCY PRESENTATION TROUBLESHOOTING MATRIX
    # =========================================================================
    h1 = doc.add_heading("4. Emergency Presenter Troubleshooting Matrix", level=1)
    h1.paragraph_format.space_before = Pt(14)
    h1.paragraph_format.space_after = Pt(6)
    for r in h1.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(15)
        r.font.color.rgb = COLOR_PRIMARY
        r.font.bold = True

    table = doc.add_table(rows=7, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table, color="D0D7DE")
    
    col_widths = [Inches(2.2), Inches(2.3), Inches(2.0)]
    headers = ["Scenario / Symptom", "Underlying Cause", "Immediate Presenter Rescue Command"]
    
    # Header row
    hdr_row = table.rows[0]
    for i, h_text in enumerate(headers):
        cell = hdr_row.cells[i]
        cell.width = col_widths[i]
        set_cell_background(cell, "0A2540")
        set_cell_margins(cell, top=100, bottom=100, left=120, right=120)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(h_text)
        r.font.name = "Calibri"
        r.font.size = Pt(9.5)
        r.font.bold = True
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    data = [
        ("Docker or Kind is lagging/stuck", "High conntrack churn or socket congestion", "docker exec conntrack-lab-worker conntrack -F"),
        ("Cluster creation timeout", "Host cgroup v1 or Docker RAM constraint", "Allocate >= 4 GB RAM in Docker Desktop; verify cgroup v2"),
        ("Need to reset conntrack to zero", "Stale entries from previous drill", "docker exec conntrack-lab-worker conntrack -F"),
        ("Reset drill namespaces cleanly", "Previous drill pods still terminating", "kubectl delete namespace checkout-prod external-systems --wait=false"),
        ("Hard reset cluster (< 60s)", "Full environment clean slate required", "bash setup/start-cluster.sh && bash setup/set-kernel-limits.sh 2048"),
        ("Accidentally switched git branch", "Need clean main branch", "git checkout main")
    ]

    for row_idx, (scen, cause, cmd) in enumerate(data, start=1):
        row = table.rows[row_idx]
        bg = "FFFFFF" if row_idx % 2 != 0 else "F8F9FA"
        for col_idx, text in enumerate([scen, cause, cmd]):
            cell = row.cells[col_idx]
            cell.width = col_widths[col_idx]
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.1
            r = p.add_run(text)
            r.font.name = "Consolas" if col_idx == 2 else "Calibri"
            r.font.size = Pt(8.5 if col_idx == 2 else 9.5)
            r.font.color.rgb = RGBColor(0x1F, 0x23, 0x28) if col_idx == 2 else COLOR_TEXT

    doc.save(output_path)
    print(f"Successfully generated docx: {output_path}")

if __name__ == "__main__":
    out_path = sys.argv[1] if len(sys.argv) > 1 else "TEACHER_GUIDE.docx"
    build_document(out_path)
