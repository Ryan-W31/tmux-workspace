#!/usr/bin/env bash
set -eu

plugin_dir="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# Respect an explicit setting; otherwise use the plugin's actual install path.
tmux set-option -og @workspace-plugin-dir "$plugin_dir"
tmux set-option -og @workspace-key C-a

tmux set-environment -gF TMUX_WORKSPACE_PLUGIN_DIR "#{@workspace-plugin-dir}"
tmux set-environment -gF TMUX_WORKSPACE_ROOT "#{@workspace-root}"
tmux set-environment -gF TMUX_WORKSPACE_TEMPLATE "#{@workspace-template}"

tmux bind-key -T prefix "#{@workspace-key}" \
	display-popup -E -w 80% -h 60% "#{@workspace-plugin-dir}/bin/tmux-workspace"
