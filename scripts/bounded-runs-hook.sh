#!/usr/bin/env bash
# dev-copilot plugin: PreToolUse(Bash) hook -- refuse unbounded heavy test runs.
#
# Two jobs, both cheap:
#   1. Keep a stable path to the bounded runner: ~/.claude/dev-copilot/bin/ka0s-bounded is a symlink
#      to this plugin version's scripts/ka0s-bounded, refreshed whenever it points anywhere else (a
#      plugin update moves the cache directory). Specs and the refusal message name that path. The
#      legacy ~/.claude/wow-addon/bin/ka0s-bounded link (from before wow-addon merged into
#      dev-copilot) is maintained the same way, because addon docs and vendored kits still name it.
#   2. Hand the command to scripts/bounded_runs.py, which denies a heavy run that is not bounded.
#
# Fails open: any error here exits 0 with no output, so a broken hook can never block Bash.

set -u

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)}"

target="$root/scripts/ka0s-bounded"
for link_dir in "$HOME/.claude/dev-copilot/bin" "$HOME/.claude/wow-addon/bin"; do
    if [ -f "$target" ] && [ "$(readlink "$link_dir/ka0s-bounded" 2>/dev/null)" != "$target" ]; then
        mkdir -p "$link_dir" 2>/dev/null && ln -sfn "$target" "$link_dir/ka0s-bounded" 2>/dev/null
    fi
done

input="$(cat 2>/dev/null || true)"

# Fast path: nothing that could be a heavy run.
case "$input" in
    *lua*|*luacheck*|*lizard*|*run-automated-tests*) ;;
    *) exit 0 ;;
esac

printf '%s' "$input" | python3 "$root/scripts/bounded_runs.py" 2>/dev/null || true
exit 0
