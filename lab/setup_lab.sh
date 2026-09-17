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

echo "[*] Starting the Fraggle amplifier service (UDP echo) on each amplifier..."
# A tiny UDP echo server (src/udp_echo.py) stands in for the historically common
# echo/chargen services Fraggle abused. It is detached with setsid so it survives
# this script exiting; teardown/defend stop it by its command line (pkill -f).
for i in $(seq 1 "$AMP_COUNT"); do
  ip netns exec "amp$i" setsid python3 "$SCRIPT_DIR/src/udp_echo.py" "$FRAGGLE_PORT" \
    </dev/null >/dev/null 2>&1 &
done
disown -a 2>/dev/null || true
sleep 0.3

echo "[*] Baseline connectivity check (normal unicast)..."
# ping (iputils) is optional: if it is missing we fall back to a raw-socket probe so
# setup still self-verifies on minimal images.
HAVE_PING=0; command -v ping >/dev/null 2>&1 && HAVE_PING=1
chk() { # <ns> <target> <label>
  local ok=1
  if [ "$HAVE_PING" -eq 1 ]; then
    ip netns exec "$1" ping -c1 -W1 "$2" >/dev/null 2>&1 || ok=0
  else
    # No ping: send one raw ICMP echo and look for the reply in the kernel counter.
    ip netns exec "$1" python3 "$SCRIPT_DIR/src/smurf.py" \
      --victim "$(ip -n "$1" -4 addr show eth0 | awk '/inet /{print $2}' | cut -d/ -f1)" \
      --broadcast "$2" --count 1 --rate 1 >/dev/null 2>&1 || ok=0
    # (best-effort reachability; the amplification self-test below is authoritative)
  fi
  [ "$ok" -eq 1 ] && echo "    OK   $3" || echo "    FAIL $3"
}
if [ "$HAVE_PING" -eq 1 ]; then
  chk attacker "$ROUTER_VIC_IP"   "attacker -> router"
  chk attacker "${AMP_SUBNET}.11" "attacker -> amp1 (through router)"
  chk victim   "${AMP_SUBNET}.11" "victim   -> amp1 (through router)"
else
  echo "    (ping not installed -> skipping unicast check; see self-test below)"
fi

echo "[*] Amplification self-test (real, non-spoofed broadcast from attacker)..."
# One request to the directed broadcast should draw AMP_COUNT replies. We read the
# attacker's own kernel counters after the probe (a single -c1 ping would exit on the
# FIRST reply and miss the rest). ICMP uses ping -b when present, else our own raw
# sender with a NON-spoofed source; the Fraggle check uses the raw UDP sender.
attacker_intype0() {  # ICMP echo-replies received at the attacker
  ip netns exec attacker cat /proc/net/snmp | awk '
    /^IcmpMsg:/ { if (!h) { for (i=2;i<=NF;i++) c[$i]=i; h=1 }
                  else { print (("InType0" in c) ? $(c["InType0"]) : 0); p=1 } }
    END { if (!p) print 0 }'
}
attacker_udp_noports() {  # UDP replies to the attacker's (closed) source port
  ip netns exec attacker cat /proc/net/snmp | awk '
    /^Udp:/ { if (!h) { for (i=2;i<=NF;i++) c[$i]=i; h=1 }
              else print (("NoPorts" in c) ? $(c["NoPorts"]) : 0) }'
}

b=$(attacker_intype0)
if [ "$HAVE_PING" -eq 1 ]; then
  ip netns exec attacker ping -b -c1 -W1 "$AMP_BCAST" >/dev/null 2>&1 || true
else
  ip netns exec attacker python3 "$SCRIPT_DIR/src/smurf.py" \
    --victim "$ATTACKER_IP" --broadcast "$AMP_BCAST" --count 1 --rate 1 >/dev/null 2>&1 || true
fi
sleep 0.3
got_icmp=$(( $(attacker_intype0) - b ))
echo "    Smurf  (ICMP): one broadcast request drew $got_icmp echo-replies (expected $AMP_COUNT)"

b=$(attacker_udp_noports)
ip netns exec attacker python3 "$SCRIPT_DIR/src/fraggle.py" \
  --victim "$ATTACKER_IP" --broadcast "$AMP_BCAST" --dport "$FRAGGLE_PORT" \
  --sport "$FRAGGLE_SPORT" --count 1 --rate 1 >/dev/null 2>&1 || true
sleep 0.3
got_udp=$(( $(attacker_udp_noports) - b ))
echo "    Fraggle (UDP): one broadcast request drew $got_udp echo-replies (expected $AMP_COUNT)"

if [ "$got_icmp" -ge 2 ] && [ "$got_udp" -ge 2 ]; then
  echo "    => amplification path is LIVE for both Smurf and Fraggle"
else
  echo "    => WARNING: path not fully amplifying; check bc_forwarding / amp sysctls / responders"
fi

echo
echo "[+] Lab is up. Namespaces: router victim attacker $(for i in $(seq 1 "$AMP_COUNT"); do printf 'amp%s ' "$i"; done)"
echo "    Next: sudo bash measure.sh        # spoofed attack + amplification factor"
echo "          sudo bash defend.sh         # apply fixes, then re-run measure.sh"
echo "          sudo bash teardown_lab.sh   # remove everything"
