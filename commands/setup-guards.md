---
description: One-time machine setup - install gitleaks and the global git pre-commit secret scan
allowed-tools: Bash, AskUserQuestion
---

Set up the machine-level secret guards for the jeffa-dev-rules plugin.

1. Tell the owner exactly what will change, then ask for approval with AskUserQuestion
   (Proceed / Cancel, plus their own answer):
   - downloads gitleaks from its GitHub release, verifies the sha256, installs it to
     `~/.local/bin/gitleaks` (skipped if gitleaks is already installed);
   - writes `~/.git-hooks/pre-commit`, backing up any different existing file;
   - sets `git config --global core.hooksPath ~/.git-hooks`, unless it is already set
     to something else, in which case nothing is changed and the owner is told.
2. Only after approval, run: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup-guards.sh"`
3. Report the script's output verbatim. Exit code 2 means another global hooksPath
   exists: explain the two options it printed and ask which the owner wants.
4. Check the current repo, if any: `git config --local --get core.hooksPath`. If it
   prints a path (husky, lefthook), tell the owner that repo needs
   `gitleaks git --pre-commit --staged --redact` added to its own pre-commit hook.
