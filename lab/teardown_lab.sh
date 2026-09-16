#!/usr/bin/env bash
# teardown_lab.sh — delete every namespace the lab created.
# Deleting a namespace removes the interfaces inside it; veth peers vanish with
# their partner, and the bridges (which live in the router ns) go with it.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lab.env
source "$SCRIPT_DIR/lab.env"

if [ "$(id -u)" -ne 0 ]; then exec sudo -E bash "$0" "$@"; fi

for i in $(seq 1 "$AMP_COUNT"); do
  ip netns del "amp$i" 2>/dev/null || true
done
for ns in attacker victim "$NS_ROUTER"; do
  ip netns del "$ns" 2>/dev/null || true
done

# Remove any stray veths a crashed setup may have left in the root namespace
# (a healthy run has none — deleting a namespace already reaps its veth pairs).
strays="r-vic r-att p-victim p-attacker"
for i in $(seq 1 "$AMP_COUNT"); do strays="$strays r-amp$i p-amp$i"; done
for l in $strays; do ip link del "$l" 2>/dev/null || true; done

echo "[*] Lab removed."
