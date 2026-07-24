#!/usr/bin/env bash
# =============================================================================
# install_workflows.sh — Paramount CRM
#
# WHY THIS EXISTS
#   The automation agent's GitHub App token does not have the `workflows`
#   permission, so it cannot push files into .github/workflows/ directly.
#   The three workflow YAMLs are therefore staged in github_workflows/.
#
# WHAT TO DO (takes ~30 seconds)
#   Option A — run this script locally with your own credentials:
#       git clone https://github.com/maithilrahuljha/Paramount-crm-system.git
#       cd Paramount-crm-system
#       git checkout arena/019f9176-paramount-crm-system
#       bash install_workflows.sh
#
#   Option B — in the GitHub web UI:
#       For each file in github_workflows/, click "Add file → Create new file",
#       name it .github/workflows/<same filename>, paste the contents, commit.
# =============================================================================
set -euo pipefail

mkdir -p .github/workflows
cp github_workflows/*.yml .github/workflows/

git add .github/workflows
git commit -m "ci: install Paramount CRM automation workflows"
git push

echo "✅ Workflows installed. Check the Actions tab on GitHub."
