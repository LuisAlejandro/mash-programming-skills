#!/usr/bin/env bash
# Execute the complete add-node-version workflow with semi-automated confirmations.
#
# Usage:
#   ./execute-workflow.sh <major-version> [suites...]
#
# Example:
#   ./execute-workflow.sh 26 trixie unstable

set -euo pipefail

MAJOR="${1:?Usage: execute-workflow.sh <major-version> [suites...]}"
shift
SUITES=("${@:-trixie unstable}")

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "${SCRIPT_DIR}")"
WORKSPACE="$(cd "${SKILL_DIR}/../../.." && pwd)"
NODE_PIPELINE="${WORKSPACE}/node-pipeline"
NODE_REPO="${WORKSPACE}/node${MAJOR}"

COLOR_RESET='\033[0m'
COLOR_BOLD='\033[1m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_RED='\033[0;31m'
COLOR_BLUE='\033[0;34m'

log_step() {
    echo -e "${COLOR_BOLD}${COLOR_BLUE}===> $1${COLOR_RESET}"
}

log_success() {
    echo -e "${COLOR_GREEN}✓ $1${COLOR_RESET}"
}

log_warning() {
    echo -e "${COLOR_YELLOW}⚠ $1${COLOR_RESET}"
}

log_error() {
    echo -e "${COLOR_RED}✗ $1${COLOR_RESET}"
}

confirm() {
    local prompt="$1"
    local default="${2:-n}"
    local response
    
    if [ "$default" = "y" ]; then
        read -p "$(echo -e "${COLOR_YELLOW}${prompt} [Y/n]:${COLOR_RESET} ")" -n 1 -r response
    else
        read -p "$(echo -e "${COLOR_YELLOW}${prompt} [y/N]:${COLOR_RESET} ")" -n 1 -r response
    fi
    echo
    
    if [ -z "$response" ]; then
        response="$default"
    fi
    
    [[ "$response" =~ ^[Yy]$ ]]
}

check_prerequisites() {
    log_step "Checking prerequisites"
    
    local errors=0
    
    # Check workspace structure
    if [ ! -d "${NODE_PIPELINE}" ]; then
        log_error "node-pipeline/ not found in workspace"
        ((errors++))
    fi
    
    # Check git config
    if ! git config user.name >/dev/null 2>&1; then
        log_error "git user.name not configured"
        ((errors++))
    fi
    
    if ! git config user.email >/dev/null 2>&1; then
        log_error "git user.email not configured"
        ((errors++))
    fi
    
    # Check for DEBFULLNAME and DEBEMAIL
    if [ -z "${DEBFULLNAME:-}" ] && ! grep -q "^DEBFULLNAME=" "${NODE_PIPELINE}/config.env" 2>/dev/null; then
        log_warning "DEBFULLNAME not set (optional but recommended)"
    fi
    
    if [ -z "${DEBEMAIL:-}" ] && ! grep -q "^DEBEMAIL=" "${NODE_PIPELINE}/config.env" 2>/dev/null; then
        log_warning "DEBEMAIL not set (optional but recommended)"
    fi
    
    # Check upstream branch exists
    log_step "Verifying v${MAJOR}.x branch exists on nodejs/node"
    if ! git ls-remote --heads https://github.com/nodejs/node.git "refs/heads/v${MAJOR}.x" | grep -q "v${MAJOR}.x"; then
        log_error "Branch v${MAJOR}.x does not exist at https://github.com/nodejs/node"
        ((errors++))
    else
        log_success "Branch v${MAJOR}.x exists"
    fi
    
    if [ $errors -gt 0 ]; then
        log_error "Prerequisites check failed with $errors errors"
        return 1
    fi
    
    log_success "Prerequisites check passed"
    return 0
}

seed_repository() {
    log_step "Seeding node${MAJOR} repository"
    
    if [ -e "${NODE_REPO}" ]; then
        log_error "${NODE_REPO} already exists"
        if ! confirm "Remove and recreate?" n; then
            return 1
        fi
        rm -rf "${NODE_REPO}"
    fi
    
    cd "${NODE_PIPELINE}"
    ./scripts/seed-node-repo.sh "${MAJOR}" "${NODE_REPO}"
    
    log_success "Repository seeded at ${NODE_REPO}"
}

register_in_makefile() {
    log_step "Registering node${MAJOR} in NODE_VERSIONS"
    
    local makefile="${NODE_PIPELINE}/Makefile"
    
    # Check if already registered
    if grep -q "NODE_VERSIONS.*\b${MAJOR}\b" "${makefile}"; then
        log_warning "node${MAJOR} already registered in NODE_VERSIONS"
        return 0
    fi
    
    # Show current NODE_VERSIONS
    local current=$(grep "^NODE_VERSIONS :=" "${makefile}" || echo "NODE_VERSIONS := not found")
    echo "Current: ${current}"
    
    if ! confirm "Add ${MAJOR} to NODE_VERSIONS?" y; then
        log_warning "Skipped registration"
        return 1
    fi
    
    # Add to NODE_VERSIONS (assumes format: NODE_VERSIONS := 16 18 20 22 24)
    sed -i.bak "s/^\(NODE_VERSIONS :=.*\)$/\1 ${MAJOR}/" "${makefile}"
    rm -f "${makefile}.bak"
    
    # Show new NODE_VERSIONS
    local updated=$(grep "^NODE_VERSIONS :=" "${makefile}")
    echo "Updated: ${updated}"
    
    log_success "Registered node${MAJOR}"
}

build_for_suite() {
    local suite="$1"
    
    log_step "Building node${MAJOR} for ${suite}"
    
    cd "${NODE_PIPELINE}"
    
    # Materialize
    log_step "  Materializing work tree for ${suite}"
    if ! make materialize NODE="${MAJOR}" DIST="${suite}"; then
        log_error "Materialize failed for ${suite}"
        return 1
    fi
    log_success "Materialized for ${suite}"
    
    # Build
    log_step "  Building binary packages"
    if ! make build NODE="${MAJOR}"; then
        log_error "Build failed"
        return 1
    fi
    log_success "Build completed"
    
    # Check for artifacts
    local deb_count=$(find dist/ -name "*.deb" -type f 2>/dev/null | wc -l)
    if [ "$deb_count" -eq 0 ]; then
        log_error "No .deb files found in dist/"
        return 1
    fi
    log_success "Generated ${deb_count} .deb packages"
    
    # Publish
    if confirm "Publish packages to ${suite} repository?" y; then
        log_step "  Publishing to ${suite}"
        if ! make publish DIST="${suite}"; then
            log_error "Publish failed for ${suite}"
            return 1
        fi
        log_success "Published to ${suite}"
    else
        log_warning "Skipped publish for ${suite}"
    fi
}

commit_and_push() {
    log_step "Committing changes"
    
    # Commit node${MAJOR} repo
    cd "${NODE_REPO}"
    if [ -n "$(git status --porcelain)" ]; then
        log_warning "node${MAJOR} has uncommitted changes"
        git status --short
    fi
    
    if confirm "Push node${MAJOR} to GitHub?" y; then
        log_step "  Pushing node${MAJOR}"
        echo "Enter GitHub remote URL (or press Enter to skip):"
        read -r remote_url
        if [ -n "${remote_url}" ]; then
            git remote add origin "${remote_url}" 2>/dev/null || git remote set-url origin "${remote_url}"
            git push -u origin main
            log_success "Pushed node${MAJOR}"
        else
            log_warning "Skipped push for node${MAJOR}"
        fi
    fi
    
    # Update parent repo
    cd "${WORKSPACE}"
    if confirm "Commit parent repository updates?" y; then
        git add "node${MAJOR}" "node-pipeline/Makefile"
        git commit -m "Add node${MAJOR} packaging repository

- Seed node${MAJOR} from template
- Register node/ submodule pointing to v${MAJOR}.x branch
- Add ${MAJOR} to NODE_VERSIONS in node-pipeline/Makefile"
        log_success "Committed parent repository"
        
        if confirm "Push parent repository?" y; then
            git push origin main
            log_success "Pushed parent repository"
        fi
    fi
}

main() {
    echo -e "${COLOR_BOLD}Dockershelf Node Version Addition Workflow${COLOR_RESET}"
    echo "Version: node${MAJOR}"
    echo "Suites: ${SUITES[*]}"
    echo
    
    if ! check_prerequisites; then
        exit 1
    fi
    
    echo
    if ! confirm "Proceed with workflow?" y; then
        log_warning "Workflow cancelled"
        exit 0
    fi
    
    echo
    if ! seed_repository; then
        exit 1
    fi
    
    echo
    if ! register_in_makefile; then
        exit 1
    fi
    
    for suite in "${SUITES[@]}"; do
        echo
        if ! build_for_suite "${suite}"; then
            log_error "Build failed for ${suite}"
            exit 1
        fi
    done
    
    echo
    commit_and_push
    
    echo
    log_success "Workflow completed successfully!"
    echo
    echo "Next steps:"
    echo "  1. Verify packages: apt-cache policy nodejs-${MAJOR}"
    echo "  2. Test installation: apt install nodejs-${MAJOR}"
    echo "  3. Update downstream dockershelf images"
    echo "  4. Monitor GitHub Actions workflows"
}

main "$@"
