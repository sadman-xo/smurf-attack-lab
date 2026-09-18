#!/usr/bin/env bash
# defend.sh — apply (or revert) the defenses, one layer at a time or all at once.
#
#   both        (default) the two classic Smurf fixes: router + amps
#   router      directed-broadcast forwarding off        (UNIVERSAL: stops Smurf AND Fraggle)
#   amps        amplifiers ignore broadcast echo         (ICMP-only: Smurf, not Fraggle)
#   service     stop the UDP echo responders             (UDP-only: Fraggle, not Smurf)
#   spoofguard  edge IP source guard at the attacker port(UNIVERSAL: stops the spoof itself)
#   all         every layer above (defence in depth)
#   revert      re-enable the full vulnerable config (to demo the attack again)
#
# Why several layers:
#   * router (bc_forwarding=0) is the single root-cause fix — one packet stays one
#     packet regardless of L4 protocol, so it kills Smurf and Fraggle alike.
#   * amps (icmp_echo_ignore_broadcasts=1) only silences ICMP; a Fraggle over UDP
#     sails straight past it — a concrete demo that the protocol isn't the bug.
#   * service (stop echo) is the UDP mirror image: it stops Fraggle but not Smurf.
#   * spoofguard drops the forged source at the access port (BCP 38 family), so the
#     attack never even reaches the router. Note it works here because we filter the
#     attacker's own switch port; plain subnet uRPF would NOT catch this particular
#     spoof, since the forged victim address is itself valid on the victim subnet.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lab.env
source "$SCRIPT_DIR/lab.env"

if [ "$(id -u)" -ne 0 ]; then exec sudo -E bash "$0" "$@"; fi

MODE="${1:-both}"
MODE="${MODE#--}"   # accept --both / --router / etc.

router_fix() {   # 0 = secure, 1 = vulnerable
  local v="$1"
  ip netns exec "$NS_ROUTER" sysctl -qw "net.ipv4.conf.all.bc_forwarding=$v"
  ip netns exec "$NS_ROUTER" sysctl -qw "net.ipv4.conf.${BR_AMP}.bc_forwarding=$v"
  ip netns exec "$NS_ROUTER" sysctl -qw "net.ipv4.conf.${BR_VIC}.bc_forwarding=$v"
}
amp_fix() {      # 1 = secure (ignore), 0 = vulnerable (answer)
  local v="$1"
  for i in $(seq 1 "$AMP_COUNT"); do
    ip netns exec "amp$i" sysctl -qw "net.ipv4.icmp_echo_ignore_broadcasts=$v"
  done
}
stop_responders() {
  pkill -f "$SCRIPT_DIR/src/udp_echo.py" 2>/dev/null || true
}
start_responders() {
  stop_responders
  for i in $(seq 1 "$AMP_COUNT"); do
    ip netns exec "amp$i" setsid python3 "$SCRIPT_DIR/src/udp_echo.py" "$FRAGGLE_PORT" \
      </dev/null >/dev/null 2>&1 &
  done
  disown -a 2>/dev/null || true
  sleep 0.3
}
sg_supported() {
  # Does this kernel's nftables have the bridge family? (Absent on e.g. Cloud Shell.)
  ip netns exec "$NS_ROUTER" nft add table bridge "${SG_TABLE}_probe" >/dev/null 2>&1 || return 1
  ip netns exec "$NS_ROUTER" nft delete table bridge "${SG_TABLE}_probe" >/dev/null 2>&1 || true
  return 0
}
spoofguard_on() {
  if ! sg_supported; then
    echo "[!] spoofguard unavailable: this kernel lacks the nftables bridge family." >&2
    echo "    It is needed only for this one defense; every attack and the router/amps/" >&2
    echo "    service defenses still work. Run this layer on a full Linux kernel." >&2
    return 3
  fi
  # nftables bridge family: drop any frame entering the attacker's access port whose
  # IP source isn't the attacker's real address. Hook 'prerouting' because the forged
  # broadcast is delivered up to the bridge's own L3 interface, not bridged port->port.
  ip netns exec "$NS_ROUTER" nft delete table bridge "$SG_TABLE" 2>/dev/null || true
  ip netns exec "$NS_ROUTER" nft -f - <<EOF
table bridge $SG_TABLE {
    chain pre {
        type filter hook prerouting priority -300; policy accept;
        iif "$ATT_PORT" ip saddr != $ATTACKER_IP counter drop
    }
}
EOF
}
spoofguard_off() {
  ip netns exec "$NS_ROUTER" nft delete table bridge "$SG_TABLE" 2>/dev/null || true
}

case "$MODE" in
  both)
    router_fix 0; amp_fix 1
    echo "[+] Secured (both classic fixes): router bc_forwarding=0 AND amplifiers ignore broadcast echo."
    ;;
  router)
    router_fix 0
    echo "[+] Secured (router): bc_forwarding=0 — stops Smurf AND Fraggle at the root."
    ;;
  amps)
    amp_fix 1
    echo "[+] Secured (amps): icmp_echo_ignore_broadcasts=1 — stops Smurf; Fraggle (UDP) still amplifies."
    ;;
  service)
    stop_responders
    echo "[+] Secured (service): UDP echo responders stopped — stops Fraggle; Smurf (ICMP) still amplifies."
    ;;
  spoofguard|edge)
    if spoofguard_on; then
      echo "[+] Secured (spoofguard): edge IP source guard on '$ATT_PORT' — drops the forged source, stops both."
    else
      exit 3   # unsupported kernel; caller (e.g. run_all.sh) treats this as "skip"
    fi
    ;;
  all)
    router_fix 0; amp_fix 1; stop_responders
    if spoofguard_on; then
      echo "[+] Secured (ALL layers): router + amps + service + edge source guard (defence in depth)."
    else
      echo "[+] Secured (router + amps + service). spoofguard skipped: no nftables bridge family here."
    fi
    ;;
  revert)
    router_fix 1; amp_fix 0; spoofguard_off; start_responders
    echo "[!] Reverted to the VULNERABLE configuration (for re-demonstration)."
    ;;
  *)
    echo "usage: $0 [both|router|amps|service|spoofguard|all|revert]" >&2
    exit 2
    ;;
esac

echo "    Re-run 'sudo bash measure.sh' (ICMP) or 'sudo bash measure.sh --proto udp' (Fraggle) to compare."
