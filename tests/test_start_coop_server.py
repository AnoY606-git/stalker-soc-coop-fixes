"""Контракты выбора лимита и безопасного плана без запуска игры или Wine."""

import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


TOOLS = Path(__file__).resolve().parents[1] / "tools"
SCRIPT = TOOLS / "start_coop_server.py"
sys.path.insert(0, str(TOOLS))


class ServerSelectionTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), "Отсутствует CLI выбора лимита сервера")
        self.starter = importlib.import_module("start_coop_server")
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.game = self.root / "Игра с пробелами; $(touch injected)"
        (self.game / "bin" / "dedicated").mkdir(parents=True)
        (self.game / "addons").mkdir()
        self.engine = self.game / "bin" / "dedicated" / "xrEngine.exe"
        self.engine.write_bytes(b"fixture, never executed")
        (self.game / "fsgame_s.ltx").write_bytes(b"fixture")
        (self.game / "addons" / "coop.addon").write_bytes(b"fixture")
        self.wine = self.root / "Wine с пробелом"
        self.wine.write_bytes(b"fixture, never executed")
        self.wine.chmod(0o700)
        self.prefix = self.root / "Отдельный prefix"
        self.prefix.mkdir()
        (self.prefix / "drive_c").mkdir()
        (self.prefix / "dosdevices").mkdir()
        (self.prefix / "system.reg").write_bytes(b"fixture")
        (self.prefix / "user.reg").write_bytes(b"fixture")

    def cli(self, *args, answers=()):
        output, errors = io.StringIO(), io.StringIO()
        with (
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(errors),
            mock.patch.object(self.starter.sys, "platform", "linux"),
            mock.patch.object(self.starter.shutil, "which", return_value=str(self.wine)),
            mock.patch("builtins.input", side_effect=answers),
        ):
            try:
                code = self.starter.main(["--game", str(self.game), *args])
            except SystemExit as error:
                code = error.code
        return code, output.getvalue(), errors.getvalue()

    def plan(self, players=5, **kwargs):
        return self.starter.build_launch_plan(
            self.game, players, platform="linux", wine=str(self.wine), **kwargs
        )

    def test_selected_limits_reach_single_start_argument(self):
        expected = {
            1: "server(coop_l01_escape/coop/hname=ShadowCoop/maxplayers=1/public=0/minplayers=1/portsv=5495) client(localhost)",
            5: "server(coop_l01_escape/coop/hname=ShadowCoop/maxplayers=5/public=0/minplayers=1/portsv=5495) client(localhost)",
            8: "server(coop_l01_escape/coop/hname=ShadowCoop/maxplayers=8/public=0/minplayers=1/portsv=5495) client(localhost)",
        }
        for players, start in expected.items():
            with self.subTest(players=players):
                code, output, errors = self.cli("--players", str(players), "--dry-run")
                self.assertEqual(code, 0, errors)
                plan = json.loads(output)
                self.assertEqual(plan["argv"], [
                    str(self.wine), str(self.engine), "-i", "-noprefetch", "-nointro",
                    "-fsltx", "..\\fsgame_s.ltx", "-use_all_spawn", "-addon=coop.addon",
                    "-start", start,
                ])
                self.assertEqual(plan["cwd"], str(self.game / "bin"))
                self.assertEqual(plan["players"], players)
                self.assertFalse(plan["launch_allowed"])

    def test_windows_plan_uses_native_executable_without_wine(self):
        plan = self.starter.build_launch_plan(self.game, 8, platform="win32")
        self.assertEqual(plan.argv[0], str(self.engine))
        self.assertEqual(plan.argv[1:5], ("-i", "-noprefetch", "-nointro", "-fsltx"))
        self.assertEqual(plan.cwd, self.game / "bin")
        self.assertEqual(plan.env_overrides, {})

    def test_invalid_cli_values_never_prepare_a_process(self):
        for value in ("0", "9", "five", "5.0", "5/public=1", "5;touch injected"):
            with self.subTest(value=value), mock.patch.object(subprocess, "run") as run:
                code, output, errors = self.cli("--players", value, "--dry-run")
                self.assertNotEqual(code, 0)
                self.assertEqual(output, "")
                self.assertIn("1", errors)
                self.assertIn("8", errors)
                run.assert_not_called()

    def test_core_rejects_values_outside_integer_contract(self):
        for value in (0, 9, "5", 5.0, True):
            with self.subTest(value=value), self.assertRaises(self.starter.LaunchError):
                self.plan(value)

    def test_prompt_accepts_choice_or_defaults_to_five(self):
        for answer, expected in (("1", 1), ("8", 8), ("", 5), ("  ", 5)):
            with self.subTest(answer=answer):
                code, output, errors = self.cli("--dry-run", answers=[answer])
                self.assertEqual(code, 0, errors)
                self.assertEqual(json.loads(output)["players"], expected)

    def test_invalid_prompt_has_clear_failure_without_retry_or_launch(self):
        code, output, errors = self.cli("--dry-run", answers=["9"])
        self.assertNotEqual(code, 0)
        self.assertEqual(output, "")
        self.assertIn("1", errors)
        self.assertIn("8", errors)

    def test_eof_does_not_silently_choose_default(self):
        code, output, errors = self.cli("--dry-run", answers=[EOFError])
        self.assertNotEqual(code, 0)
        self.assertEqual(output, "")
        self.assertIn("--players", errors)

    def test_missing_required_game_files_are_reported(self):
        for relative in ("bin/dedicated/xrEngine.exe", "fsgame_s.ltx", "addons/coop.addon"):
            with self.subTest(relative=relative):
                path = self.game / relative
                original = path.read_bytes()
                path.unlink()
                try:
                    code, output, errors = self.cli("--players", "5", "--dry-run")
                    self.assertNotEqual(code, 0)
                    self.assertEqual(output, "")
                    self.assertIn(path.name, errors)
                finally:
                    path.write_bytes(original)

    def test_dry_run_has_no_process_file_or_environment_side_effects(self):
        before_files = {p.relative_to(self.root): p.read_bytes()
                        for p in self.root.rglob("*") if p.is_file()}
        before_directories = {p.relative_to(self.root)
                              for p in self.root.rglob("*") if p.is_dir()}
        before_environment = dict(os.environ)
        with mock.patch.object(subprocess, "run") as run:
            code, output, errors = self.cli(
                "--players", "5", "--dry-run", "--wine-prefix", str(self.prefix)
            )
            self.assertEqual(code, 0, errors)
            run.assert_not_called()
        self.assertEqual(dict(os.environ), before_environment)
        self.assertEqual({p.relative_to(self.root): p.read_bytes()
                          for p in self.root.rglob("*") if p.is_file()}, before_files)
        self.assertEqual({p.relative_to(self.root)
                          for p in self.root.rglob("*") if p.is_dir()}, before_directories)
        plan = json.loads(output)
        self.assertEqual(plan["environment"], {
            "inherit": True, "overrides": {"WINEPREFIX": str(self.prefix)}
        })
        self.assertNotIn("PATH", output)

    def test_dry_run_does_not_require_or_create_a_wine_prefix(self):
        code, output, errors = self.cli("--players", "5", "--dry-run")
        self.assertEqual(code, 0, errors)
        self.assertEqual(json.loads(output)["environment"]["overrides"], {})
        absent = self.root / "missing prefix"
        code, _, errors = self.cli(
            "--players", "5", "--dry-run", "--wine-prefix", str(absent)
        )
        self.assertNotEqual(code, 0)
        self.assertIn("prefix", errors)
        self.assertFalse(absent.exists())

    def test_explicit_wine_path_is_one_argument(self):
        code, output, errors = self.cli(
            "--players", "5", "--dry-run", "--wine", str(self.wine)
        )
        self.assertEqual(code, 0, errors)
        self.assertEqual(json.loads(output)["argv"][:2], [str(self.wine), str(self.engine)])

    def test_missing_wine_is_reported_without_fallback_prefix(self):
        with mock.patch.object(self.starter.shutil, "which", return_value=None):
            with self.assertRaisesRegex(self.starter.LaunchError, "[Ww]ine"):
                self.starter.resolve_wine(None)
        code, _, errors = self.cli(
            "--players", "5", "--dry-run", "--wine", str(self.root / "missing-wine")
        )
        self.assertNotEqual(code, 0)
        self.assertIn("Wine", errors)

    def test_nosound_is_opt_in(self):
        self.assertNotIn("-nosound", self.plan().argv)
        code, output, errors = self.cli("--players", "5", "--dry-run", "--nosound")
        self.assertEqual(code, 0, errors)
        self.assertIn("-nosound", json.loads(output)["argv"])

    def test_real_cli_launch_is_blocked_while_lobby_data_is_unverified(self):
        with mock.patch.object(subprocess, "run") as run:
            code, output, errors = self.cli(
                "--players", "5", "--wine-prefix", str(self.prefix)
            )
            self.assertNotEqual(code, 0)
            self.assertEqual(output, "")
            self.assertIn("lobby data", errors)
            self.assertIn("не проверен", errors)
            run.assert_not_called()

    def test_launch_boundary_also_enforces_the_lobby_gate(self):
        with mock.patch.object(subprocess, "run") as run:
            with self.assertRaisesRegex(self.starter.LaunchError, "lobby data"):
                self.starter.launch(self.plan(wine_prefix=self.prefix))
            run.assert_not_called()

    def test_real_cli_reports_known_blocker_before_prompt_or_setup_checks(self):
        self.engine.unlink()
        for args in ((), ("--players", "5")):
            with self.subTest(args=args), mock.patch.object(subprocess, "run") as run:
                code, output, errors = self.cli(*args, answers=[EOFError])
                self.assertNotEqual(code, 0)
                self.assertEqual(output, "")
                self.assertIn("lobby data", errors)
                self.assertNotIn("Количество игроков", errors)
                run.assert_not_called()

    def test_future_linux_launch_requires_existing_explicit_prefix(self):
        empty = self.root / "empty prefix"
        empty.mkdir()
        with mock.patch.object(self.starter, "LOBBY_DATA_VERIFIED", True):
            for plan in (self.plan(), self.plan(wine_prefix=self.root / "absent"),
                         self.plan(wine_prefix=empty)):
                with self.subTest(plan=plan), mock.patch.object(subprocess, "run") as run:
                    with self.assertRaisesRegex(self.starter.LaunchError, "prefix"):
                        self.starter.launch(plan)
                    run.assert_not_called()
        self.assertFalse((self.root / "absent").exists())

    def test_future_linux_launch_refuses_default_user_prefix(self):
        home = self.root / "home"
        home.mkdir()
        default = home / ".wine"
        default.symlink_to(self.prefix, target_is_directory=True)
        with (
            mock.patch.object(self.starter, "LOBBY_DATA_VERIFIED", True),
            mock.patch.object(self.starter.Path, "home", return_value=home),
            mock.patch.object(subprocess, "run") as run,
        ):
            with self.assertRaisesRegex(self.starter.LaunchError, "~/.wine"):
                self.starter.launch(self.plan(wine_prefix=self.prefix))
            run.assert_not_called()

    def test_future_launch_keeps_paths_literal_uses_copied_environment_and_returns_status(self):
        plan = self.plan(wine_prefix=self.prefix)
        before_environment = dict(os.environ)
        with (
            mock.patch.object(self.starter, "LOBBY_DATA_VERIFIED", True),
            mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 7)) as run,
        ):
            self.assertEqual(self.starter.launch(plan), 7)
        args, kwargs = run.call_args
        self.assertEqual(args, (list(plan.argv),))
        self.assertEqual(kwargs["cwd"], plan.cwd)
        self.assertIs(kwargs["shell"], False)
        self.assertEqual(kwargs["env"]["WINEPREFIX"], str(self.prefix))
        self.assertIsNot(kwargs["env"], os.environ)
        self.assertEqual(dict(os.environ), before_environment)
        self.assertFalse((self.root / "injected").exists())

    def test_future_native_launch_does_not_require_wine_prefix(self):
        plan = self.starter.build_launch_plan(self.game, 1, platform="win32")
        with (
            mock.patch.object(self.starter, "LOBBY_DATA_VERIFIED", True),
            mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0)),
        ):
            self.assertEqual(self.starter.launch(plan), 0)

    def encoded_cli(self, *args):
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "ascii"
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--game", str(self.game), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment, timeout=10,
            check=False,
        )

    def test_cli_dry_run_emits_utf8_json_under_ascii_stdio(self):
        result = self.encoded_cli("--players", "5", "--dry-run", "--wine", str(self.wine))
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        output = result.stdout.decode("utf-8")
        plan = json.loads(output)
        self.assertEqual(plan["cwd"], str(self.game / "bin"))
        self.assertEqual(plan["argv"][:2], [str(self.wine), str(self.engine)])
        self.assertEqual(plan["players"], 5)
        self.assertFalse(plan["launch_allowed"])
        self.assertIn("ещё не проверен", plan["launch_block_reason"])

    def test_cli_help_emits_utf8_under_ascii_stdio(self):
        result = self.encoded_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        self.assertIn("Экспериментальный выбор 1–8 игроков", result.stdout.decode("utf-8"))
        self.assertEqual(result.stderr, b"")

    def test_import_does_not_change_stdio_encoding(self):
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "ascii"
        program = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "before = (sys.stdout.encoding, sys.stderr.encoding); "
            "import start_coop_server; "
            "assert (sys.stdout.encoding, sys.stderr.encoding) == before; "
            "print('import leaves stdio unchanged')"
        )
        result = subprocess.run(
            [sys.executable, "-B", "-c", program, str(TOOLS)], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=environment, timeout=10, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8", errors="replace"))
        self.assertEqual(result.stdout, b"import leaves stdio unchanged\n")


if __name__ == "__main__":
    unittest.main()
