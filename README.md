# ICMP Smurf Attack — Design & Isolated Lab

**Group 05, Subsection A2.** A complete study of the classic ICMP *Smurf*
amplification attack: a design report plus a hands-on lab that reproduces the
attack, measures its amplification, and demonstrates the defenses — entirely
inside isolated Linux network namespaces with **no route to any real network**.

> [!WARNING]
> **Educational use only.** This repository contains a working ICMP amplification
> packet generator. It is built to run against the self-contained namespace lab in
> this repo, which cannot reach the internet or any campus network. Do **not** point
> it at any host, address, or network you do not own and have explicit permission to
> test. Directed-broadcast amplification against third parties is illegal in most
> jurisdictions.

## Layout

```
Security_Project/
├─ reports/Smurf_Attack_Design_Report_4.pdf   design report (the deliverable)
└─ lab/
   ├─ IMPLEMENTATION_PLAN.md   how the lab maps to the report
   ├─ README.md                lab usage in detail
   ├─ lab.env                  topology constants (one source of truth)
   ├─ setup_lab.sh             build namespaces/bridges + vulnerable config
   ├─ teardown_lab.sh          remove everything
   ├─ defend.sh                apply / revert the fixes
   ├─ run_attack.sh            launch a sender in the attacker namespace
   ├─ measure.sh               run the attack + compute amplification factor
   ├─ src/smurf.py             hand-rolled sender (Python, bring-up)
   ├─ src/smurf.c              hand-rolled sender (C, report deliverable)
   └─ results/                 measured evidence (RESULTS.md, summary.tsv, *.pcap)
```

## What it shows

The lab is six network namespaces on two virtual bridges joined by a router:

```
   amp subnet 10.0.10.0/24 (br-amp)        victim subnet 10.0.20.0/24 (br-vic)
 amp1 .11 ┐                                 ┌ victim   .100  (tcpdump / counters)
 amp2 .12 ┼── br-amp ── [ router ] ── br-vic┤
 amp3 .13 ┘  .1        forwards       .1    └ attacker .50   (crafts the packet)
```

One forged echo request (`src=`victim, `dst=`amp broadcast) is forwarded by the
router, flooded to the amp subnet as an L2 broadcast, and answered by every
amplifier — so N amplifiers turn 1 request into N replies at the victim.

**Measured result (3 amplifiers):** 100 spoofed requests → **300 replies, factor
3.00**; applying *either* defense collapses it to **0.00**. Full numbers and packet
traces in [`lab/results/RESULTS.md`](lab/results/RESULTS.md).

Both senders build every IP/ICMP header field and both checksums by hand — no
`hping`/`nping`/`scapy`.

## Quick start (WSL2 / Linux, needs root)

```bash
cd lab
sudo bash setup_lab.sh                     # build lab + vulnerable config + self-test
sudo bash measure.sh --label vulnerable    # spoofed attack -> factor ~3
sudo bash defend.sh both                   # apply the fixes
sudo bash measure.sh --label defended      # re-run -> collapses to 0
sudo bash teardown_lab.sh                  # clean up
```

See [`lab/README.md`](lab/README.md) for prerequisites, the C sender, payload/rate
options, and the full settings table.
