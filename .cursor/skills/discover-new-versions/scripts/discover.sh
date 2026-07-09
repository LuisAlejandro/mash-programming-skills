#!/usr/bin/env bash
# Discover new major/minor versions of Node.js, Python, and Go
# that exist upstream but aren't yet in the Dockershelf pipeline.
#
# Usage:
#   ./discover.sh [node|python|go|all]
#
# Examples:
#   ./discover.sh          # Check all languages
#   ./discover.sh node     # Check only Node.js
#   ./discover.sh all      # Explicit: check all
#
# Note: This script only DISCOVERS new versions. The discover-new-versions
# skill will automatically add new versions and retire the oldest version
# if the total count exceeds 5 for any language.

set -euo pipefail

WORKSPACE="${DOCKERSHELF_WORKSPACE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)}"
cd "$WORKSPACE"

LANG_FILTER="${1:-all}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# GitHub API authentication (optional, increases rate limits)
GITHUB_API_HEADERS=()
if [ -n "${GITHUB_TOKEN:-}" ]; then
  GITHUB_API_HEADERS=("-H" "Authorization: token $GITHUB_TOKEN")
fi

# Utility: Check if jq is available
check_jq() {
  if ! command -v jq >/dev/null 2>&1; then
    echo -e "${RED}Error: jq is required but not installed${NC}" >&2
    echo "Install with: brew install jq (macOS) or apt-get install jq (Debian/Ubuntu)" >&2
    exit 1
  fi
}

# Read current versions from Makefile
read_current_versions() {
  local pipeline="$1"
  local var_name="$2"
  
  if [ ! -f "${pipeline}/Makefile" ]; then
    echo -e "${RED}Error: ${pipeline}/Makefile not found${NC}" >&2
    return 1
  fi
  
  grep "^${var_name} :=" "${pipeline}/Makefile" | sed "s/${var_name} := //"
}

# Query GitHub API with rate limit handling
github_api() {
  local url="$1"
  local response
  local rate_limit
  
  response=$(curl -fsSL "${GITHUB_API_HEADERS[@]}" "$url" 2>&1) || {
    echo -e "${RED}Error: Failed to query GitHub API${NC}" >&2
    echo "URL: $url" >&2
    echo "Response: $response" >&2
    
    # Check if rate limit error
    if echo "$response" | grep -q "rate limit"; then
      echo -e "${YELLOW}Tip: Set GITHUB_TOKEN environment variable to increase rate limits${NC}" >&2
    fi
    return 1
  }
  
  echo "$response"
}

# Discover new Node.js versions
discover_node() {
  echo -e "${BOLD}=== Node.js ===${NC}"
  
  local current
  current=$(read_current_versions "node-pipeline" "NODE_VERSIONS")
  echo -e "Current pipeline: ${GREEN}$current${NC}"
  
  echo "Querying upstream branches..."
  local upstream_raw
  upstream_raw=$(github_api "https://api.github.com/repos/nodejs/node/branches?per_page=100")
  
  local upstream
  upstream=$(echo "$upstream_raw" | jq -r '.[].name' | grep -E '^v[0-9]+\.x$' | sed 's/^v//; s/\.x$//' | sort -n)
  echo -e "Upstream branches: ${BLUE}$(echo $upstream | tr '\n' ' ')${NC}"
  
  local new_versions=()
  for ver in $upstream; do
    if ! echo " $current " | grep -q " $ver "; then
      new_versions+=("$ver")
      echo -e "  ${YELLOW}🆕 NEW: Node.js $ver${NC} (branch v${ver}.x exists)"
      
      # Check for stable releases
      echo "     Checking for stable releases..."
      local tags
      tags=$(git ls-remote https://github.com/nodejs/node.git "refs/tags/v${ver}.*" 2>/dev/null | grep -v 'rc\|beta\|test' | wc -l)
      if [ "$tags" -gt 0 ]; then
        echo -e "     ${GREEN}✓ $tags stable release(s) found${NC}"
      else
        echo -e "     ${YELLOW}⚠ No stable releases yet (may be pre-release)${NC}"
      fi
    fi
  done
  
  if [ ${#new_versions[@]} -eq 0 ]; then
    echo -e "  ${GREEN}✓ Pipeline is up to date${NC}"
  fi
  
  echo ""
  return ${#new_versions[@]}
}

# Discover new Python versions
discover_python() {
  echo -e "${BOLD}=== Python ===${NC}"
  
  local current
  current=$(read_current_versions "python-pipeline" "PY_VERSIONS")
  echo -e "Current pipeline: ${GREEN}$current${NC}"
  
  echo "Querying upstream branches..."
  local upstream_raw
  upstream_raw=$(github_api "https://api.github.com/repos/python/cpython/branches?per_page=100")
  
  local upstream
  upstream=$(echo "$upstream_raw" | jq -r '.[].name' | grep -E '^3\.[0-9]+$' | sort -V)
  echo -e "Upstream branches: ${BLUE}$(echo $upstream | tr '\n' ' ')${NC}"
  
  local new_versions=()
  for ver in $upstream; do
    if ! echo " $current " | grep -q " $ver "; then
      new_versions+=("$ver")
      echo -e "  ${YELLOW}🆕 NEW: Python $ver${NC} (branch $ver exists)"
      
      # Check for stable releases
      echo "     Checking for stable releases..."
      local tags
      tags=$(git ls-remote https://github.com/python/cpython.git "refs/tags/v${ver}.0" 2>/dev/null | grep -v 'a[0-9]\|b[0-9]\|rc[0-9]' | wc -l)
      if [ "$tags" -gt 0 ]; then
        echo -e "     ${GREEN}✓ Stable release v${ver}.0 found${NC}"
      else
        echo -e "     ${YELLOW}⚠ No stable v${ver}.0 yet (may be pre-release)${NC}"
      fi
    fi
  done
  
  if [ ${#new_versions[@]} -eq 0 ]; then
    echo -e "  ${GREEN}✓ Pipeline is up to date${NC}"
  fi
  
  echo ""
  return ${#new_versions[@]}
}

# Discover new Go versions
discover_go() {
  echo -e "${BOLD}=== Go ===${NC}"
  
  local current
  current=$(read_current_versions "go-pipeline" "GO_VERSIONS")
  echo -e "Current pipeline: ${GREEN}$current${NC}"
  
  echo "Querying upstream branches..."
  local upstream_raw
  upstream_raw=$(github_api "https://api.github.com/repos/golang/go/branches?per_page=100")
  
  local upstream
  upstream=$(echo "$upstream_raw" | jq -r '.[].name' | grep -E '^release-branch\.go[0-9]+\.[0-9]+$' | sed 's/^release-branch\.go//' | sort -V)
  echo -e "Upstream branches: ${BLUE}$(echo $upstream | tr '\n' ' ')${NC}"
  
  local new_versions=()
  for ver in $upstream; do
    if ! echo " $current " | grep -q " $ver "; then
      new_versions+=("$ver")
      echo -e "  ${YELLOW}🆕 NEW: Go $ver${NC} (branch release-branch.go$ver exists)"
      
      # Check for stable releases
      echo "     Checking for stable releases..."
      local tags
      tags=$(git ls-remote https://github.com/golang/go.git "refs/tags/go${ver}.0" 2>/dev/null | wc -l)
      if [ "$tags" -gt 0 ]; then
        echo -e "     ${GREEN}✓ Stable release go${ver}.0 found${NC}"
      else
        echo -e "     ${YELLOW}⚠ No stable go${ver}.0 yet (may be pre-release)${NC}"
      fi
    fi
  done
  
  if [ ${#new_versions[@]} -eq 0 ]; then
    echo -e "  ${GREEN}✓ Pipeline is up to date${NC}"
  fi
  
  echo ""
  return ${#new_versions[@]}
}

# Main execution
main() {
  check_jq
  
  echo -e "${BOLD}${BLUE}🔍 Dockershelf Version Discovery${NC}"
  echo ""
  
  local node_count=0
  local python_count=0
  local go_count=0
  
  if [ "$LANG_FILTER" = "all" ] || [ "$LANG_FILTER" = "node" ]; then
    discover_node || node_count=$?
  fi
  
  if [ "$LANG_FILTER" = "all" ] || [ "$LANG_FILTER" = "python" ]; then
    discover_python || python_count=$?
  fi
  
  if [ "$LANG_FILTER" = "all" ] || [ "$LANG_FILTER" = "go" ]; then
    discover_go || go_count=$?
  fi
  
  # Summary
  echo -e "${BOLD}=== Summary ===${NC}"
  local total=$((node_count + python_count + go_count))
  
  if [ $total -eq 0 ]; then
    echo -e "${GREEN}✓ All pipelines are up to date${NC}"
  else
    echo -e "${YELLOW}Found $total new version(s) across all languages${NC}"
    echo ""
    echo -e "${BOLD}Next steps:${NC}"
    
    if [ $node_count -gt 0 ] && [ "$LANG_FILTER" != "python" ] && [ "$LANG_FILTER" != "go" ]; then
      echo "  • Node.js: Create GitHub repos and run /add-node-version for each new version"
    fi
    
    if [ $python_count -gt 0 ] && [ "$LANG_FILTER" != "node" ] && [ "$LANG_FILTER" != "go" ]; then
      echo "  • Python: Create GitHub repos and run /add-python-version for each new version"
    fi
    
    if [ $go_count -gt 0 ] && [ "$LANG_FILTER" != "node" ] && [ "$LANG_FILTER" != "python" ]; then
      echo "  • Go: Create GitHub repos and run /add-go-version for each new version"
    fi
    
    echo ""
    echo -e "${BOLD}⚠️  Version limit enforcement:${NC}"
    echo "  Each language maintains a maximum of 5 active versions."
    echo "  When adding a new version causes the count to exceed 5,"
    echo "  the oldest version will be automatically retired."
  fi
  
  return $total
}

main
