#!/usr/bin/env bash
# setup/set-kernel-limits.sh
# Sets nf_conntrack_max and UDP timeouts on the worker node to reproduce connection tracking exhaustion.

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

LIMIT="${1:-2048}"
CONTAINER="${2:-}"
if [ -z "$CONTAINER" ]; then
  CONTAINER=$(docker ps --filter "name=conntrack-lab-worker" --format "{{.Names}}" 2>/dev/null | head -n 1 || true)
  if [ -z "$CONTAINER" ]; then
    CONTAINER=$(docker ps --filter "name=conntrack-lab" --format "{{.Names}}" 2>/dev/null | head -n 1 || true)
  fi
  if [ -z "$CONTAINER" ]; then
    CONTAINER="conntrack-lab-worker"
  fi
fi

# Check if target container exists and is running
if ! docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null | grep -q "true"; then
  echo -e "\n${RED}${BOLD}╔═══════════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${RED}${BOLD}║  [ERROR] Kind Node Container '${CONTAINER}' is NOT running!        ║${NC}"
  echo -e "${RED}${BOLD}╚═══════════════════════════════════════════════════════════════════╝${NC}"
  echo -e "${YELLOW}The Kind cluster must be running before kernel limits can be tuned.${NC}\n"
  echo -e "👉 ${BOLD}Run this command first to spin up your cluster:${NC}"
  echo -e "   ${GREEN}${BOLD}bash setup/start-cluster.sh${NC}\n"
  exit 1
fi

echo -e "\n${YELLOW}[1/4] Flushing existing conntrack table entries...${NC}"
docker exec "${CONTAINER}" conntrack -F 2>/dev/null || true
echo -e "  ${GREEN}✓${NC} Flushed stale netfilter tracking entries."

echo -e "\n${YELLOW}[2/4] Setting sysctl net.netfilter.nf_conntrack_max=${LIMIT}...${NC}"
if ! docker exec "${CONTAINER}" sysctl -w net.netfilter.nf_conntrack_max="${LIMIT}" 2>/dev/null; then
  # Modern Linux kernels restrict nf_conntrack_max to init_net (host network namespace)
  docker run --rm --privileged --net=host kindest/node:v1.30.0 sysctl -w net.netfilter.nf_conntrack_max="${LIMIT}" &>/dev/null || \
  docker run --rm --privileged --net=host alpine sysctl -w net.netfilter.nf_conntrack_max="${LIMIT}" &>/dev/null || true
fi

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
