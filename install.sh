#!/usr/bin/env bash
set -e

echo "🌹 Installing Rosey Agentic Environment..."

INSTALL_ROOT="$(pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$SCRIPT_DIR"

echo "-> Installing from $SOURCE_ROOT into $INSTALL_ROOT..."

if [ ! -d "$SOURCE_ROOT/.cursor" ]; then
    echo "❌ Error: Could not find .cursor directory in $SOURCE_ROOT"
    echo "   Run this script from the rosey-agentic-env repository (install.sh must live beside .cursor/)."
    exit 1
fi

echo "-> Scaffolding .cursor folder..."
mkdir -p .cursor

# Copy rules, skills, agents, and mcp.json from this repo
[ -d "$SOURCE_ROOT/.cursor/rules" ] && cp -R "$SOURCE_ROOT/.cursor/rules" .cursor/
[ -d "$SOURCE_ROOT/.cursor/skills" ] && cp -R "$SOURCE_ROOT/.cursor/skills" .cursor/
[ -d "$SOURCE_ROOT/.cursor/agents" ] && cp -R "$SOURCE_ROOT/.cursor/agents" .cursor/
[ -f "$SOURCE_ROOT/.cursor/mcp.json" ] && cp "$SOURCE_ROOT/.cursor/mcp.json" .cursor/

echo "-> Updating .gitignore..."
touch .gitignore
if ! grep -q "docs/plans" .gitignore 2>/dev/null; then
    echo -e "\n# Rosey Agentic Environment" >> .gitignore
    echo "docs/plans/" >> .gitignore
    echo "docs/designs/" >> .gitignore
fi

# --- npm install helpers ---

install_npm_deps() {
    local dir="$1"
    local label="$2"

    if [ ! -f "$dir/package.json" ]; then
        return 0
    fi
    if ! command -v npm >/dev/null 2>&1; then
        echo "   ⚠️  Skipping $label (npm not found on PATH)"
        return 0
    fi

    echo "-> npm install: $label"
    (
        cd "$dir"
        if [ -f pnpm-lock.yaml ] && command -v pnpm >/dev/null 2>&1; then
            pnpm install --frozen-lockfile 2>/dev/null || pnpm install
        elif [ -f yarn.lock ] && command -v yarn >/dev/null 2>&1; then
            yarn install --frozen-lockfile 2>/dev/null || yarn install
        elif [ -f package-lock.json ]; then
            npm ci 2>/dev/null || npm install
        else
            npm install
        fi
    ) || echo "   ⚠️  npm install failed in $label (continuing)"
}

echo "-> Installing skill dependencies (OpenDesign, etc.)..."
if [ -d ".cursor/skills" ]; then
    while IFS= read -r -d '' pkg; do
        skill_dir="$(dirname "$pkg")"
        install_npm_deps "$skill_dir" "skill $(basename "$skill_dir")"
    done < <(find .cursor/skills -name package.json -not -path '*/node_modules/*' -print0 2>/dev/null)
fi

echo "-> Installing app dependencies..."
if [ -f "$INSTALL_ROOT/package.json" ]; then
    install_npm_deps "$INSTALL_ROOT" "workspace root"
fi

# --- Sentrux ---

install_sentrux() {
    if command -v sentrux >/dev/null 2>&1; then
        echo "-> Sentrux already installed ($(sentrux --version 2>/dev/null || echo ok))"
        return 0
    fi

    echo "-> Installing Sentrux CLI (required for rosey-manager / rosey-developer / rosey-qa)..."
    case "$(uname -s)" in
        Darwin)
            if command -v brew >/dev/null 2>&1; then
                brew install sentrux/tap/sentrux || {
                    echo "   ⚠️  brew install sentrux failed. Try: brew install sentrux/tap/sentrux"
                    return 1
                }
            else
                echo "   ⚠️  Homebrew not found. Install Sentrux manually:"
                echo "      brew install sentrux/tap/sentrux"
                return 1
            fi
            ;;
        Linux)
            curl -fsSL https://sentrux.dev/install.sh | sh || {
                echo "   ⚠️  Sentrux install script failed. See https://sentrux.dev/docs/mcp/"
                return 1
            }
            ;;
        *)
            echo "   ⚠️  Automatic Sentrux install not supported on this OS."
            echo "      Install manually: cargo install sentrux  (see rosey-sentrux skill)"
            return 1
            ;;
    esac

    if command -v sentrux >/dev/null 2>&1; then
        echo "   Sentrux installed: $(sentrux --version 2>/dev/null || true)"
    fi
}

install_sentrux || true

# --- Hindsight embed ---

check_hindsight_embed() {
    echo "-> Checking optional Hindsight embed CLI..."

    if ! command -v uvx >/dev/null 2>&1; then
        echo "   ⚠️  Hindsight embed requires uv/uvx for local memory."
        echo "      Install uv: https://docs.astral.sh/uv/"
        echo "      Then run: uvx hindsight-embed configure"
        return 0
    fi

    if uvx hindsight-embed daemon status >/dev/null 2>&1; then
        echo "   Hindsight embed is configured."
    else
        echo "   ⚠️  Hindsight embed is optional and not configured yet."
        echo "      Run once when you want local memory: uvx hindsight-embed configure"
    fi
}

check_hindsight_embed || true

echo ""
echo "✅ Rosey Environment installed successfully!"
echo "   .cursor/rules, .cursor/skills, .cursor/agents, and mcp.json are in place."
echo "   Next: configure MCP secrets in .cursor/mcp.json."
echo "   Optional local memory: configure Hindsight with 'uvx hindsight-embed configure'."
