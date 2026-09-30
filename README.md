# tmux-workspace

A small tmux plugin for creating a fresh directory, applying a shell based
template, then opening a tmux session in that directory. Templates can create
folders and files, write file contents, clone repositories, make symlinks, etc.

## Install with TPM

Add this to `~/.tmux.conf`:

```tmux
set -g @plugin 'Ryan-W31/tmux-workspace'
set -g @workspace-root '~/Projects'
set -g @workspace-template '~/.config/tmux/workspace-template.sh'
set -g @workspace-key 'C-a'
```

Then press `prefix` + `C-a` and enter a session name and directory. The
directory defaults to `<workspace-root>/<session-name>`. `@workspace-template`
is optional; by default the plugin uses `templates/default.sh`.

## Recommended companion: tmux-picker

[`tmux-picker`](https://github.com/Prometheus1400/tmux-picker) is recommended
alongside `tmux-workspace`, but it is optional.
This plugin creates workspaces as ordinary tmux sessions; tmux-picker makes it
easy to find and switch between those sessions, windows, and panes. Create a
workspace with `prefix` + `C-a`, then open tmux-picker with its default
`prefix` + `o` binding.

Install both plugins with TPM:

```tmux
set -g @plugin 'Ryan-W31/tmux-workspace'
set -g @plugin 'Prometheus1400/tmux-picker'
```

They work independently, and their default key bindings do not conflict. See
the tmux-picker README for its requirements and configuration.

## Template format

A template is a Bash script run with `SESSION_NAME` and `WORKSPACE_DIR` set.
It can use these helpers:

```bash
dir src/components
file TODO.md
write src/README.md <<'EOF'
Project notes go here.
EOF
clone https://github.com/example/project.git vendor/project
symlink ~/.config/nvim nvim-config
```

`dir`, `file`, `write`, and the destination passed to `clone` or `symlink` are
workspace-relative. These helpers reject absolute paths and `..` traversal.
The symlink source is passed through to `ln -s`, so it may be an absolute path.
Template files are shell scripts and can run ordinary shell commands; only use
templates you trust.

The command can also be run directly from a shell:

```sh
tmux-workspace my-app ~/Projects/my-app ~/.config/tmux/web-template.sh
```

When invoked from inside tmux, it creates and switches to a detached session.
Outside tmux, it creates and attaches to the new session.
