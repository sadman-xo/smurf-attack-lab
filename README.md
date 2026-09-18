# ICMP Smurf & Fraggle Attacks — Design & Isolated Lab

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https%3A%2F%2Fgithub.com%2Fsadman-xo%2Fsmurf-attack-lab&cloudshell_tutorial=tutorial.md&cloudshell_workspace=.)

**Group 05, Subsection A2.** A complete study of the classic ICMP *Smurf*
amplification attack **and its UDP twin, *Fraggle***: a design report plus a hands-on
lab that reproduces both attacks, measures their amplification, shows it scale with the
number of amplifiers, and demonstrates a layered set of defenses — entirely inside
isolated Linux network namespaces with **no route to any real network**.

> [!WARNING]
> **Educational use only.** This repository contains working ICMP/UDP amplification
> packet generators. They are built to run against the self-contained namespace lab in
> this repo, which cannot reach the internet or any campus network. Do **not** point
> them at any host, address, or network you do not own and have explicit permission to
> test. Directed-broadcast amplification against third parties is illegal in most
> jurisdictions.

## Layout

```
Security_Project/
├─ reports/Smurf_Attack_Design_Report_4.pdf   design report (the deliverable)
└─ lab/
   ├─ IMPLEMENTATION_PLAN.md   how the lab maps to the report (+ extensions)
   ├─ README.md                lab usage in detail
   ├─ lab.env                  topology constants (one source of truth)
   ├─ setup_lab.sh             build namespaces/bridges + vulnerable config
   ├─ teardown_lab.sh          remove everything
   ├─ defend.sh                apply / revert the defenses (router|amps|service|spoofguard|all)
   ├─ run_attack.sh            launch a sender in the attacker namespace (--proto icmp|udp)
   ├─ measure.sh               run one attack + compute amplification factor
   ├─ run_all.sh               reproduce the whole attack/defense matrix in one command
   ├─ scale_test.sh            sweep the amplifier count -> factor(k) = k
   ├─ src/smurf.{py,c}         hand-rolled ICMP Smurf sender  (Python + C)
   ├─ src/fraggle.{py,c}       hand-rolled UDP Fraggle sender (Python + C)
   ├─ src/udp_echo.py          tiny UDP echo service = the Fraggle amplifier
   └─ results/                 measured evidence (RESULTS.md, summary.tsv, scaling.tsv, *.pcap)
```

> The PDF report designs the classic ICMP Smurf attack. The **Fraggle variant, the
> amplifier-count scaling experiment, and the edge source-guard defense** are lab
> extensions that go beyond the report — they exist to prove the report's own thesis
> that *the misconfiguration, not the protocol, is the vulnerability.*

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
amplifier — so N amplifiers turn 1 request into N replies at the victim. Swap ICMP
echo for a UDP echo (port 7) and it is *Fraggle*: same forged source, same directed
broadcast, same amplification.

**Measured results (3 amplifiers, 100 spoofed requests each):**

| | Smurf (ICMP) | Fraggle (UDP) |
|---|:---:|:---:|
| Vulnerable | **factor 3.00** | **factor 3.00** |
| `bc_forwarding=0` (router) | 0.00 | 0.00 |
| amps ignore broadcast echo | 0.00 | 3.00 *(unaffected!)* |
| stop UDP echo service | 3.00 *(unaffected!)* | 0.00 |
| edge IP source guard | 0.00 | 0.00 |

The router fix and the edge source-guard each stop **both** attacks; the ICMP host fix
stops only Smurf and the UDP host fix only Fraggle — proving the misconfiguration, not
the protocol, is the bug. Amplification scales linearly with the number of live
amplifiers (`factor(k) = k`, verified 1→8). Full numbers, the scaling sweep, and packet
traces are in [`lab/results/RESULTS.md`](lab/results/RESULTS.md).

All four senders build every IP / ICMP / UDP header field and every checksum (including
the UDP pseudo-header checksum) by hand — no `hping`/`nping`/`scapy`.

## Quick start (WSL2 / Linux, needs root)

```bash
cd lab
sudo bash setup_lab.sh                       # build lab + vulnerable config + self-test
sudo bash measure.sh --label vuln            # ICMP Smurf   -> factor ~3
sudo bash measure.sh --proto udp --label vuln # UDP Fraggle -> factor ~3
sudo bash defend.sh both                      # apply the classic fixes
sudo bash measure.sh --label defended         # re-run -> collapses to 0
sudo bash teardown_lab.sh                      # clean up

# ...or reproduce the entire matrix + scaling sweep in two commands:
sudo bash run_all.sh                           # every attack x every defense
sudo bash scale_test.sh                        # amplification factor vs. amplifier count
```

See [`lab/README.md`](lab/README.md) for prerequisites, the C senders, the Fraggle
variant, payload/rate options, the defense taxonomy, and the full settings table.
