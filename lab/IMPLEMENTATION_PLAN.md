# ICMP Smurf Attack — Implementation Plan (WSL2 / network namespaces)

**Group 05, Subsection A2** — companion to `reports/Smurf_Attack_Design_Report_4.pdf`.

## 0. Approach in one line

Recreate the whole lab — attacker, router, amplifiers, victim — as **Linux network
namespaces inside one WSL2 Ubuntu kernel**. No VMs, no cloud. Every packet stays on a
virtual switch with no route to the internet, satisfying the report's isolation rule
automatically. The kernel is confirmed to support directed-broadcast forwarding
(`net.ipv4.conf.*.bc_forwarding` exists), which is the one feature the attack needs.

## 1. Topology and addressing

Two L2 segments (virtual bridges) joined by a router namespace.

```
        Amplifier subnet 10.0.10.0/24                Victim subnet 10.0.20.0/24
        (bridge br-amp)                              (bridge br-vic)
   amp1 10.0.10.11 ┐                                 ┌ victim   10.0.20.100  (tcpdump here)
   amp2 10.0.10.12 ┼── br-amp ── router ── br-vic ──┤
   amp3 10.0.10.13 ┘   10.0.10.1        10.0.20.1    └ attacker 10.0.20.50   (sends packet)
                       (bc_forwarding=1 on amp side, ip_forward=1)
```

Namespaces: `attacker`, `router`, `amp1`, `amp2`, `amp3`, `victim` (6 total, few MB each).

**Attack flow:** attacker sends ONE echo request, `src=10.0.20.100` (victim, spoofed),
`dst=10.0.10.255` (amp broadcast) → router forwards toward amp subnet → `bc_forwarding`
turns it into an L2 broadcast → amp1/2/3 each reply to 10.0.20.100 → victim receives 3
replies for 1 request. Amplification factor N = number of live amplifiers.

## 2. Deliberately vulnerable configuration (lab-only)

Applied by `setup_lab.sh`, all inside namespaces:
- **router:** `net.ipv4.ip_forward=1`, and `net.ipv4.conf.<amp-iface>.bc_forwarding=1`
  (directed-broadcast forwarding — historically the root cause).
- **amp1/2/3:** `net.ipv4.icmp_echo_ignore_broadcasts=0` (answer broadcast pings — the
  opposite of the modern safe default).
- No egress/anti-spoof filtering in the path, so the forged source survives.

## 3. Hand-written packet-crafting code

No ready-made tools (no hping/nping). Every header byte and BOTH checksums are ours.
- **`src/smurf.py`** (bring-up): `socket(AF_INET, SOCK_RAW, IPPROTO_RAW)` + `IP_HDRINCL`;
  IP + ICMP headers via `struct.pack`; own 16-bit one's-complement checksum; `sendto()`
  to `10.0.10.255` in a rate-controlled loop. Optional payload padding for bandwidth
  amplification.
- **`src/smurf.c`** (report deliverable): same design in C — `SOCK_RAW`, `IP_HDRINCL`,
  fill `struct iphdr`/`struct icmphdr`, own `checksum()` for both headers, `sendto()`
  loop. Args: victim IP, broadcast IP, rate, count, payload size.

Fields we set (from report Table 1): IP src=victim, IP dst=subnet broadcast, IP proto=1,
recompute IP checksum; ICMP type=8 code=0, id/seq, recompute ICMP checksum.

## 4. Measurement

- `tcpdump -ni <iface> icmp` in the **victim** namespace → count echo *replies* received.
- Attacker prints requests *sent*.
- **Amplification factor = replies_received / requests_sent** (expect ≈ N = 3).
- Record victim CPU / link rate over time; optionally vary amplifier count and payload
  size to separate packet-count from bandwidth amplification.
- `measure.sh` automates capture + count.

## 5. Defense demo (bonus) — before/after

`defend.sh` flips the vulnerable settings back to secure defaults:
1. **Primary:** `bc_forwarding=0` on the router → one packet stays one packet.
2. **Host suppression:** `icmp_echo_ignore_broadcasts=1` on amplifiers → silent.
Re-run the identical attack → replies collapse to **0**. Produce a before/after table.
(Note: the same fixes also stop the UDP "Fraggle" variant — misconfig matters more than
the protocol.)

## 6. File layout

```
Security_Project/
├─ reports/Smurf_Attack_Design_Report_4.pdf   (existing)
└─ lab/
   ├─ IMPLEMENTATION_PLAN.md   (this file)
   ├─ setup_lab.sh             (create namespaces/bridges/veth + vulnerable config)
   ├─ teardown_lab.sh          (delete everything cleanly)
   ├─ defend.sh                (apply secure-by-default settings)
   ├─ measure.sh               (capture at victim + count + amplification factor)
   ├─ run_attack.sh            (helper: launch sender in attacker ns)
   └─ src/
      ├─ smurf.py              (Python raw-socket sender)
      └─ smurf.c               (C raw-socket sender — report deliverable)
```

## 7. Build order

0. **Prep:** `sudo apt install tcpdump` (and `build-essential` if needed); verify
   `ip netns`, `veth`, and bridge work in this WSL2 kernel.
1. **Lab up:** write + run `setup_lab.sh`; verify connectivity (attacker→router→amps,
   victim reachable) with normal unicast ping first.
2. **Baseline:** confirm a normal 1:1 ping (report's Figure 2 baseline).
3. **Attack (Python):** run `smurf.py`, confirm victim sees ~N replies per request.
4. **Measure:** capture + compute amplification factor.
5. **Port to C:** `smurf.c`, re-verify identical behaviour.
6. **Defense:** run `defend.sh`, re-run attack, capture the before/after collapse.
7. **Teardown:** `teardown_lab.sh`.

## 8. Safety invariants (hold throughout)

- All namespaces are internal; no bridge to the real NIC → no internet/campus route.
- Vulnerable settings live only inside namespaces and are torn down after.
- Low, instrumented packet rate — we demonstrate the *multiplier*, not raw throughput.
