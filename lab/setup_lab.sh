#!/usr/bin/env bash
# setup_lab.sh — build the isolated Smurf lab out of Linux network namespaces.
#
# Topology (all virtual, no route to the real NIC):
#
#     amp subnet 10.0.10.0/24 (br-amp)        victim subnet 10.0.20.0/24 (br-vic)
#   amp1 .11 ┐                                 ┌ victim   .100  (tcpdump / counters)
#   amp2 .12 ┼── br-amp ── [ router ] ── br-vic┤
#   amp3 .13 ┘  .1        forwards       .1    └ attacker .50   (crafts the packet)
#
# Both bridges live INSIDE the router namespace and are its L3 interfaces, so the
# only path between the two subnets is through the router. Nothing is bridged to a
# real interface, so the lab cannot reach the internet or the campus network.
#
# Run: bash setup_lab.sh   (re-execs itself under sudo; needs root for ip netns).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lab.env
source "$SCRIPT_DIR/lab.env"

if [ "$(id -u)" -ne 0 ]; then exec sudo -E bash "$0" "$@"; fi

echo "[*] Removing any previous lab..."
bash "$SCRIPT_DIR/teardown_lab.sh" >/dev/null 2>&1 || true

echo "[*] Creating router namespace + two bridges..."
ip netns add "$NS_ROUTER"
ip -n "$NS_ROUTER" link set lo up
ip -n "$NS_ROUTER" link add "$BR_AMP" type bridge
ip -n "$NS_ROUTER" link add "$BR_VIC" type bridge
ip -n "$NS_ROUTER" addr add "${ROUTER_AMP_IP}/24" dev "$BR_AMP"
ip -n "$NS_ROUTER" addr add "${ROUTER_VIC_IP}/24" dev "$BR_VIC"
ip -n "$NS_ROUTER" link set "$BR_AMP" up
ip -n "$NS_ROUTER" link set "$BR_VIC" up

# add_host <ns> <router-side-veth> <bridge> <host-cidr> <gateway>
add_host() {
  local ns="$1" rif="$2" br="$3" cidr="$4" gw="$5"
  ip netns add "$ns"
  ip -n "$ns" link set lo up
  ip link add "$rif" type veth peer name "p-$ns"
  ip link set "$rif" netns "$NS_ROUTER"
  ip link set "p-$ns" netns "$ns"
  ip -n "$NS_ROUTER" link set "$rif" master "$br"
  ip -n "$NS_ROUTER" link set "$rif" up
  ip -n "$ns" link set "p-$ns" name eth0
  ip -n "$ns" addr add "$cidr" dev eth0
  ip -n "$ns" link set eth0 up
  ip -n "$ns" route add default via "$gw"
}

echo "[*] Attaching victim-side hosts..."
add_host victim   r-vic  "$BR_VIC" "${VICTIM_IP}/24"   "$ROUTER_VIC_IP"
add_host attacker r-att  "$BR_VIC" "${ATTACKER_IP}/24" "$ROUTER_VIC_IP"

echo "[*] Attaching $AMP_COUNT amplifiers..."
for i in $(seq 1 "$AMP_COUNT"); do
  add_host "amp$i" "r-amp$i" "$BR_AMP" "${AMP_SUBNET}.$((10 + i))/24" "$ROUTER_AMP_IP"
done

echo "[*] Applying the deliberately vulnerable configuration (lab only)..."
# Router: forward packets, AND forward directed broadcasts.
#   bc_forwarding is gated per-interface AND'd with conf.all, and the kernel checks
#   it on the *incoming* interface of the directed broadcast. We turn it on for
#   conf.all and BOTH bridges so the request is forwarded regardless of direction.
ip netns exec "$NS_ROUTER" sysctl -qw net.ipv4.ip_forward=1
ip netns exec "$NS_ROUTER" sysctl -qw net.ipv4.conf.all.bc_forwarding=1
ip netns exec "$NS_ROUTER" sysctl -qw "net.ipv4.conf.${BR_AMP}.bc_forwarding=1"
ip netns exec "$NS_ROUTER" sysctl -qw "net.ipv4.conf.${BR_VIC}.bc_forwarding=1"
# No anti-spoof filtering in the path, so the forged source survives.
ip netns exec "$NS_ROUTER" sysctl -qw net.ipv4.conf.all.rp_filter=0
ip netns exec "$NS_ROUTER" sysctl -qw "net.ipv4.conf.${BR_AMP}.rp_filter=0"
ip netns exec "$NS_ROUTER" sysctl -qw "net.ipv4.conf.${BR_VIC}.rp_filter=0"
# Amplifiers: answer broadcast pings (the opposite of the modern safe default of 1).
for i in $(seq 1 "$AMP_COUNT"); do
  ip netns exec "amp$i" sysctl -qw net.ipv4.icmp_echo_ignore_broadcasts=0
done

echo "[*] Baseline connectivity check (normal unicast)..."
chk() { # <ns> <target> <label>
  if ip netns exec "$1" ping -c1 -W1 "$2" >/dev/null 2>&1; then
    echo "    OK   $3"
  else
    echo "    FAIL $3"
  fi
}
chk attacker "$ROUTER_VIC_IP"   "attacker -> router"
chk attacker "${AMP_SUBNET}.11" "attacker -> amp1 (through router)"
chk victim   "${AMP_SUBNET}.11" "victim   -> amp1 (through router)"

echo "[*] Amplification self-test (real, non-spoofed broadcast ping from attacker)..."
# One request to the directed broadcast should draw AMP_COUNT replies. We can't use
# ping's own count -- with -c1 it exits on the FIRST reply and never sees the rest --
# so we read the attacker's kernel ICMP counter (echo-replies received, by type).
attacker_replies() {
  ip netns exec attacker cat /proc/net/snmp | awk '
    /^IcmpMsg:/ { if (!h) { for (i=2;i<=NF;i++) c[$i]=i; h=1 }
                  else { print (("InType0" in c) ? $(c["InType0"]) : 0); p=1 } }
    END { if (!p) print 0 }'
}
b=$(attacker_replies)
ip netns exec attacker ping -b -c1 -W1 "$AMP_BCAST" >/dev/null 2>&1 || true
sleep 0.3
a=$(attacker_replies)
got=$((a - b))
echo "    one directed-broadcast request drew $got echo-replies (expected $AMP_COUNT)"
if [ "$got" -ge 2 ]; then
  echo "    => amplification path is LIVE"
else
  echo "    => WARNING: path not amplifying; check bc_forwarding / amp sysctls"
fi

echo
echo "[+] Lab is up. Namespaces: router victim attacker $(for i in $(seq 1 "$AMP_COUNT"); do printf 'amp%s ' "$i"; done)"
echo "    Next: sudo bash measure.sh        # spoofed attack + amplification factor"
echo "          sudo bash defend.sh         # apply fixes, then re-run measure.sh"
echo "          sudo bash teardown_lab.sh   # remove everything"
