# Smurf / Fraggle Lab — Measured Results

**Environment:** Ubuntu 24.04, Linux kernel 6.18 (`bc_forwarding` supported), 6 network
namespaces on two virtual bridges, **3 amplifiers** (canonical topology). Each run
sends **100** requests with a spoofed source (`src=10.0.20.100` = victim,
`dst=10.0.10.255` = amp directed broadcast) at 50 pps. Every row here is reproduced
by `sudo bash run_all.sh`; the scaling sweep by `sudo bash scale_test.sh`.

Amplification factor = replies received at victim / requests sent by attacker.

Replies are counted at the victim two independent ways that agree exactly:
- a **tcpdump pcap** on the victim's link, and
- a **kernel counter** in `/proc/net/snmp` — `IcmpMsg InType0` for Smurf (ICMP
  echo-replies), `Udp NoPorts` for Fraggle (the victim isn't listening on the echoed
  port, so every reply is counted there).

## 1. Attack matrix — Smurf (ICMP) and Fraggle (UDP)

Both attacks use the *same* forged source and the *same* directed broadcast; only the
L4 protocol differs (ICMP echo vs. UDP echo/port 7).

| Scenario | Sender | Proto | Sent | Replies | Factor |
|----------|--------|-------|------|---------|--------|
| Vulnerable | `smurf.py`   | ICMP | 100 | 300 | **3.00** |
| Vulnerable | `smurf.c`    | ICMP | 100 | 300 | **3.00** |
| Vulnerable | `fraggle.py` | UDP  | 100 | 300 | **3.00** |
| Vulnerable | `fraggle.c`  | UDP  | 100 | 300 | **3.00** |
| Revert → recheck | `smurf.py`   | ICMP | 100 | 300 | **3.00** |
| Revert → recheck | `fraggle.py` | UDP  | 100 | 300 | **3.00** |

Both protocols amplify identically, and both hand-written senders (Python and C)
produce identical results — confirming the by-hand IP/ICMP/UDP headers and all three
checksums (IP, ICMP, and the UDP pseudo-header checksum) are correct.

## 2. Defenses — which layer stops which attack

Each defense is applied alone (the config is reverted between layers) so its effect is
isolated. This is the heart of the lab: **the misconfiguration, not the protocol, is
the vulnerability.**

| Defense (applied alone) | Layer | Smurf (ICMP) | Fraggle (UDP) |
|-------------------------|-------|:------------:|:-------------:|
| `bc_forwarding=0` (router) | router forwarding | **0.00** | **0.00** |
| `icmp_echo_ignore_broadcasts=1` (amps) | ICMP host behaviour | **0.00** | 3.00 |
| stop UDP echo service (amps) | UDP host behaviour | 3.00 | **0.00** |
| edge IP source guard (attacker port) | source-address validation | **0.00** | **0.00** |

What the matrix shows:

1. **The router fix is the universal, root-cause fix.** Turning off directed-broadcast
   forwarding collapses *both* Smurf and Fraggle to zero — one packet stays one packet
   no matter the protocol.
2. **The classic ICMP host fix is protocol-specific.** Making the amplifiers ignore
   broadcast *echo* kills Smurf but a Fraggle over UDP sails straight past it (still
   3.00). Defending the symptom of one protocol leaves the door open for the next.
3. **The UDP host fix is the mirror image.** Disabling the echo service kills Fraggle
   but does nothing to Smurf (still 3.00).
4. **Edge source-address validation stops the attack before amplification.** Dropping
   the forged source at the attacker's access port (BCP 38 family) collapses both to
   zero — the spoofed request never even reaches the router. During the guarded runs
   the nft counter recorded every forged packet dropped. *Note:* this works because we
   validate the attacker's own switch port; plain subnet uRPF would **not** catch this
   spoof, since the forged victim address is itself valid on the victim subnet.
5. **It is the configuration, not luck.** Reverting every fix restores factor 3.00, so
   the collapse to 0 is caused by the defence, not by the lab breaking.

Defence in depth = router fix **and** host fixes **and** edge source guard; any one of
the two universal layers is sufficient on its own.

## 3. Amplification scales with the number of amplifiers

`scale_test.sh` enables *k* of the amplifiers and fires the identical attack. The
factor tracks *k* exactly (extended sweep to 8 amplifiers, `AMP_COUNT=8`):

| Live amplifiers (k) | Sent | Replies | Factor |
|:-------------------:|------|---------|:------:|
| 1 | 100 | 100 | 1.00 |
| 2 | 100 | 200 | 2.00 |
| 3 | 100 | 300 | 3.00 |
| 4 | 100 | 400 | 4.00 |
| 5 | 100 | 500 | 5.00 |
| 6 | 100 | 600 | 6.00 |
| 7 | 100 | 700 | 7.00 |
| 8 | 100 | 800 | 8.00 |

```
factor  1 #
vs      2 ##
live    3 ###
amps    4 ####
        5 #####
        6 ######
        7 #######
        8 ########
```

`factor(k) = k`. A real directed broadcast reaches every host on the subnet, so a
production /24 with hundreds of responders yields a three-orders-of-magnitude
multiplier from a single spoofed packet — the reason Smurf was a top-tier DDoS
technique before directed-broadcast forwarding was disabled by default (RFC 2644).

## 4. Packet-path proof (from the live traces)

**Smurf (ICMP)** — a single directed-broadcast echo request is forwarded by the router,
flooded to the amp subnet as an L2 broadcast (`dst MAC ff:ff:ff:ff:ff:ff`), and all
three amplifiers reply to the *victim* address:

```
router br-vic (in):  10.0.20.50 > 10.0.10.255: ICMP echo request
router br-amp (out): 10.0.20.50 > 10.0.10.255: ICMP echo request   <-- forwarded
amp1 eth0:  .. > ff:ff:ff:ff:ff:ff  10.0.20.50 > 10.0.10.255  echo request
router br-vic (in):  10.0.10.11 > 10.0.20.50: ICMP echo reply
                     10.0.10.12 > 10.0.20.50: ICMP echo reply
                     10.0.10.13 > 10.0.20.50: ICMP echo reply        <-- 3 replies
```

**Fraggle (UDP)** — identical amplification over UDP echo (port 7), captured at the
victim. One spoofed request draws one reply from each amplifier; the attacker's own
address (`10.0.20.50`) never appears — every reply is sourced from an amplifier:

```
10.0.10.11.7 > 10.0.20.100.40000: UDP, length 7
10.0.10.13.7 > 10.0.20.100.40000: UDP, length 7
10.0.10.12.7 > 10.0.20.100.40000: UDP, length 7      <-- 3 replies, one per amp
```

Over the full 100-request Fraggle run the victim received exactly 100 replies from
each of `10.0.10.11`, `10.0.10.12`, `10.0.10.13` (300 total); the four "defended"
captures for the router, amps-ICMP, service-UDP, and source-guard fixes contain **0**
reply packets.

## Evidence files (this directory)

- `summary.tsv` — one row per attack/defense run (machine-readable; regenerated by
  `run_all.sh`). Columns: `timestamp proto label engine sent pcap kernel factor`.
- `scaling.tsv` — the amplifier-count sweep (regenerated by `scale_test.sh`).
- `*.pcap` — victim-side captures, one per run. Count replies with, e.g.
  `tcpdump -r vulnerable-icmp-py-*.pcap 'icmp[0] = 0' | wc -l` or
  `tcpdump -r vulnerable-fraggle-py-*.pcap 'udp and dst port 40000' | wc -l`.
