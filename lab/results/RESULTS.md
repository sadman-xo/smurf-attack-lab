# Smurf Lab — Measured Results

**Environment:** WSL2 Ubuntu, kernel 5.15 (`bc_forwarding` supported), 6 network
namespaces on two virtual bridges, **3 amplifiers**. Each run sends **100** ICMP
echo requests with a spoofed source (`src=10.0.20.100` = victim, `dst=10.0.10.255`
= amp directed broadcast) at 100 pps. Replies are counted at the victim three
independent ways — a tcpdump pcap, and the kernel counters `IcmpMsg InType0` and
`Icmp InEchoReps` — which agree exactly.

Amplification factor = replies received at victim / requests sent by attacker.

| Scenario | Sender | Sent | Replies at victim | Factor |
|----------|--------|------|-------------------|--------|
| Vulnerable | `smurf.py` | 100 | 300 | **3.00** |
| Vulnerable | `smurf.c`  | 100 | 300 | **3.00** |
| Defended — both fixes | `smurf.py` | 100 | 0 | **0.00** |
| Defended — router only (`bc_forwarding=0`) | `smurf.py` | 100 | 0 | **0.00** |
| Defended — amps only (`icmp_echo_ignore_broadcasts=1`) | `smurf.py` | 100 | 0 | **0.00** |
| Revert → recheck (still vulnerable) | `smurf.py` | 100 | 300 | **3.00** |

## What the numbers show

1. **Amplification.** One spoofed request draws N=3 replies — exactly the number of
   live amplifiers. The victim absorbs 3× the traffic the attacker emits, all of it
   apparently sourced from the amplifiers (the attacker's address never appears).
2. **Both senders are equivalent.** The hand-written Python and C generators produce
   identical results, confirming the by-hand IP/ICMP headers and checksums are correct.
3. **Either defence alone collapses the flood to zero.** Turning off directed-broadcast
   forwarding on the router, *or* making the amplifiers ignore broadcast echo, is
   sufficient; applying both is defence in depth.
4. **It is the configuration, not luck.** Reverting the fixes restores factor 3.00, so
   the collapse to 0 is caused by the defence, not by the lab breaking.

## Evidence files (this directory)

- `summary.tsv` — one row per run (machine-readable).
- `*.pcap` — victim-side captures; e.g. count echo-replies with
  `tcpdump -r vulnerable-py-*.pcap 'icmp[icmptype]==icmp-echoreply' | wc -l`.

## Packet-path proof (from a live trace)

A single directed-broadcast request was forwarded by the router and flooded to the
amp subnet as an L2 broadcast (`dst MAC ff:ff:ff:ff:ff:ff`); all three amplifiers
replied to the victim address:

```
router br-vic (in):  10.0.20.50 > 10.0.10.255: ICMP echo request
router br-amp (out): 10.0.20.50 > 10.0.10.255: ICMP echo request   <-- forwarded
amp1 eth0:  76:c9:...:99 > ff:ff:ff:ff:ff:ff  10.0.20.50 > 10.0.10.255  echo request
router br-vic (in):  10.0.10.11 > 10.0.20.50: ICMP echo reply
                     10.0.10.12 > 10.0.20.50: ICMP echo reply
                     10.0.10.13 > 10.0.20.50: ICMP echo reply        <-- 3 replies
```
