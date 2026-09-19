#!/usr/bin/env bash
# telemetry/watch-conntrack.sh
# Real-time visual terminal gauge for Linux netfilter conntrack table saturation and drop statistics.

set -euo pipefail

# ANSI color codes
RESET="\033[0m"
BOLD="\033[1m"
RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
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

# Verify container is running
if ! docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null | grep -q "true"; then
  echo -e "\n${RED}${BOLD}╔═══════════════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${RED}${BOLD}║  [ERROR] Kind Node Container '${CONTAINER}' is NOT running!        ║${RESET}"
  echo -e "${RED}${BOLD}╚═══════════════════════════════════════════════════════════════════╝${RESET}"
  echo -e "${YELLOW}The Kind cluster must be running before telemetry can be captured.${RESET}\n"
  echo -e "👉 ${BOLD}Run this command first to spin up your cluster:${RESET}"
  echo -e "   ${GREEN}${BOLD}bash setup/start-cluster.sh${RESET}\n"
  exit 1
fi

render_bar() {
  local pct=$1
  local width=30
  local filled=$(( pct * width / 100 ))
  local empty=$(( width - filled ))
  local bar=""
  
  for ((i=0; i<filled; i++)); do bar="${bar}█"; done
  for ((i=0; i<empty; i++)); do bar="${bar}-"; done

  if [ "$pct" -lt 50 ]; then
    echo -e "${GREEN}[${bar}] ${pct}%${RESET}"
  elif [ "$pct" -lt 80 ]; then
    echo -e "${YELLOW}[${bar}] ${pct}%${RESET}"
  else
    echo -e "${RED_BG} [${bar}] ${pct}% SATURATED ${RESET}"
  fi
}

# Hide cursor on exit
trap 'tput cnorm; echo ""; exit 0' SIGINT SIGTERM
tput civis

while true; do
  # Read conntrack metrics from node /proc
  COUNT=$(docker exec "${CONTAINER}" cat /proc/sys/net/netfilter/nf_conntrack_count 2>/dev/null || echo "0")
  MAX=$(docker exec "${CONTAINER}" cat /proc/sys/net/netfilter/nf_conntrack_max 2>/dev/null || echo "1")
  
  if [ -z "$COUNT" ] || [ "$COUNT" = "0" ]; then COUNT=0; fi
  if [ -z "$MAX" ] || [ "$MAX" = "0" ]; then MAX=1; fi

  PCT=$(( COUNT * 100 / MAX ))
  if [ "$PCT" -gt 100 ]; then PCT=100; fi

  # Collect netfilter conntrack statistics (-S)
  STATS=$(docker exec "${CONTAINER}" conntrack -S 2>/dev/null || echo "conntrack_stats_unavailable")
  
  DROPS=$(echo "$STATS" | grep -E "drop=" | head -n 1 || echo "drop=0 early_drop=0")
  INSERT_FAILED=$(echo "$STATS" | grep -o "insert_failed=[0-9]*" || echo "insert_failed=0")

  # Clear and redraw UI
  clear
  echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${CYAN}${BOLD}║  LIVE TELEMETRY: LINUX NETFILTER CONNECTION TRACKING (CONNTRACK) MONITOR         ║${RESET}"
  echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════════════════════════════════════╝${RESET}"
  echo -e " Target Node Container: ${BOLD}${CONTAINER}${RESET}    Time: ${WHITE_BG} $(date +'%T') ${RESET}"
  echo ""
  echo -e " ${BOLD}Table Capacity Status:${RESET}"
  echo -e "   Current Entries:     ${BOLD}${COUNT}${RESET} / ${BOLD}${MAX}${RESET}"
  echo -ne "   Saturation Level:    "
  render_bar "${PCT}"
  echo ""

  if [ "$PCT" -ge 85 ]; then
    echo -e " ${RED}${BOLD}🚨 CRITICAL ALERT: Table saturation exceeds 85%! Kernel dropping new UDP packets!${RESET}"
  elif [ "$PCT" -ge 50 ]; then
    echo -e " ${YELLOW}${BOLD}⚠️  WARNING: Elevated connection churn detected.${RESET}"
  else
    echo -e " ${GREEN}✓  HEALTHY: Table utilization within safe operational margins.${RESET}"
  fi

  echo -e "\n${BOLD}Netfilter Conntrack Counters (conntrack -S):${RESET}"
  echo -e "----------------------------------------------------------------------------------"
  if [ "$STATS" != "conntrack_stats_unavailable" ]; then
    echo "$STATS" | while IFS= read -r line; do
      if echo "$line" | grep -qE "drop=[1-9]|insert_failed=[1-9]"; then
        echo -e "  ${RED}${BOLD}▶ ${line}${RESET}"
      else
        echo -e "    ${line}"
      fi
    done
  else
    echo "  (conntrack utility loading...)"
  fi
  echo -e "----------------------------------------------------------------------------------"
  echo -e "${BLUE}Press [Ctrl+C] to exit telemetry monitor.${RESET}"
  
  sleep 1
done
