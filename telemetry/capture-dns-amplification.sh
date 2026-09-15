#!/usr/bin/env bash
# telemetry/capture-dns-amplification.sh
# Uses tcpdump on the worker node to capture UDP port 53 traffic,
# visually highlighting the 5 search paths and parallel A/AAAA glibc queries.

set -euo pipefail

CONTAINER="${1:-conntrack-lab-worker}"

RESET="\033[0m"
BOLD="\033[1m"
RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
CYAN="\033[1;36m"
MAGENTA="\033[1;35m"

if ! docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null | grep -q "true"; then
  echo -e "${RED}[ERROR] Container '${CONTAINER}' is not running.${RESET}"
  exit 1
fi

echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}${BOLD}║  LIVE PACKET INSPECTOR: KUBERNETES DNS AMPLIFICATION (ndots:5 WALKS)             ║${RESET}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════════════════════════╝${RESET}"
echo -e " Capturing on interface: ${BOLD}any${RESET} | Port: ${BOLD}UDP 53${RESET} | Node: ${BOLD}${CONTAINER}${RESET}"
echo -e " Watch for parallel ${BOLD}A${RESET} and ${BOLD}AAAA${RESET} queries across search domains:"
echo -e "   1. <name>.triage-lab.svc.cluster.local."
echo -e "   2. <name>.svc.cluster.local."
echo -e "   3. <name>.cluster.local."
echo -e "   4. <name>."
echo -e "----------------------------------------------------------------------------------"

# Run tcpdump inside the container and pipe through an awk/sed color highlighter
docker exec -i "${CONTAINER}" tcpdump -nn -l -i any udp port 53 2>/dev/null | \
awk -v RESET="$RESET" -v BOLD="$BOLD" -v RED="$RED" -v GREEN="$GREEN" -v YELLOW="$YELLOW" -v CYAN="$CYAN" -v MAGENTA="$MAGENTA" '
{
  line = $0
  # Detect A vs AAAA queries
  if (line ~ / A\? /) {
    record_type = BOLD CYAN "[A-RECORD IPv4]" RESET
  } else if (line ~ / AAAA\? /) {
    record_type = BOLD MAGENTA "[AAAA-RECORD IPv6]" RESET
  } else {
    record_type = "[DNS-RESP]"
  }

  # Highlight search domain suffix
  if (line ~ /triage-lab\.svc\.cluster\.local/) {
    path = YELLOW "[SEARCH-1: ns]" RESET
  } else if (line ~ /svc\.cluster\.local/) {
    path = YELLOW "[SEARCH-2: svc]" RESET
  } else if (line ~ /cluster\.local/) {
    path = YELLOW "[SEARCH-3: cluster]" RESET
  } else if (line ~ /db\.internal\./) {
    path = GREEN "[FINAL-ROOT]" RESET
  } else {
    path = ""
  }

  if (line ~ /NXDomain/) {
    status = RED "[NXDOMAIN - 404]" RESET
  } else if (line ~ /0\/[0-9]/) {
    status = YELLOW "[NOERROR - NODATA]" RESET
  } else {
    status = ""
  }

  print path " " record_type " " line " " status
  fflush()
}
'
