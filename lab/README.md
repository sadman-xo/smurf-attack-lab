# ICMP Smurf Attack — Lab

Companion to [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) and
`../reports/Smurf_Attack_Design_Report_4.pdf` (Group 05, Subsection A2).

The whole lab — attacker, router, amplifiers, victim — runs as **Linux network
namespaces inside one WSL2 Ubuntu kernel**. No VMs, no cloud, no route to the real
network: every packet stays on two virtual bridges joined by a router namespace.

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

## Prerequisites

- WSL2 with an Ubuntu distro (kernel ≥ 5.1 for `bc_forwarding`; confirmed present).
- `gcc`, `python3`, `iproute2` (`ip`) — already installed here.
- `sudo` (root is required for `ip netns`). You will be prompted for your password;
  every script re-execs itself under `sudo` automatically.
- **Optional:** `tcpdump` for a pcap capture at the victim. Without it the scripts
  still measure the flood using the victim's kernel ICMP counters. Install with:

  ```bash
  sudo apt-get update && sudo apt-get install -y tcpdump
  ```

Run everything from inside WSL, in this directory:

```bash
cd /mnt/c/Users/sadma/OneDrive/Desktop/Security_Project/lab
```

## Run order

```bash
sudo bash setup_lab.sh          # build namespaces/bridges + vulnerable config + self-test
sudo bash measure.sh --label vulnerable   # spoofed attack -> amplification factor (~3)
sudo bash defend.sh both        # apply the fixes (bc_forwarding=0, ignore broadcasts)
sudo bash measure.sh --label defended     # re-run identical attack -> replies collapse to 0
sudo bash teardown_lab.sh       # remove everything
```

`measure.sh` appends every run to `results/summary.tsv`, giving you the before/after
table for the report. Compare the `vulnerable` and `defended` rows.

## The two source senders (no hping/nping/scapy)

Both build the IP + ICMP headers and **both checksums** by hand over a raw
`IPPROTO_RAW` / `IP_HDRINCL` socket.

- [`src/smurf.py`](src/smurf.py) — bring-up tool.
- [`src/smurf.c`](src/smurf.c) — report deliverable. Build: `gcc -O2 -Wall -o src/smurf src/smurf.c`

`run_attack.sh` picks the engine and runs it in the attacker namespace:

```bash
sudo bash run_attack.sh --engine c  --count 100 --rate 50        # C sender
sudo bash run_attack.sh --engine py --count 1                    # single forged packet
sudo bash measure.sh   --engine c  --count 200 --size 512 --label c-big  # C + payload
```

## Deliberately vulnerable settings (lab only, torn down after)

| Where | Setting | Vulnerable | Secure default |
|-------|---------|-----------|----------------|
| router | `net.ipv4.ip_forward` | 1 | 1 (routing) |
| router | `net.ipv4.conf.*.bc_forwarding` | **1** | 0 |
| amp1-3 | `net.ipv4.icmp_echo_ignore_broadcasts` | **0** | 1 |
| router | `net.ipv4.conf.*.rp_filter` | 0 | (varies) |

`defend.sh` flips these back. Either the router fix **or** the amplifier fix alone
stops the flood; `defend.sh both` shows defence in depth. The same fixes also stop
the UDP "Fraggle" variant — the misconfiguration matters more than the protocol.

## Safety invariants

- All six namespaces are internal; nothing is bridged to the real NIC → no
  internet / campus route.
- Vulnerable sysctls live only inside namespaces and are removed by teardown.
- Low, instrumented packet rate — the point is the **multiplier**, not throughput.
