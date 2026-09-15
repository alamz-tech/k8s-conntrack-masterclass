#!/usr/bin/env bash
# incidents/drills/01-baseline-traffic.sh
# Establishes normal morning operational baseline:
#   - Deploys mock external systems (Stripe gateway & Aurora Postgres)
#   - Deploys checkout-service at normal baseline (2 replicas)
#   - Observes steady transactions with low conntrack table pressure (<10%)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/../.."

CYAN='\033[0;36m'
GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}=== DRILL 01: ESTABLISHING MORNING OPERATIONAL BASELINE ===${NC}"

# 1. Deploy upstream mock external systems
echo -e "\n${CYAN}[1/3] Deploying mock external systems (Stripe API & Postgres)...${NC}"
kubectl apply -f "${REPO_ROOT}/deploy/mock-external/upstream-services.yaml"
kubectl wait --for=condition=Available deployment/mock-postgres -n external-systems --timeout=45s
kubectl wait --for=condition=Available deployment/mock-stripe -n external-systems --timeout=45s

# 2. Deploy checkout-service with production defaults
echo -e "\n${CYAN}[2/3] Deploying checkout-service (baseline: 2 replicas)...${NC}"
kubectl apply -f "${REPO_ROOT}/deploy/checkout-service.yaml"
kubectl rollout status deployment/checkout-service -n checkout-prod --timeout=60s

# 3. Check baseline status
echo -e "\n${GREEN}${BOLD}[3/3] Baseline Established Successfully!${NC}"
echo -e "Checkout Service Pods:"
kubectl get pods -n checkout-prod -o wide
echo -e "\nCheck telemetry terminal (Pane 1) to verify healthy baseline utilization (< 15%)."
