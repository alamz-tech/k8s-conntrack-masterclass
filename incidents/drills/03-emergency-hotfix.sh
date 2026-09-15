#!/usr/bin/env bash
# incidents/drills/03-emergency-hotfix.sh
# Simulates the 02:30 AM On-Call SRE Emergency Mitigation:
#   - You don't have time to write code, open a PR, run CI/CD, and deploy at 2 AM.
#   - SRE accesses the degraded worker node via emergency privileged session.
#   - Dynamically expands net.netfilter.nf_conntrack_max to 65536 and flushes dead UDP tuples.
#   - Bleeding stops instantly; customer transactions recover while permanent PR is drafted.

set -euo pipefail

CONTAINER="${1:-conntrack-lab-worker}"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}============================================================${NC}"
echo -e "${CYAN}${BOLD}  DRILL 03: 02:30 AM ON-CALL EMERGENCY BANDAGE (HOTFIX)     ${NC}"
echo -e "${CYAN}${BOLD}============================================================${NC}"

echo -e "\n${YELLOW}[1/3] Dynamically expanding node conntrack table to 65536 entries...${NC}"
docker exec "${CONTAINER}" sysctl -w net.netfilter.nf_conntrack_max=65536

echo -e "\n${YELLOW}[2/3] Flushing stale unreplied UDP tracking tuples...${NC}"
docker exec "${CONTAINER}" conntrack -F 2>/dev/null || true

echo -e "\n${GREEN}${BOLD}[3/3] Hotfix Applied!${NC}"
COUNT=$(docker exec "${CONTAINER}" cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo "0")
MAX=$(docker exec "${CONTAINER}" cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null || echo "0")
echo -e "  Current Conntrack Utilization: ${BOLD}${COUNT} / ${MAX}${NC}"
echo -e "  Notice in Pane 1: Table saturation immediately drops to < 5%."
echo -e "  Notice in Checkout Logs: DNS resolution errors cease immediately."
echo -e "\n${YELLOW}NOTE: This bought us time. Now we open the GitOps PR for the permanent fix.${NC}"
