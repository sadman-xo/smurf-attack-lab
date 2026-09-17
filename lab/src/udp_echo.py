#!/usr/bin/env python3
"""udp_echo.py — a tiny UDP echo service (RFC 862), the Fraggle "amplifier".

The classic Fraggle attack abuses hosts that answer the UDP *echo* (7) or
*chargen* (19) services on a directed-broadcast address: one spoofed request to
the broadcast draws one reply from every host, just like the ICMP Smurf. Modern
systems ship these services off, so the lab runs this stand-in on each amplifier
to recreate the vulnerable-but-once-common condition.

It binds ``0.0.0.0:<port>`` (so it also receives packets delivered to the subnet
directed broadcast) and echoes each datagram straight back to its *sender* — which,
under the attack, is the spoofed victim address. Nothing here is Fraggle-specific:
it is an ordinary, correct echo server; the amplification comes entirely from the
router forwarding the directed broadcast, exactly as with Smurf.

Run inside an amplifier namespace, e.g.:
    ip netns exec amp1 python3 udp_echo.py 7
"""
import signal
import socket
import sys


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 7

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # SO_BROADCAST lets the socket both receive broadcast-destined datagrams and,
    # if ever needed, reply to one; the echo reply itself is a normal unicast.
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind(("0.0.0.0", port))

    # Terminate cleanly on SIGTERM (how teardown_lab.sh / defend.sh stop us).
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    while True:
        try:
            data, addr = s.recvfrom(65535)
        except (InterruptedError, OSError):
            continue
        try:
            s.sendto(data, addr)          # echo back to the (spoofed) sender
        except OSError:
            pass                          # unreachable reply target -> ignore


if __name__ == "__main__":
    sys.exit(main())
