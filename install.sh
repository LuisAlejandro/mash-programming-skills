#!/usr/bin/env bash
set -e

echo "🌹 Installing Rosey Agentic Environment..."

# Update this URL to point to the actual GitHub repository where this environment is hosted
REPO_URL="https://github.com/LuisAlejandro/rosey-agentic-env"
TAR_URL="${REPO_URL}/archive/main.tar.gz"

TEMP_DIR=$(mktemp -d)

echo "-> Downloading latest rules and skills from $REPO_URL..."
if ! curl -sSL "$TAR_URL" | tar -xz -C "$TEMP_DIR" --strip-components=1; then
    echo "❌ Error: Failed to download or extract the repository."
    echo "   Ensure the repository is public or you have the correct access rights."
    rm -rf "$TEMP_DIR"
    exit 1
fi

if [ ! -d "$TEMP_DIR/.cursor" ]; then
    echo "❌ Error: Could not find .cursor directory in the downloaded archive."
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "-> Scaffolding .cursor folder..."
mkdir -p .cursor

# Safely copy rules, skills, scripts, and mcp.json
[ -d "$TEMP_DIR/.cursor/rules" ] && cp -R "$TEMP_DIR/.cursor/rules" .cursor/
[ -d "$TEMP_DIR/.cursor/skills" ] && cp -R "$TEMP_DIR/.cursor/skills" .cursor/
[ -d "$TEMP_DIR/.cursor/scripts" ] && cp -R "$TEMP_DIR/.cursor/scripts" .cursor/
[ -f "$TEMP_DIR/.cursor/mcp.json" ] && cp "$TEMP_DIR/.cursor/mcp.json" .cursor/

echo "-> Updating .gitignore..."
touch .gitignore
if ! grep -q "docs/plans" .gitignore 2>/dev/null; then
    echo -e "\n# Rosey Agentic Environment" >> .gitignore
    echo "docs/plans/" >> .gitignore
    echo "docs/designs/" >> .gitignore
    echo "docs/memory-bank/" >> .gitignore
fi

rm -rf "$TEMP_DIR"

echo "✅ Rosey Environment installed successfully!"
echo "   Rules and Skills are now inside your local .cursor directory."
