#!/usr/bin/env bash
# measure.sh — run the spoofed attack and report the amplification factor.
#
#   sudo bash measure.sh [--proto icmp|udp] [--engine py|c]
#                        [--count N] [--rate PPS] [--size B] [--label TXT]
#
# Counting is done at the VICTIM in two independent ways so it works with or
# without tcpdump installed:
#
#   ICMP (Smurf):
#     1. tcpdump pcap of ICMP echo-replies on the victim's link  (if tcpdump present)
#     2. kernel counter  IcmpMsg InType0  (echo-reply messages received)
#        cross-checked against Icmp InEchoReps
#   UDP (Fraggle):
#     1. tcpdump pcap of UDP replies to the spoofed source port  (if tcpdump present)
#     2. kernel counter  Udp NoPorts  — the victim isn't listening on that port, so
#        every echoed reply is counted here (deterministic, no listener needed)
#
# amplification factor = replies_received / requests_sent   (~= number of amps)
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
LABEL="run"
while [ $# -gt 0 ]; do
  case "$1" in
    --proto)  PROTO="$2";  shift 2;;
    --engine) ENGINE="$2"; shift 2;;
    --count)  COUNT="$2";  shift 2;;
    --rate)   RATE="$2";   shift 2;;
    --size)   SIZE="$2";   shift 2;;
    --label)  LABEL="$2";  shift 2;;
    *) echo "unknown option: $1" >&2; exit 2;;
  esac
done
case "$PROTO" in icmp|udp) ;; *) echo "unknown proto: $PROTO (use icmp or udp)" >&2; exit 2;; esac

RESULTS="$SCRIPT_DIR/$RESULTS_DIR_NAME"
mkdir -p "$RESULTS"
STAMP="$(date +%Y%m%d-%H%M%S)"
PCAP="$RESULTS/${LABEL}-${STAMP}.pcap"

# --- kernel counters, read inside the victim ns ---
snmp_field() {  # <line-prefix> <field-name>  -> counter value (0 if column absent)
  ip netns exec victim cat /proc/net/snmp | awk -v pfx="$1:" -v key="$2" '
    $1==pfx { if (!h) { for (i=2;i<=NF;i++) c[$i]=i; h=1 }
              else { print ((key in c) ? $(c[key]) : 0); p=1 } }
    END { if (!p) print 0 }'
}

if [ "$PROTO" = icmp ]; then
  KLABEL1="IcmpMsg InType0"; KLABEL2="Icmp InEchoReps"
  kcount1() { snmp_field IcmpMsg InType0; }
  kcount2() { snmp_field Icmp InEchoReps; }
  TD_FILTER='icmp'
  PCAP_FILTER='icmp[icmptype] = icmp-echoreply'
else
  KLABEL1="Udp NoPorts"; KLABEL2="Udp InErrors"
  kcount1() { snmp_field Udp NoPorts; }
  kcount2() { snmp_field Udp InErrors; }
  TD_FILTER="udp"
  PCAP_FILTER="udp and dst port $FRAGGLE_SPORT"
fi

HAVE_TCPDUMP=0
command -v tcpdump >/dev/null 2>&1 && HAVE_TCPDUMP=1

echo "[*] proto=$PROTO label=$LABEL engine=$ENGINE count=$COUNT rate=${RATE}pps size=${SIZE}B"
before_k1="$(kcount1)"
before_k2="$(kcount2)"

TD_PID=""
if [ "$HAVE_TCPDUMP" -eq 1 ]; then
  ip netns exec victim tcpdump -ni eth0 -w "$PCAP" "$TD_FILTER" >/dev/null 2>&1 &
  TD_PID=$!
  sleep 0.5   # let tcpdump attach before traffic starts
else
  echo "    (tcpdump not installed -> using kernel counters only; pcap skipped)"
fi

# --- fire the attack ---
bash "$SCRIPT_DIR/run_attack.sh" --proto "$PROTO" --engine "$ENGINE" \
  --count "$COUNT" --rate "$RATE" --size "$SIZE"

sleep 1  # let the last replies arrive before snapshotting

if [ -n "$TD_PID" ]; then
  kill -INT "$TD_PID" 2>/dev/null || true
  wait "$TD_PID" 2>/dev/null || true
fi

after_k1="$(kcount1)"
after_k2="$(kcount2)"
replies_k1=$((after_k1 - before_k1))
replies_k2=$((after_k2 - before_k2))

pcap_replies="-"
if [ "$HAVE_TCPDUMP" -eq 1 ] && [ -f "$PCAP" ]; then
  pcap_replies="$(tcpdump -r "$PCAP" -n "$PCAP_FILTER" 2>/dev/null | wc -l | tr -d ' ')"
fi

# primary reply count: prefer pcap, else the primary kernel counter
replies="$replies_k1"
[ "$pcap_replies" != "-" ] && replies="$pcap_replies"
factor="$(awk -v r="$replies" -v c="$COUNT" 'BEGIN { if (c>0) printf "%.2f", r/c; else print "n/a" }')"

echo
printf '  %-28s %s\n' "requests sent"           "$COUNT"
printf '  %-28s %s\n' "replies (pcap)"          "$pcap_replies"
printf '  %-28s %s\n' "replies ($KLABEL1)"      "$replies_k1"
printf '  %-28s %s\n' "replies ($KLABEL2)"      "$replies_k2"
printf '  %-28s %s\n' "AMPLIFICATION FACTOR"    "$factor"
echo

LOG="$RESULTS/summary.tsv"
[ -f "$LOG" ] || printf 'timestamp\tproto\tlabel\tengine\tsent\tpcap\tkernel\tfactor\n' >"$LOG"
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
  "$STAMP" "$PROTO" "$LABEL" "$ENGINE" "$COUNT" "$pcap_replies" "$replies_k1" "$factor" >>"$LOG"
echo "[+] appended to $LOG"
if [ "$pcap_replies" != "-" ]; then echo "[+] pcap: $PCAP"; fi
exit 0   # never let a false final test leave a non-zero status (e.g. no tcpdump)
