#!/usr/bin/env bash
# run_all.sh — one command that reproduces the whole attack/defense matrix and
# regenerates results/summary.tsv from scratch (plus a pcap per run).
#
#   sudo bash run_all.sh
#
# It builds the lab, then for BOTH protocols (Smurf/ICMP and Fraggle/UDP) runs the
# vulnerable baseline and every defense layer, reverting between layers so each is
# measured in isolation. The scaling sweep is a separate experiment — run
# 'sudo bash scale_test.sh' (optionally AMP_COUNT=8 ...) for that.
#
# The point of the matrix (all verified by the numbers it prints):
#   * both protocols amplify by the same factor (~= AMP_COUNT);
#   * router bc_forwarding=0 and edge source-guard each stop BOTH;
#   * the ICMP amp fix stops only Smurf; stopping the UDP echo service stops only
#     Fraggle — i.e. the misconfiguration, not the protocol, is the vulnerability.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lab.env
source "$SCRIPT_DIR/lab.env"

if [ "$(id -u)" -ne 0 ]; then exec sudo -E bash "$0" "$@"; fi

COUNT="${COUNT:-100}"
RATE="${RATE:-50}"
RESULTS="$SCRIPT_DIR/$RESULTS_DIR_NAME"

# run <proto> <engine> <label>  -> prints the factor; measure.sh logs to summary.tsv
run() {
  local proto="$1" engine="$2" label="$3" f
  f="$(bash "$SCRIPT_DIR/measure.sh" --proto "$proto" --engine "$engine" \
        --count "$COUNT" --rate "$RATE" --label "$label" 2>/dev/null \
        | awk '/AMPLIFICATION/{print $3}')"
  printf '  %-36s %-5s %-3s factor=%s\n' "$label" "$proto" "$engine" "$f"
}

echo "############################################################"
echo "# Smurf/Fraggle lab — full matrix ($AMP_COUNT amplifiers, $COUNT req/run)"
echo "############################################################"

echo "[*] Building a fresh, fully-vulnerable lab..."
bash "$SCRIPT_DIR/setup_lab.sh" >/dev/null

# Start summary.tsv clean so this run is the whole file.
rm -f "$RESULTS/summary.tsv"

echo
echo "== Vulnerable baseline (both senders, both protocols) =="
run icmp py vulnerable-icmp-py
run icmp c  vulnerable-icmp-c
run udp  py vulnerable-fraggle-py
run udp  c  vulnerable-fraggle-c

echo
echo "== Defense: router (bc_forwarding=0) — expect BOTH collapse to 0 =="
bash "$SCRIPT_DIR/defend.sh" router >/dev/null
run icmp py defended-router-icmp
run udp  py defended-router-fraggle

echo
echo "== Defense: amps (icmp ignore) — expect Smurf 0, Fraggle unchanged =="
bash "$SCRIPT_DIR/defend.sh" revert >/dev/null
bash "$SCRIPT_DIR/defend.sh" amps >/dev/null
run icmp py defended-amps-icmp
run udp  py defended-amps-fraggle

echo
echo "== Defense: service (stop UDP echo) — expect Fraggle 0, Smurf unchanged =="
bash "$SCRIPT_DIR/defend.sh" revert >/dev/null
bash "$SCRIPT_DIR/defend.sh" service >/dev/null
run icmp py defended-service-icmp
run udp  py defended-service-fraggle

echo
echo "== Defense: spoofguard (edge source guard) — expect BOTH collapse to 0 =="
bash "$SCRIPT_DIR/defend.sh" revert >/dev/null
bash "$SCRIPT_DIR/defend.sh" spoofguard >/dev/null
run icmp py defended-spoofguard-icmp
run udp  py defended-spoofguard-fraggle

echo
echo "== Revert -> recheck (still vulnerable) =="
bash "$SCRIPT_DIR/defend.sh" revert >/dev/null
run icmp py vulnerable-recheck-icmp
run udp  py vulnerable-recheck-fraggle

echo
echo "[*] Tearing the lab down..."
bash "$SCRIPT_DIR/teardown_lab.sh" >/dev/null

echo
echo "[+] Full matrix complete. Machine-readable results: $RESULTS/summary.tsv"
column -t -s $'\t' "$RESULTS/summary.tsv" 2>/dev/null || cat "$RESULTS/summary.tsv"
