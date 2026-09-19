#!/usr/bin/env bash
# telemetry/monitor-kernel-drops.sh
# Streams kernel ring buffer messages filtered for nf_conntrack drops and netfilter table saturation.

set -euo pipefail

CONTAINER="${1:-conntrack-lab-worker}"

RESET="\033[0m"
BOLD="\033[1m"
RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
CYAN="\033[1;36m"
WHITE_BG="\033[47;30m"
RED_BG="\033[41;37;1m"

CONTAINER="${1:-}"
if [ -z "$CONTAINER" ]; then
  CONTAINER=$(docker ps --filter "name=conntrack-lab-worker" --format "{{.Names}}" 2>/dev/null | head -n 1 || true)
  if [ -z "$CONTAINER" ]; then
    CONTAINER=$(docker ps --filter "name=conntrack-lab" --format "{{.Names}}" 2>/dev/null | head -n 1 || true)
  fi
  if [ -z "$CONTAINER" ]; then
    CONTAINER="conntrack-lab-worker"
  fi
fi

if ! docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null | grep -q "true"; then
  echo -e "\n${RED}${BOLD}╔═══════════════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${RED}${BOLD}║  [ERROR] Kind Node Container '${CONTAINER}' is NOT running!        ║${RESET}"
  echo -e "${RED}${BOLD}╚═══════════════════════════════════════════════════════════════════╝${RESET}"
  echo -e "${YELLOW}The Kind cluster must be running before kernel drops can be monitored.${RESET}\n"
  echo -e "👉 ${BOLD}Run this command first to spin up your cluster:${RESET}"
  echo -e "   ${GREEN}${BOLD}bash setup/start-cluster.sh${RESET}\n"
  exit 1
fi

echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║  LIVE KERNEL MONITOR: NETFILTER CONNTRACK DROPS (dmesg -w)                       ║${RESET}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════════════════════════╝${RESET}"
echo -e " Node: ${BOLD}${CONTAINER}${RESET} | Filter: ${BOLD}'table full, dropping packet'${RESET}"
echo -e " Listening for kernel netfilter drops in real time..."
echo -e "----------------------------------------------------------------------------------"

# Follow kernel dmesg stream inside worker container
docker exec -i "${CONTAINER}" bash -c '
  if dmesg --help 2>&1 | grep -q -- "-w"; then
    dmesg -wT 2>/dev/null || dmesg -w 2>/dev/null || dmesg
  else
    # Fallback to polling dmesg if -w not supported in current environment
    while true; do
      dmesg | tail -n 20
      sleep 2
    done
  fi
' | awk -v RESET="$RESET" -v BOLD="$BOLD" -v RED="$RED" -v RED_BG="$RED_BG" -v YELLOW="$YELLOW" '
/table full.*dropping packet|nf_conntrack: table full|netfilter/ {
  print RED_BG " 🚨 KERNEL DROP DETECTED " RESET " " RED BOLD $0 RESET
  fflush()
  next
}
/drop/ {
  print YELLOW "[KERNEL WARNING] " $0 RESET
  fflush()
  next
}
{
  # If running in live stream, suppress unrelated kernel noise
}
'
