#!/usr/bin/env bash
# defend.sh — flip the vulnerable settings back to secure defaults (or revert).
#
#   both        (default) apply BOTH fixes below
#   router      only the router fix
#   amps        only the amplifier fix
#   revert      re-enable the vulnerable config (to demo the attack again)
#
# Fix 1 (router): net.ipv4.conf.*.bc_forwarding=0  -> a directed broadcast is no
#                 longer forwarded onto the amp subnet: one packet stays one packet.
# Fix 2 (amps)  : net.ipv4.icmp_echo_ignore_broadcasts=1 -> hosts stay silent even
#                 if a broadcast echo reaches them.
# Either fix alone collapses the flood; together they are defence in depth. The
# same fixes also stop the UDP "Fraggle" variant -- misconfig matters, not protocol.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lab.env
source "$SCRIPT_DIR/lab.env"

if [ "$(id -u)" -ne 0 ]; then exec sudo -E bash "$0" "$@"; fi

MODE="${1:-both}"
MODE="${MODE#--}"   # accept --both / --router / etc.

router_fix() {
  local v="$1"   # 0 = secure, 1 = vulnerable
  ip netns exec "$NS_ROUTER" sysctl -qw "net.ipv4.conf.all.bc_forwarding=$v"
  ip netns exec "$NS_ROUTER" sysctl -qw "net.ipv4.conf.${BR_AMP}.bc_forwarding=$v"
  ip netns exec "$NS_ROUTER" sysctl -qw "net.ipv4.conf.${BR_VIC}.bc_forwarding=$v"
}
amp_fix() {
  local v="$1"   # 1 = secure (ignore), 0 = vulnerable (answer)
  for i in $(seq 1 "$AMP_COUNT"); do
    ip netns exec "amp$i" sysctl -qw "net.ipv4.icmp_echo_ignore_broadcasts=$v"
  done
}

case "$MODE" in
  both)
    router_fix 0; amp_fix 1
    echo "[+] Secured: router bc_forwarding=0 AND amplifiers ignore broadcast echo."
    ;;
  router)
    router_fix 0
    echo "[+] Secured (router only): bc_forwarding=0 on the router."
    ;;
  amps)
    amp_fix 1
    echo "[+] Secured (amps only): icmp_echo_ignore_broadcasts=1 on amplifiers."
    ;;
  revert)
    router_fix 1; amp_fix 0
    echo "[!] Reverted to the VULNERABLE configuration (for re-demonstration)."
    ;;
  *)
    echo "usage: $0 [both|router|amps|revert]" >&2
    exit 2
    ;;
esac

echo "    Re-run 'sudo bash measure.sh' to see the before/after difference."
