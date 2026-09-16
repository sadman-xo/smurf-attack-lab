#!/usr/bin/env bash
# measure.sh — run the spoofed attack and report the amplification factor.
#
#   sudo bash measure.sh [--engine py|c] [--count N] [--rate PPS] [--size B] [--label TXT]
#
# Counting is done at the VICTIM in two independent ways so it works with or
# without tcpdump installed:
#   1. tcpdump pcap of ICMP echo-replies on the victim's link  (if tcpdump present)
#   2. the victim's kernel ICMP counters in /proc/net/snmp (always available):
#        IcmpMsg InType0  = echo-reply messages received  (primary counter)
#        Icmp    InEchoReps = classic echo-reply counter    (cross-check)
#
# amplification factor = replies_received / requests_sent   (~= number of amps)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lab.env
source "$SCRIPT_DIR/lab.env"

if [ "$(id -u)" -ne 0 ]; then exec sudo -E bash "$0" "$@"; fi

ENGINE=py
COUNT=100
RATE=50
SIZE=0
LABEL="run"
while [ $# -gt 0 ]; do
  case "$1" in
    --engine) ENGINE="$2"; shift 2;;
    --count)  COUNT="$2";  shift 2;;
    --rate)   RATE="$2";   shift 2;;
    --size)   SIZE="$2";   shift 2;;
    --label)  LABEL="$2";  shift 2;;
    *) echo "unknown option: $1" >&2; exit 2;;
  esac
done

RESULTS="$SCRIPT_DIR/$RESULTS_DIR_NAME"
mkdir -p "$RESULTS"
STAMP="$(date +%Y%m%d-%H%M%S)"
PCAP="$RESULTS/${LABEL}-${STAMP}.pcap"

# --- kernel ICMP counters, read inside the victim ns ---
victim_intype0() {  # echo-replies received, by ICMP type (absent column => 0)
  ip netns exec victim cat /proc/net/snmp | awk '
    /^IcmpMsg:/ { if (!h) { for (i=2;i<=NF;i++) c[$i]=i; h=1 }
                  else { print (("InType0" in c) ? $(c["InType0"]) : 0); p=1 } }
    END { if (!p) print 0 }'
}
victim_inechoreps() {  # classic Icmp InEchoReps (fixed column, always present)
  ip netns exec victim cat /proc/net/snmp | awk '
    /^Icmp:/ { if (!h) { for (i=2;i<=NF;i++) c[$i]=i; h=1 }
               else print (("InEchoReps" in c) ? $(c["InEchoReps"]) : 0) }'
}

HAVE_TCPDUMP=0
command -v tcpdump >/dev/null 2>&1 && HAVE_TCPDUMP=1

echo "[*] label=$LABEL engine=$ENGINE count=$COUNT rate=${RATE}pps size=${SIZE}B"
before_t0="$(victim_intype0)"
before_er="$(victim_inechoreps)"

TD_PID=""
if [ "$HAVE_TCPDUMP" -eq 1 ]; then
  ip netns exec victim tcpdump -ni eth0 -w "$PCAP" 'icmp' >/dev/null 2>&1 &
  TD_PID=$!
  sleep 0.5   # let tcpdump attach before traffic starts
else
  echo "    (tcpdump not installed -> using kernel counters only; pcap skipped)"
fi

# --- fire the attack ---
bash "$SCRIPT_DIR/run_attack.sh" --engine "$ENGINE" --count "$COUNT" --rate "$RATE" --size "$SIZE"

sleep 1  # let the last replies arrive before snapshotting

if [ -n "$TD_PID" ]; then
  kill -INT "$TD_PID" 2>/dev/null || true
  wait "$TD_PID" 2>/dev/null || true
fi

after_t0="$(victim_intype0)"
after_er="$(victim_inechoreps)"
replies_t0=$((after_t0 - before_t0))
replies_er=$((after_er - before_er))

pcap_replies="-"
if [ "$HAVE_TCPDUMP" -eq 1 ] && [ -f "$PCAP" ]; then
  pcap_replies="$(tcpdump -r "$PCAP" -n 'icmp[icmptype]==icmp-echoreply' 2>/dev/null | wc -l | tr -d ' ')"
fi

# primary reply count: prefer pcap, else the by-type counter
replies="$replies_t0"
[ "$pcap_replies" != "-" ] && replies="$pcap_replies"
factor="$(awk -v r="$replies" -v c="$COUNT" 'BEGIN { if (c>0) printf "%.2f", r/c; else print "n/a" }')"

echo
printf '  %-28s %s\n' "requests sent"                 "$COUNT"
printf '  %-28s %s\n' "replies (pcap echo-reply)"     "$pcap_replies"
printf '  %-28s %s\n' "replies (IcmpMsg InType0)"     "$replies_t0"
printf '  %-28s %s\n' "replies (Icmp InEchoReps)"     "$replies_er"
printf '  %-28s %s\n' "AMPLIFICATION FACTOR"          "$factor"
echo

LOG="$RESULTS/summary.tsv"
[ -f "$LOG" ] || printf 'timestamp\tlabel\tengine\tsent\tpcap\tintype0\tinechoreps\tfactor\n' >"$LOG"
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$STAMP" "$LABEL" "$ENGINE" "$COUNT" "$pcap_replies" "$replies_t0" "$replies_er" "$factor" >>"$LOG"
echo "[+] appended to $LOG"
[ "$pcap_replies" != "-" ] && echo "[+] pcap: $PCAP"
