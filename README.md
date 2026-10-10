# jeffa-dev-rules

A Claude Code plugin that brings one set of engineering rules into every session, on
every machine, and stops secrets from reaching git or the chat transcript.

## What it does

| Part | How |
|---|---|
| **Rules** ([`rules/CLAUDE.md`](rules/CLAUDE.md)) | Loaded into every session by a `SessionStart` hook, including after `/clear` and compaction. Covers: the owner decides and Claude asks; the Karpathy guidelines; an implement → review → test → mutation-check loop; DRY/SOLID; OWASP Top 10 security; error handling; destructive-op safety; git etiquette; honest reporting. |
| **Secret guard** ([`hooks/guard-secrets.py`](hooks/guard-secrets.py)) | Runs before every Bash, Read and Grep call Claude makes. Blocks `git add`/`commit` of `.env*`, keys and credentials; bulk staging (`git add -A`, `git add .`, `commit -a`); `--no-verify`; and reading secret files into the transcript. `.env.example` is allowed. |
| **Commit scan** ([`git-hooks/pre-commit`](git-hooks/pre-commit)) | A global git pre-commit hook that runs [gitleaks](https://github.com/gitleaks/gitleaks) on staged changes, for every commit by anyone. It still runs the repo's own pre-commit hook afterwards. Installed by `/jeffa-dev-rules:setup-guards`. |

## Install

In Claude Code:

```
/plugin marketplace add J3ff4/jeffa-dev-rules
/plugin install jeffa-dev-rules@jeffa-dev-rules
```

Restart Claude Code, then run the one-time machine setup:

```
/jeffa-dev-rules:setup-guards
```

Requirements: `python3`, `git`, `curl`, `tar`. Supported on Linux and macOS (x64/arm64).

## Update

```
/plugin marketplace update jeffa-dev-rules
```

Rule changes reach every machine on the next session.

## Notes

- **Project rules layer on top.** A repo's own `CLAUDE.md` adds project specifics.
- **husky and lefthook override the global hook.** A repo that sets a local
  `core.hooksPath` turns the gitleaks hook off for that repo. Check with
  `git config --local --get core.hooksPath`, and add
  `gitleaks git --pre-commit --staged --redact` to that repo's own hook.
- **The guard is a safety net, not a sandbox.** It catches the common paths: named
  files, bulk staging, readers like `cat`/`grep`/`source`. The rules cover the rest.
- **Turn the commit scan off:** `git config --global --unset core.hooksPath`.
