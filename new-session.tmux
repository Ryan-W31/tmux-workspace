#!/usr/bin/env bash
set -eu

plugin_dir="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# Respect an explicit setting; otherwise use the plugin's actual install path.
if ! tmux show-option -gq @workspace-plugin-dir >/dev/null 2>&1; then
	tmux set-option -gq @workspace-plugin-dir "$plugin_dir"
fi
if ! tmux show-option -gq @workspace-key >/dev/null 2>&1; then
	tmux set-option -gq @workspace-key C-a
fi
workspace_key="$(tmux show-option -gqv @workspace-key)"

shell_quote() {
	printf "'%s'" "${1//\'/\'\\\'\'}"
}

tmux set-environment -gF TMUX_WORKSPACE_PLUGIN_DIR "#{@workspace-plugin-dir}"
tmux set-environment -gF TMUX_WORKSPACE_ROOT "#{@workspace-root}"
tmux set-environment -gF TMUX_WORKSPACE_TEMPLATE "#{@workspace-template}"

tmux bind-key -T prefix "$workspace_key" \
	display-popup -E -w 80% -h 60% "$(shell_quote "$plugin_dir/bin/tmux-workspace")"
