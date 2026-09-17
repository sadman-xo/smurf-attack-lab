#!/usr/bin/env bash
# preflight.sh — check that THIS kernel/host can actually run the lab.
#
#   sudo bash preflight.sh
#
# The lab needs three kernel features that some environments (notably the default
# WSL2 Microsoft kernel) ship without: network namespaces, Linux bridges, and
# directed-broadcast forwarding (net.ipv4.conf.*.bc_forwarding). This script builds a
# throwaway namespace, tries each feature, and prints a PASS/FAIL verdict with a hint
# for anything missing. It changes nothing permanent (its scratch namespace is deleted
# at the end).
set -uo pipefail

if [ "$(id -u)" -ne 0 ]; then exec sudo -E bash "$0" "$@"; fi

PASS=0; FAIL=0; PROBE=__preflight_probe
pass() { printf '  \033[32mPASS\033[0m  %s\n' "$1"; PASS=$((PASS+1)); }
fail() { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; [ -n "${2:-}" ] && printf '        -> %s\n' "$2"; FAIL=$((FAIL+1)); }
info() { printf '  ....  %s\n' "$1"; }

cleanup() { ip netns del "$PROBE" 2>/dev/null || true; ip link del __pf_ve0 2>/dev/null || true; }
trap cleanup EXIT

echo "== Environment =="
info "kernel : $(uname -r)"
if grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
  info "host   : WSL2 detected — the DEFAULT WSL kernel often lacks bridge + bc_forwarding."
  info "         If checks below fail, build/use a custom WSL kernel, or run the lab in a"
  info "         real Linux VM/container instead (see hints)."
else
  info "host   : native Linux (or VM/container)"
fi

echo "== Required tools =="
command -v ip      >/dev/null 2>&1 && pass "iproute2 (ip) present"      || fail "iproute2 (ip) missing"      "apt-get install -y iproute2"
command -v python3 >/dev/null 2>&1 && pass "python3 present"            || fail "python3 missing"            "apt-get install -y python3"
command -v gcc     >/dev/null 2>&1 && pass "gcc present (for C senders)" || fail "gcc missing"                "apt-get install -y build-essential"

echo "== Required kernel features =="

# 1) network namespaces
if ip netns add "$PROBE" 2>/dev/null; then
  pass "network namespaces (ip netns)"
  ip netns exec "$PROBE" ip link set lo up 2>/dev/null
else
  fail "network namespaces (ip netns add failed)" "kernel needs CONFIG_NET_NS; not usable in this environment"
fi

# 2) bridge device  (the classic WSL2 gap)
if ip netns list 2>/dev/null | grep -q "^$PROBE"; then
  if ip -n "$PROBE" link add br-pf type bridge 2>/dev/null; then
    pass "Linux bridge device (type bridge)"
  else
    fail "Linux bridge device (ip link add type bridge failed)" \
         "kernel lacks CONFIG_BRIDGE — the default WSL2 kernel is the usual culprit"
  fi

  # 3) veth pair
  if ip -n "$PROBE" link add v0 type veth peer name v1 2>/dev/null; then
    pass "veth pair (type veth)"
  else
    fail "veth pair (type veth failed)" "kernel lacks CONFIG_VETH"
  fi

  # 4) bc_forwarding — the feature the whole attack depends on
  if ip netns exec "$PROBE" sysctl -qw net.ipv4.conf.all.bc_forwarding=1 2>/dev/null \
     && [ "$(ip netns exec "$PROBE" sysctl -n net.ipv4.conf.all.bc_forwarding 2>/dev/null)" = "1" ]; then
    pass "directed-broadcast forwarding (bc_forwarding)"
  else
    fail "directed-broadcast forwarding (bc_forwarding missing/unsettable)" \
         "kernel too old (<5.1) or built without it — the amplification cannot work without this"
  fi

  # 5) ip_forward + icmp_echo_ignore_broadcasts (should exist everywhere)
  ip netns exec "$PROBE" sysctl -qw net.ipv4.ip_forward=1 2>/dev/null \
    && pass "IPv4 forwarding (ip_forward)" || fail "ip_forward unsettable" "unexpected — check kernel"
  ip netns exec "$PROBE" sysctl -qw net.ipv4.icmp_echo_ignore_broadcasts=0 2>/dev/null \
    && pass "broadcast-echo control (icmp_echo_ignore_broadcasts)" \
    || fail "icmp_echo_ignore_broadcasts unsettable" "unexpected — check kernel"
fi

echo "== Optional (measurement / extra defense) =="
command -v tcpdump >/dev/null 2>&1 && pass "tcpdump (pcap capture)" || info "tcpdump absent — fine, kernel counters are used instead (apt-get install -y tcpdump)"
command -v ping    >/dev/null 2>&1 && pass "ping (unicast reachability check)" || info "ping absent — fine, a raw-socket probe is used instead (apt-get install -y iputils-ping)"
if ip netns list 2>/dev/null | grep -q "^$PROBE"; then
  if command -v nft >/dev/null 2>&1 && ip netns exec "$PROBE" nft add table bridge pf 2>/dev/null; then
    pass "nftables bridge family (for the 'spoofguard' defense)"
    ip netns exec "$PROBE" nft delete table bridge pf 2>/dev/null || true
  else
    info "nftables bridge family absent — every attack + other defenses still work; only 'defend.sh spoofguard' needs it"
  fi
fi

echo
echo "== Verdict =="
if [ "$FAIL" -eq 0 ]; then
  echo "  All required checks passed ($PASS ok). This host can run the lab:"
  echo "    sudo bash setup_lab.sh && sudo bash run_all.sh"
else
  echo "  $FAIL required check(s) FAILED, $PASS passed."
  echo "  This host cannot run the lab as-is. Most common on WSL2: the default kernel"
  echo "  lacks CONFIG_BRIDGE and/or bc_forwarding. Options:"
  echo "    1) Run the lab in a real Linux VM (e.g. multipass/VirtualBox) or a container"
  echo "       on a full kernel, or on any cloud Linux box."
  echo "    2) On WSL2, replace the kernel with one built with CONFIG_BRIDGE=y,"
  echo "       CONFIG_VETH=y and directed-broadcast forwarding, via .wslconfig."
  exit 1
fi
