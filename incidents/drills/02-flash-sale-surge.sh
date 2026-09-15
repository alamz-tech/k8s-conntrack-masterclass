#!/usr/bin/env bash
# incidents/drills/02-flash-sale-surge.sh
# Simulates Cyber Monday flash-sale traffic surge:
#   - HPA or manual scaling increases checkout-service replicas from 2 to 6
#   - Pods generate high-throughput payment & DB checkout calls
#   - Unqualified hostnames (api.stripe.com, postgres.internal) trigger 10x DNS amplification
#   - Netfilter conntrack table hits 100% capacity in seconds, triggering silent UDP drops

set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${RED}${BOLD}============================================================${NC}"
echo -e "${RED}${BOLD}  DRILL 02: SIMULATING FLASH-SALE SCALE SURGE (BLACK FRIDAY) ${NC}"
echo -e "${RED}${BOLD}============================================================${NC}"

echo -e "\n${YELLOW}[1/2] Simulating HPA traffic spike: Scaling checkout-service to 6 replicas...${NC}"
kubectl scale deployment/checkout-service -n checkout-prod --replicas=6
kubectl rollout status deployment/checkout-service -n checkout-prod --timeout=45s

echo -e "\n${RED}${BOLD}[2/2] Traffic Surge Active!${NC}"
echo -e "Each pod is executing 20 concurrent checkout loops."
echo -e "Because 'api.stripe.com' and 'postgres.internal' have < 5 dots, each checkout attempt generates 20 UDP queries across search domains."
echo -e "Watch:"
echo -e "  Pane 1: ${YELLOW}Conntrack table gauge will climb to 100% and show drops.${NC}"
echo -e "  Pane 2: ${YELLOW}tcpdump will stream parallel A/AAAA lookups across 4 search paths.${NC}"
echo -e "  Pane 3: ${YELLOW}Follow pod logs: kubectl logs -n checkout-prod -l app=checkout-service -f --tail=30${NC}"
