#!/usr/bin/env python3
"""Run with python3 tests/run.py; tmux checks use a private temporary server."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
TMUX = shutil.which("tmux")


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tmux-workspace 'test ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.commands = self.root / "commands.jsonl"
        self.template = self.root / "template.sh"
        self.template.write_text("write marker <<<'created'\n")
        mock_bin = self.root / "bin"
        mock_bin.mkdir()
        mock = mock_bin / "tmux"
        mock.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "args = sys.argv[1:]\n"
            "with open(os.environ['TEST_TMUX_LOG'], 'a') as log:\n"
            "    log.write(json.dumps(args) + '\\n')\n"
            "if os.environ.get('TEST_REAL_TMUX'):\n"
            "    os.execv(os.environ['TEST_REAL_TMUX'], "
            "[os.environ['TEST_REAL_TMUX'], '-S', os.environ['TEST_TMUX_SOCKET'], *args])\n"
            "if args[0] == 'has-session':\n"
            "    sys.exit(0 if os.environ.get('TEST_EXISTING_SESSION') else 1)\n"
            "sys.exit(0)\n"
        )
        mock.chmod(0o755)
        self.env = dict(os.environ)
        for key in list(self.env):
            if key.startswith("TMUX_WORKSPACE_") or key == "TMUX":
                del self.env[key]
        self.env.update(
            PATH=str(mock_bin) + os.pathsep + os.environ["PATH"],
            TEST_TMUX_LOG=str(self.commands),
            TMUX_WORKSPACE_ROOT=str(self.root / "workspaces"),
            TMUX_WORKSPACE_TEMPLATE=str(self.template),
        )

    def run_workspace(self, *args, input=None):
        return subprocess.run(
            ["/bin/bash", str(ROOT / "bin/tmux-workspace"), *args],
            cwd=self.root, env=self.env, input=input, text=True,
            capture_output=True, timeout=10,
        )

    def logged_commands(self):
        if not self.commands.exists():
            return []
        return [json.loads(line) for line in self.commands.read_text().splitlines()]

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)


class WorkspaceTests(Fixture):
    def test_tilde_root_and_template(self):
        def tilde(path):
            return "~/" + os.path.relpath(path, Path.home())

        self.env["TMUX_WORKSPACE_ROOT"] = tilde(self.root / "workspaces")
        self.env["TMUX_WORKSPACE_TEMPLATE"] = tilde(self.template)
        self.assert_success(self.run_workspace("app"))
        self.assertEqual((self.root / "workspaces/app/marker").read_text(), "created\n")
        self.assertEqual(self.logged_commands()[-1], ["attach-session", "-t", "=app"])

    def test_relative_paths_and_template_subshell(self):
        self.template.write_text(
            "printf '%s' \"$PWD\" > cwd\n"
            "printf '%s' \"$SESSION_NAME\" > name\n"
            "dir src\nfile src/empty\nwrite src/readme <<<'hello'\n"
            "directory=/incorrect\nsession_name=incorrect\ncd /\nexit 0\n"
        )
        self.env["TMUX"] = "test"
        # A relative directory must resolve from the caller, even with CDPATH set.
        alternative = self.root / "alternative"
        (alternative / "workspace").mkdir(parents=True)
        self.env["CDPATH"] = str(alternative)
        result = self.run_workspace("app", "workspace", "template.sh")
        self.assert_success(result)
        workspace = self.root / "workspace"
        self.assertEqual((workspace / "cwd").read_text(), str(workspace))
        self.assertEqual((workspace / "name").read_text(), "app")
        self.assertTrue((workspace / "src/empty").exists())
        self.assertEqual((workspace / "src/readme").read_text(), "hello\n")
        self.assertEqual(self.logged_commands()[-2],
                         ["new-session", "-d", "-s", "app", "-c", str(workspace)])
        self.assertEqual(self.logged_commands()[-1], ["switch-client", "-t", "=app"])

    def test_invalid_names_leave_no_directory(self):
        for name in ("my.app", ".", "..", "bad:name", "two words"):
            with self.subTest(name=name):
                result = self.run_workspace(name)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("session name", result.stderr)
        self.assertFalse((self.root / "workspaces").exists())
        self.assertEqual(self.logged_commands(), [])

    def test_existing_session_leaves_no_directory(self):
        self.env["TEST_EXISTING_SESSION"] = "1"
        result = self.run_workspace("app")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)
        self.assertFalse((self.root / "workspaces").exists())

    def test_nonempty_directory_is_untouched(self):
        workspace = self.root / "existing"
        workspace.mkdir()
        marker = workspace / ".hidden"
        marker.write_text("keep")
        result = self.run_workspace("app", str(workspace))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not empty", result.stderr)
        self.assertEqual(marker.read_text(), "keep")
        self.assertEqual(list(workspace.iterdir()), [marker])

    def test_helper_path_rejection(self):
        for index, path in enumerate(("../outside", "nested/../../outside", str(self.root / "outside"))):
            with self.subTest(path=path):
                self.template.write_text("write '" + path.replace("'", "'\\''") + "' <<<'bad'\n")
                result = self.run_workspace("app", str(self.root / f"workspace-{index}"))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("workspace path", result.stderr)
        self.assertFalse((self.root / "outside").exists())

    def test_helpers_reject_symlink_parents_and_targets(self):
        outside = self.root / "outside"
        outside.mkdir()
        target = outside / "target"
        target.write_text("keep")
        for index, helper in enumerate(("dir link/sub", "file link/target", "write link/target <<<'bad'",
                                        "symlink /tmp link/new", "clone ignored link/repo",
                                        "write direct <<<'bad'", "file direct", "write link/ <<<'bad'")):
            with self.subTest(helper=helper):
                self.template.write_text(
                    'symlink "$TEST_OUTSIDE" link\n'
                    'symlink "$TEST_OUTSIDE/target" direct\n' + helper + "\n"
                )
                self.env["TEST_OUTSIDE"] = str(outside)
                result = self.run_workspace("app", str(self.root / f"links-{index}"))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("cannot follow a symlink", result.stderr)
                self.assertEqual(target.read_text(), "keep")
                self.assertEqual(list(outside.iterdir()), [target])

    def test_template_failure_prevents_session_creation(self):
        self.template.write_text("false\nwrite unreachable <<<'bad'\n")
        result = self.run_workspace("app")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "workspaces/app/unreachable").exists())
        self.assertFalse(any(command[0] == "new-session" for command in self.logged_commands()))

    def test_prompt_and_default_template(self):
        del self.env["TMUX_WORKSPACE_TEMPLATE"]
        self.assert_success(self.run_workspace(input="app\n\n"))
        workspace = self.root / "workspaces/app"
        self.assertIn("# app", (workspace / "README.md").read_text())
        self.assertTrue((workspace / "notes").is_dir())


@unittest.skipUnless(TMUX, "tmux is required for loader integration checks")
class LoaderTests(Fixture):
    def setUp(self):
        super().setUp()
        self.env.update(TEST_REAL_TMUX=TMUX, TEST_TMUX_SOCKET=str(self.root / "tmux.sock"))
        self.addCleanup(self.tmux, "kill-server", check=False)
        self.tmux("-f", "/dev/null", "new-session", "-d", "-s", "review", "sleep 60")
        self.assertEqual(self.tmux("list-sessions", "-F", "#{session_name}").stdout.strip(), "review")

    def tmux(self, *args, check=True):
        return subprocess.run(
            [TMUX, "-S", self.env["TEST_TMUX_SOCKET"], *args], env=self.env,
            capture_output=True, text=True, timeout=10, check=check,
        )

    def load(self):
        result = subprocess.run(
            ["/bin/bash", str(ROOT / "new-session.tmux")], env=self.env,
            capture_output=True, text=True, timeout=10,
        )
        self.assert_success(result)

    def test_defaults_and_reload(self):
        self.load()
        self.load()
        self.assertEqual(self.tmux("show-option", "-gv", "@workspace-key").stdout.strip(), "C-a")
        self.assertEqual(self.tmux("show-option", "-gv", "@workspace-plugin-dir").stdout.strip(), str(ROOT))
        binding = self.tmux("list-keys", "-T", "prefix", "C-a").stdout
        self.assertIn("display-popup", binding)
        self.assertIn(str(ROOT / "bin/tmux-workspace"), binding)

    def test_custom_options_survive_reload(self):
        self.tmux("set-option", "-g", "@workspace-key", "C-w")
        self.tmux("set-option", "-g", "@workspace-plugin-dir", str(ROOT))
        self.tmux("set-option", "-g", "@workspace-root", "~/Custom Projects")
        self.load()
        self.load()
        self.assertEqual(self.tmux("show-option", "-gv", "@workspace-key").stdout.strip(), "C-w")
        self.assertIn("display-popup", self.tmux("list-keys", "-T", "prefix", "C-w").stdout)
        self.assertIn("TMUX_WORKSPACE_ROOT=~/Custom Projects",
                      self.tmux("show-environment", "-g", "TMUX_WORKSPACE_ROOT").stdout)


if __name__ == "__main__":
    unittest.main()
