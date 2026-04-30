#!/usr/bin/env bash
# One-time setup: clone VPS wiki bare repo into Obsidian vault
#
# Usage:
#   VPS_USER=ubuntu VPS_IP=1.2.3.4 VAULT_PATH=~/Documents/Obsidian/MyVault \
#     bash scripts/setup-obsidian-sync.sh
#
# After running, configure Obsidian Git plugin:
#   - Custom base path: Web3/Project_Tracking
#   - Auto pull interval: 30 minutes
#   - Pull on startup: enabled

set -euo pipefail

: "${VPS_USER:?Set VPS_USER (e.g. ubuntu)}"
: "${VPS_IP:?Set VPS_IP (e.g. 1.2.3.4)}"
: "${VAULT_PATH:?Set VAULT_PATH (e.g. ~/Documents/Obsidian/MyVault)}"

VAULT_PATH="${VAULT_PATH/#\~/$HOME}"
TARGET_DIR="$VAULT_PATH/Web3/Project_Tracking"
BARE_REPO="${VPS_USER}@${VPS_IP}:/opt/crypto-wiki-private.git"

echo "→ Target: $TARGET_DIR"
echo "→ Remote: $BARE_REPO"

if [ -d "$TARGET_DIR/.git" ]; then
  echo "Already cloned — running git pull instead"
  git -C "$TARGET_DIR" pull origin main
else
  mkdir -p "$TARGET_DIR"
  git clone "$BARE_REPO" "$TARGET_DIR"
  echo "✅ Clone complete"
fi

echo ""
echo "Next steps:"
echo "  1. Install 'Obsidian Git' community plugin in Obsidian"
echo "  2. Settings → Obsidian Git → Custom base path: Web3/Project_Tracking"
echo "  3. Auto pull interval: 30 minutes | Pull on startup: enabled"
echo "  4. Command Palette → 'Obsidian Git: Pull' to verify"
