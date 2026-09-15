#!/usr/bin/env bash
# setup/set-kernel-limits.sh
# Sets nf_conntrack_max and UDP timeouts on the worker node to reproduce connection tracking exhaustion.

set -euo pipefail

LIMIT="${1:-2048}"
CONTAINER="${2:-conntrack-lab-worker}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}=== Netfilter Conntrack Kernel Limit Tuning ===${NC}"
echo -e "Target Node Container: ${BOLD}${CONTAINER}${NC}"
echo -e "Target Conntrack Max:  ${BOLD}${LIMIT}${NC}"

# Check if target container exists and is running
if ! docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null | grep -q "true"; then
  echo -e "${RED}[ERROR] Container '${CONTAINER}' is not running.${NC}"
  echo -e "Available kind nodes:"
  docker ps --filter "name=conntrack-lab" --format "table {{.Names}}\t{{.Status}}"
  exit 1
fi

echo -e "\n${YELLOW}[1/4] Flushing existing conntrack table entries...${NC}"
docker exec "${CONTAINER}" conntrack -F 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} Flushed stale netfilter tracking entries."

echo -e "\n${YELLOW}[2/4] Setting sysctl net.netfilter.nf_conntrack_max=${LIMIT}...${NC}"
docker exec "${CONTAINER}" sysctl -w net.netfilter.nf_conntrack_max="${LIMIT}"

echo -e "\n${YELLOW}[3/4] Configuring realistic UDP conntrack timeouts...${NC}"
# In standard Linux, UDP unreplied is 30s, stream is 120-180s. Setting standard retention:
docker exec "${CONTAINER}" sysctl -w net.netfilter.nf_conntrack_udp_timeout=30 2>/dev/null || true
docker exec "${CONTAINER}" sysctl -w net.netfilter.nf_conntrack_udp_timeout_stream=60 2>/dev/null || true

echo -e "\n${YELLOW}[4/4] Verifying netfilter parameters inside ${CONTAINER}...${NC}"
COUNT=$(docker exec "${CONTAINER}" cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo "N/A")
MAX=$(docker exec "${CONTAINER}" cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null || echo "N/A")
UDP_TO=$(docker exec "${CONTAINER}" cat /proc/sys/net/netfilter/nf_conntrack_udp_timeout 2>/dev/null || echo "N/A")

echo -e "------------------------------------------------------------"
echo -e "  Current Conntrack Count:    ${BOLD}${COUNT}${NC}"
echo -e "  Configured Conntrack Max:   ${GREEN}${BOLD}${MAX}${NC}"
echo -e "  UDP Conntrack Timeout:      ${BOLD}${UDP_TO}s${NC}"
echo -e "------------------------------------------------------------"

if [ "${MAX}" = "${LIMIT}" ]; then
  echo -e "${GREEN}${BOLD}SUCCESS: Kernel netfilter limits are primed for triage demonstration.${NC}\n"
else
  echo -e "${RED}[WARNING] Value mismatch! Max is ${MAX}, expected ${LIMIT}.${NC}\n"
fi
