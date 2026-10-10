#!/usr/bin/env bash
# One-time machine setup: gitleaks + a global git pre-commit hook that runs it.
# Idempotent. Touches only ~/.local/bin/gitleaks, ~/.git-hooks/pre-commit and
# the global git config key core.hooksPath.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$HOME/.local/bin"
HOOKS="$HOME/.git-hooks"

case "$(uname -s)" in
  Linux) os=linux ;;
  Darwin) os=darwin ;;
  *) echo "unsupported OS $(uname -s); install gitleaks by hand" >&2; exit 1 ;;
esac
case "$(uname -m)" in
  x86_64 | amd64) arch=x64 ;;
  arm64 | aarch64) arch=arm64 ;;
  *) echo "unsupported arch $(uname -m)" >&2; exit 1 ;;
esac

# 1. gitleaks, checksum-verified against the release's own checksums file.
if command -v gitleaks >/dev/null || [ -x "$BIN/gitleaks" ]; then
  echo "gitleaks already installed: $( (command -v gitleaks || echo "$BIN/gitleaks") )"
else
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  v="$(curl -fsSL https://api.github.com/repos/gitleaks/gitleaks/releases/latest \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['tag_name'].lstrip('v'))")"
  asset="gitleaks_${v}_${os}_${arch}.tar.gz"
  base="https://github.com/gitleaks/gitleaks/releases/download/v$v"
  (cd "$tmp" && curl -fsSLO "$base/$asset" && curl -fsSLO "$base/gitleaks_${v}_checksums.txt")
  expected="$(grep " $asset\$" "$tmp/gitleaks_${v}_checksums.txt" | cut -d' ' -f1)"
  actual="$( (sha256sum "$tmp/$asset" 2>/dev/null || shasum -a 256 "$tmp/$asset") | cut -d' ' -f1)"
  if [ -z "$expected" ] || [ "$expected" != "$actual" ]; then
    echo "gitleaks checksum mismatch; aborting" >&2
    exit 1
  fi
  tar xzf "$tmp/$asset" -C "$tmp" gitleaks
  mkdir -p "$BIN"
  install -m 755 "$tmp/gitleaks" "$BIN/gitleaks"
  echo "installed gitleaks $v to $BIN"
fi
case ":$PATH:" in *":$BIN:"*) ;; *) echo "note: $BIN is not on PATH (the hook finds it anyway)" ;; esac

# 2. Global pre-commit hook.
mkdir -p "$HOOKS"
if [ -e "$HOOKS/pre-commit" ] && ! cmp -s "$ROOT/git-hooks/pre-commit" "$HOOKS/pre-commit"; then
  cp "$HOOKS/pre-commit" "$HOOKS/pre-commit.bak.$(date +%Y%m%d%H%M%S)"
  echo "backed up existing $HOOKS/pre-commit"
fi
install -m 755 "$ROOT/git-hooks/pre-commit" "$HOOKS/pre-commit"

# 3. Point git at it, unless something else already owns the global hooksPath.
current="$(git config --global --get core.hooksPath || true)"
if [ -n "$current" ] && [ "$current" != "$HOOKS" ] && [ "$current" != "~/.git-hooks" ]; then
  echo "core.hooksPath is already set globally to '$current'; NOT changed." >&2
  echo "Add gitleaks to that hook, or set it to $HOOKS yourself." >&2
  exit 2
fi
git config --global core.hooksPath "$HOOKS"
echo "core.hooksPath -> $HOOKS"
echo "done. Repos with a LOCAL core.hooksPath (husky, lefthook) override this; check with:"
echo "  git config --local --get core.hooksPath"
