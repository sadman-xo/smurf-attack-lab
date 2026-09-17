# Smurf & Fraggle Attacks — Lab

Companion to [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) and
`../reports/Smurf_Attack_Design_Report_4.pdf` (Group 05, Subsection A2).

The whole lab — attacker, router, amplifiers, victim — runs as **Linux network
namespaces** inside a single kernel (WSL2 Ubuntu, or any modern Linux host). No VMs,
no cloud, no route to the real network: every packet stays on two virtual bridges
joined by a router namespace.

```
   amp subnet 10.0.10.0/24 (br-amp)        victim subnet 10.0.20.0/24 (br-vic)
 amp1 .11 ┐                                 ┌ victim   .100  (tcpdump / counters)
 amp2 .12 ┼── br-amp ── [ router ] ── br-vic┤
 amp3 .13 ┘  .1        forwards       .1    └ attacker .50   (crafts the packet)
```

**One forged packet** — `src=10.0.20.100` (victim, spoofed), `dst=10.0.10.255`
(amp broadcast) — is forwarded by the router, turned into an L2 broadcast, and
answered by every amplifier. N amplifiers turn 1 request into N replies at the
victim: **amplification factor N**.

Two attacks share that one mechanism:

- **Smurf** — the request is an ICMP *echo* (ping). Amplifiers answer because they
  reply to broadcast pings.
- **Fraggle** — the request is a UDP datagram to the *echo* service (port 7). Amplifiers
  answer because they run an echo service (the lab starts a tiny one, `src/udp_echo.py`,
  on each amplifier). Same forged source, same directed broadcast, same factor.

## Prerequisites

- A Linux kernel ≥ 5.1 (for `net.ipv4.conf.*.bc_forwarding`). WSL2 Ubuntu works;
  so does a plain Linux host or container with `CAP_NET_ADMIN`.
- `gcc`, `python3`, `iproute2` (`ip`).
- `sudo` / root (required for `ip netns`). Every script re-execs itself under `sudo`.
- **Optional:** `tcpdump` for a pcap capture at the victim, and `iputils-ping` for the
  setup connectivity check. Both are optional — without them the scripts fall back to
  the victim's kernel counters (`/proc/net/snmp`) and a raw-socket self-test. Install:

  ```bash
  sudo apt-get update && sudo apt-get install -y tcpdump iputils-ping
  ```

Run everything from inside this `lab/` directory. **Not sure your machine can run it?**
Check first — this prints a PASS/FAIL verdict for every required kernel feature:

```bash
sudo bash preflight.sh
```

> **WSL2 note:** the *default* Microsoft WSL kernel often ships without `CONFIG_BRIDGE`
> and without `bc_forwarding`, the two features the lab depends on — so the lab can fail
> on WSL2 while working on any full Linux kernel (a VM, a container, or a cloud box).
> `preflight.sh` tells you exactly what is missing.

## Run order

```bash
sudo bash setup_lab.sh                        # build lab + vulnerable config + self-test
sudo bash measure.sh --label vuln             # ICMP Smurf   -> amplification factor (~3)
sudo bash measure.sh --proto udp --label vuln # UDP Fraggle  -> amplification factor (~3)
sudo bash defend.sh both                       # apply the classic fixes
sudo bash measure.sh --label defended          # re-run identical attack -> collapses to 0
sudo bash teardown_lab.sh                       # remove everything
```

`measure.sh` appends every run to `results/summary.tsv` (columns:
`timestamp proto label engine sent pcap kernel factor`), giving you the before/after
table. Two one-command shortcuts reproduce the whole study:

```bash
sudo bash run_all.sh      # every attack (Smurf/Fraggle, py/c) x every defense -> summary.tsv
sudo bash scale_test.sh   # amplification factor vs. number of live amplifiers -> scaling.tsv
```

## The four senders + the amplifier service (no hping/nping/scapy)

Every sender builds the IP + L4 headers and **every checksum** by hand over a raw
`IPPROTO_RAW` / `IP_HDRINCL` socket. The Fraggle senders additionally compute the UDP
checksum over its 12-byte pseudo-header (RFC 768).

- [`src/smurf.py`](src/smurf.py) / [`src/smurf.c`](src/smurf.c) — ICMP Smurf (Python bring-up + C deliverable).
- [`src/fraggle.py`](src/fraggle.py) / [`src/fraggle.c`](src/fraggle.c) — UDP Fraggle.
- [`src/udp_echo.py`](src/udp_echo.py) — the amplifier: a tiny UDP echo service the
  lab runs on each amplifier so Fraggle has something to amplify.

`run_attack.sh` picks the protocol + engine and runs it in the attacker namespace
(the C binaries are built on demand):

```bash
sudo bash run_attack.sh --engine c  --count 100 --rate 50            # C Smurf
sudo bash run_attack.sh --proto udp --engine c --count 100           # C Fraggle
sudo bash run_attack.sh --proto udp --engine py --count 1            # single forged UDP packet
sudo bash measure.sh   --engine c  --count 200 --size 512 --label c-big  # C + payload
```

## Defenses — one flag per layer

`defend.sh <mode>` applies (or reverts) each layer independently:

| `defend.sh` mode | What it changes | Stops Smurf | Stops Fraggle |
|------------------|-----------------|:-----------:|:-------------:|
| `router`     | `bc_forwarding=0` on the router | ✅ | ✅ |
| `amps`       | `icmp_echo_ignore_broadcasts=1` on amps | ✅ | ❌ |
| `service`    | stop the UDP echo service on amps | ❌ | ✅ |
| `spoofguard` | edge IP source guard at the attacker's port | ✅ | ✅ |
| `both`       | `router` + `amps` (the two classic fixes) | ✅ | ✅ |
| `all`        | every layer above (defence in depth) | ✅ | ✅ |
| `revert`     | restore the fully vulnerable config | — | — |

The takeaway: the **router fix** (turn off directed-broadcast forwarding) and the
**edge source guard** (drop the forged source at its access port) each stop *both*
attacks, because they attack the root cause — the forwarded broadcast and the spoof
itself. The per-host fixes are protocol-specific: silencing broadcast *ping* does
nothing to a UDP Fraggle, and vice-versa. That is the whole point: **the
misconfiguration, not the protocol, is the vulnerability.**

> The edge source guard works here because it validates the attacker's own switch port.
> Plain subnet uRPF would *not* catch this spoof — the forged victim address is itself
> valid on the victim subnet, so only per-port source validation distinguishes them.

## Deliberately vulnerable settings (lab only, torn down after)

| Where | Setting / state | Vulnerable | Secure default |
|-------|-----------------|-----------|----------------|
| router | `net.ipv4.ip_forward` | 1 | 1 (routing) |
| router | `net.ipv4.conf.*.bc_forwarding` | **1** | 0 |
| router | `net.ipv4.conf.*.rp_filter` | 0 | (varies) |
| amp1-N | `net.ipv4.icmp_echo_ignore_broadcasts` | **0** | 1 |
| amp1-N | UDP echo service (`udp_echo.py`) | **running** | not present |
| edge   | IP source guard on attacker port | **absent** | present (BCP 38) |

`defend.sh` flips these back. All vulnerable state lives only inside the namespaces and
is removed by `teardown_lab.sh` (which also stops the responders and deletes the nft
source-guard table).

## Safety invariants

- All six namespaces are internal; nothing is bridged to the real NIC → no
  internet / campus route.
- Vulnerable sysctls and the echo responders live only inside namespaces and are
  removed by teardown.
- Low, instrumented packet rate — the point is the **multiplier**, not throughput.
