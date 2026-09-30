#!/usr/bin/env bash

# Available helpers: dir, file, write, clone, symlink.
# Paths passed to dir/file/write/clone and the symlink destination are relative
# to WORKSPACE_DIR. `write` reads the file contents from standard input.

dir notes
write README.md <<EOF
# $SESSION_NAME

Workspace created at $WORKSPACE_DIR.
Edit this template to make it your own.
EOF

write .gitignore <<'EOF'
.DS_Store
.env
EOF
