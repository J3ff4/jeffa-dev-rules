#!/usr/bin/env python3
"""PreToolUse guard: keep secret files out of git and out of the transcript.

Blocks (exit 2, reason on stderr goes back to Claude):
  - git add / git commit naming a secret file
  - bulk staging: git add -A / . / --all / -u, git commit -a / --all
  - reading a secret file (Read/Grep tools, or cat/less/head/tail/grep/... in Bash)
Templates (.env.example, .env.sample, .env.template) are allowed.
"""

from __future__ import annotations

import json
import re
import shlex
import sys

SECRET = re.compile(
    r"(^|/)("
    r"\.env(\.[^/]*)?|\.envrc"
    r"|[^/]*\.(pem|key|p12|pfx|jks|keystore|p8|mobileprovision)"
    r"|id_(rsa|dsa|ecdsa|ed25519)"
    r"|credentials[^/]*\.json|service[-_]account[^/]*\.json"
    r"|\.npmrc|\.pypirc|\.netrc|\.git-credentials"
    r")$"
)
TEMPLATE = re.compile(r"\.(example|sample|template|dist)$")
READERS = {"cat", "less", "more", "head", "tail", "bat", "grep", "rg", "awk", "sed",
           "strings", "xxd", "od", "base64", "source", ".", "cp", "scp", "nl", "tac"}
BULK_ADD = {"-A", "--all", ".", "-u", "--update", ":/", "*"}


def is_secret(path: str) -> bool:
    path = path.strip("'\"")
    return bool(SECRET.search(path)) and not TEMPLATE.search(path)


def block(reason: str) -> None:
    print(f"guard-secrets: {reason}", file=sys.stderr)
    sys.exit(2)


def check_bash(cmd: str) -> None:
    # Split on shell separators; shlex per segment. Unparseable -> fall back to whitespace.
    for seg in re.split(r"&&|\|\||;|\||\n", cmd):
        try:
            words = shlex.split(seg)
        except ValueError:
            words = seg.split()
        if not words:
            continue
        # Skip env assignments / sudo / time prefixes.
        while words and (re.match(r"^\w+=", words[0]) or words[0] in {"sudo", "time", "command"}):
            words = words[1:]
        if not words:
            continue
        prog = words[0].rsplit("/", 1)[-1]
        args = words[1:]
        if prog == "git":
            # Drop global options like -C <dir>, -c k=v.
            while args and args[0].startswith("-"):
                args = args[2:] if args[0] in {"-C", "-c"} else args[1:]
            sub, rest = (args[0], args[1:]) if args else ("", [])
            if sub == "add":
                if any(a in BULK_ADD for a in rest):
                    block("bulk staging is blocked; stage files by name (git add path/a path/b).")
                if any(is_secret(a) for a in rest):
                    block("refusing to stage a secret file; keep it in .gitignore, commit a .env.example instead.")
            elif sub == "commit":
                if any(a in {"-a", "--all"} or re.fullmatch(r"-[a-zA-Z]*a[a-zA-Z]*", a) and not a.startswith("--") for a in rest):
                    block("git commit -a is blocked; stage files by name first.")
                # -n is --no-verify on commit: it would skip the gitleaks pre-commit hook.
                if any(a == "--no-verify" or re.fullmatch(r"-[a-zA-Z]*n[a-zA-Z]*", a) for a in rest):
                    block("--no-verify is blocked; the pre-commit secret scan must run. Ask the owner.")
                if any(is_secret(a) for a in rest):
                    block("refusing to commit a secret file.")
        elif prog in READERS and any(is_secret(a) for a in args):
            block("reading secret files is blocked; ask the owner for the variable NAMES, or read .env.example.")
        # Redirect reads: `< .env`
        if re.search(r"<\s*\S+", seg) and any(is_secret(m) for m in re.findall(r"<\s*(\S+)", seg)):
            block("reading secret files is blocked.")


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return  # not our input shape; never break the harness
    tool = data.get("tool_name", "")
    inp = data.get("tool_input") or {}
    if tool == "Bash":
        check_bash(inp.get("command", ""))
    elif tool == "Read" and is_secret(inp.get("file_path", "")):
        block("reading secret files is blocked; read .env.example or ask the owner.")
    elif tool == "Grep" and (
        is_secret(inp.get("path", "") or "")
        # A glob like ".env*" is a pattern, not a path: any glob that can name a .env.
        or re.search(r"(^|[/{,])\.env", inp.get("glob", "") or "")
    ):
        block("grepping secret files is blocked.")


if __name__ == "__main__":
    main()
