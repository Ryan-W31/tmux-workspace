# This default matches TPM's standard plugin install directory. Override it if
# the plugin is installed elsewhere.
set-option -og @workspace-plugin-dir "#{HOME}/.tmux/plugins/tmux-workspace"
set-option -og @workspace-key C-a

set-environment -gF TMUX_WORKSPACE_PLUGIN_DIR "#{@workspace-plugin-dir}"
set-environment -gF TMUX_WORKSPACE_ROOT "#{@workspace-root}"
set-environment -gF TMUX_WORKSPACE_TEMPLATE "#{@workspace-template}"

bind-key -T prefix "#{@workspace-key}" \
  display-popup -E -w 80% -h 60% "#{@workspace-plugin-dir}/bin/tmux-workspace"
