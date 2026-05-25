# Rosey Agentic Environment

This is a standalone, portable Agentic Environment for Cursor, containing rules, skills, and MCP configurations.

It's designed to be injected into target "unirepos" so they gain the intelligence of the Rosey agents without needing to clone a massive meta-repository.

## Installation into a target repository

To scaffold this environment into any project, simply run the installation script in the root directory of your target repository:

```bash
curl -sSL https://raw.githubusercontent.com/LuisAlejandro/rosey-agentic-env/main/install.sh | bash
```

*Note: Update the URL above to point to the raw location of the `install.sh` file in your actual remote repository.*

### What the installer does:
1. Downloads the latest rules and skills from this repository.
2. Creates and populates the `.cursor/rules` and `.cursor/skills` folders in your target repository.
3. Automatically updates your `.gitignore` to keep AI plan and design artifacts (`docs/plans/` and `docs/designs/`) out of version control.

## Updating the environment
To update the rules and skills in a target repository, simply run the install command again. It will overwrite the `.cursor` files with the latest versions from the remote repository.