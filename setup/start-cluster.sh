#!/usr/bin/env bash
# setup/start-cluster.sh
# Provisions the two-node Kind cluster and installs diagnostic tooling on the worker node.

set -euo pipefail

CLUSTER_NAME="conntrack-lab"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/kind-config.yaml"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BLUE}${BOLD}============================================================${NC}"
echo -e "${BLUE}${BOLD}  Live Incident Triage Lab: Provisioning Cluster            ${NC}"
echo -e "${BLUE}${BOLD}============================================================${NC}"

# 1. Prerequisite verification
echo -e "\n${CYAN}[1/5] Verifying prerequisites (docker, kind, kubectl)...${NC}"
for cmd in docker kind kubectl; do
  if ! command -v "${cmd}" &>/dev/null; then
    echo -e "${RED}[ERROR] Required command '${cmd}' is not installed or not in PATH.${NC}" >&2
    exit 1
  fi
  echo -e "  ${GREEN}✓${NC} Found ${cmd}: $(command -v "${cmd}")"
done

# Check Docker daemon connectivity
if ! docker info &>/dev/null; then
  echo -e "${RED}[ERROR] Docker daemon is not running. Please start Docker / Docker Desktop and re-run.${NC}" >&2
  exit 1
fi
echo -e "  ${GREEN}✓${NC} Docker daemon is active."

# 2. Cleanup existing cluster if present
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}\$"; then
  echo -e "\n${YELLOW}[2/5] Cluster '${CLUSTER_NAME}' already exists. Deleting stale cluster...${NC}"
  kind delete cluster --name "${CLUSTER_NAME}"
else
  echo -e "\n${CYAN}[2/5] No existing cluster named '${CLUSTER_NAME}' found.${NC}"
fi

# 3. Create Kind cluster
echo -e "\n${CYAN}[3/5] Creating Kind cluster '${CLUSTER_NAME}' from ${CONFIG_FILE}...${NC}"
kind create cluster --name "${CLUSTER_NAME}" --config "${CONFIG_FILE}"

# 4. Wait for nodes to be Ready
echo -e "\n${CYAN}[4/5] Waiting for cluster nodes to reach Ready state...${NC}"
kubectl cluster-info --context "kind-${CLUSTER_NAME}"
kubectl wait --for=condition=Ready nodes --all --timeout=120s

WORKER_NODE=$(kubectl get nodes -l triage=target -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "${CLUSTER_NAME}-worker")
echo -e "  ${GREEN}✓${NC} Target worker node identified: ${BOLD}${WORKER_NODE}${NC}"

# 5. Pre-install diagnostic utilities into the worker container
echo -e "\n${CYAN}[5/5] Installing low-level diagnostic tools into worker container (${WORKER_NODE})...${NC}"
echo -e "  Installing: ${BOLD}conntrack, tcpdump, procps, iproute2, iptables, dnsutils, curl, dmesg tools${NC}"

docker exec "${WORKER_NODE}" bash -c "
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq && \
  apt-get install -y -qq \
    conntrack \
    tcpdump \
    procps \
    iproute2 \
    iptables \
    dnsutils \
    curl \
    net-tools \
    kmod &>/dev/null
"

echo -e "  ${GREEN}✓${NC} Diagnostic utilities installed inside ${WORKER_NODE}."

echo -e "\n${GREEN}${BOLD}============================================================${NC}"
echo -e "${GREEN}${BOLD}  Cluster Setup Complete!                                   ${NC}"
echo -e "${GREEN}${BOLD}============================================================${NC}"
echo -e "Next steps:"
echo -e "  1. Tune kernel limits:      ${YELLOW}bash setup/set-kernel-limits.sh 2048${NC}"
echo -e "  2. Start telemetry watch:   ${YELLOW}bash telemetry/watch-conntrack.sh${NC}"
echo -e "  3. Deploy mock database:    ${YELLOW}kubectl apply -f manifests/broken/01-mock-upstream.yaml${NC}"
echo -e "  4. Deploy broken client:    ${YELLOW}kubectl apply -f manifests/broken/02-broken-client.yaml${NC}\n"
