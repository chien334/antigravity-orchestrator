#!/usr/bin/env python3
"""
Comprehensive Unit & End-to-End Automated Test Suite for Cross-Platform Gemini Desktop App Worker Bridge.

Safety Guarantee:
- Zero GUI window launching or clicking into /Applications/Gemini.app.
- Zero mutation of the host OS clipboard.
- All real OS driver flows (MacOSGeminiDriver, WindowsGeminiDriver, LinuxGeminiDriver)
  use unittest.mock.patch and TemporaryDirectory fixtures; read-only plistlib
  inspection of /Applications/Gemini.app/Contents/Info.plist is performed safely when present.
- All live E2E dispatches use MockGeminiDriver and temporary workspace/SQLite dirs.
"""

from __future__ import annotations

from http.client import HTTPConnection
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
import urllib.error
import urllib.request

# Add repository root and orchestrator directory to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
ORCH_DIR = REPO_ROOT / "packages" / "orchestrator"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(ORCH_DIR))

from client import OrchestratorClient
import desktop_worker as dw
from desktop_worker import (
    DEFAULT_MAX_PROMPT_CHARS,
    DesktopDriverStatus,
    DesktopJobCancelledError,
    DesktopJobRequest,
    DesktopJobResult,
    DesktopWorkerManager,
    LinuxGeminiDriver,
    MacOSGeminiDriver,
    MockGeminiDriver,
    SecretRedactionError,
    SecretRedactor,
    SentinelEnvelope,
    WindowsGeminiDriver,
    build_sentinel_prompt,
    detect_desktop_environment,
    extract_sentinel_response,
    get_desktop_driver,
    redact_secrets,
    validate_app_path,
    write_desktop_artifact,
)
from models import (
    EXTERNAL_WORKERS,
    MODEL_REGISTRY,
    PRICING_TABLE,
    USD_TO_VND_RATE,
    compute_cost,
    compute_desktop_quota_saved,
    get_all_models_catalog,
    get_model_metadata,
    is_external_worker,
    normalize_model_name,
    validate_reasoning_effort,
)
from router import (
    compute_model_analytics,
    generate_audit_report,
    recommend_model,
)
from server import (
    GLOBAL_STORE,
    OrchestratorHandler,
    StateStore,
    ThreadingHTTPServer,
)


class TestCrossPlatformDriversAndDiscovery(unittest.TestCase):
    """1. Cross-Platform Driver Discovery & Harness Simulation (macOS/Windows/Linux/Mock)."""

    def test_macos_simulated_app_bundle_and_plistlib_discovery(self):
        """MacOSGeminiDriver discovers simulated .app bundle and parses Info.plist via plistlib."""
        with tempfile.TemporaryDirectory() as tmp:
            for bundle_id, app_name in (
                ("com.google.GeminiMacOS", "Gemini"),
                ("com.google.gemini", "Google Gemini"),
            ):
                app_dir = Path(tmp) / f"{app_name}.app"
                contents = app_dir / "Contents"
                contents.mkdir(parents=True, exist_ok=True)
                plist_bytes = plistlib.dumps(
                    {
                        "CFBundleIdentifier": bundle_id,
                        "CFBundleName": app_name,
                        "CFBundleDisplayName": app_name,
                        "CFBundleShortVersionString": "2.4.1",
                        "CFBundleVersion": "241",
                        "LSMinimumSystemVersion": "14.0",
                        "CFBundleURLTypes": [
                            {"CFBundleURLSchemes": ["googlegemini"]}
                        ],
                    }
                )
                (contents / "Info.plist").write_bytes(plist_bytes)

                drv = MacOSGeminiDriver()
                with mock.patch.object(MacOSGeminiDriver, "_is_app_running", return_value=True):
                    info = drv.discover_app(app_path=str(app_dir))

                self.assertTrue(info["app_detected"])
                self.assertEqual(info["bundle_id"], bundle_id)
                self.assertEqual(info["app_name"], app_name)
                self.assertEqual(info["app_version"], "2.4.1")
                self.assertEqual(info["url_schemes"], ["googlegemini"])
                self.assertTrue(info["app_running"])

    def test_macos_real_local_plist_readonly_safe(self):
        """Read-only plistlib inspection of /Applications/Gemini.app/Contents/Info.plist when present."""
        real_plist = Path("/Applications/Gemini.app/Contents/Info.plist")
        if sys.platform != "darwin" or not real_plist.exists():
            self.skipTest("Local /Applications/Gemini.app not present on host")

        parsed = MacOSGeminiDriver._parse_info_plist(real_plist)
        self.assertIsInstance(parsed, dict)
        self.assertTrue(parsed.get("CFBundleIdentifier"))
        self.assertIn("CFBundleShortVersionString", parsed)

    def test_macos_driver_execute_and_clipboard_restore_on_success(self):
        """MacOSGeminiDriver opens newchat URL, pastes via pbcopy, restores clipboard, and polls AX sentinel."""
        drv = MacOSGeminiDriver()
        job_id = "dsk-macos-ok-01"
        req = DesktopJobRequest(
            job_id=job_id,
            prompt="Analyze architecture",
            driver="macos_ax",
            timeout_sec=10,
            poll_interval_ms=50,
            restore_clipboard=True,
            new_chat=True,
        )
        framed = build_sentinel_prompt(job_id, req.prompt)
        pbcopy_calls: list[bytes] = []

        def fake_pbcopy(data: bytes) -> bool:
            pbcopy_calls.append(data)
            return True

        poll_count = 0
        complete_payload = json.dumps(
            {
                "running": True,
                "busy": False,
                "text": (
                    f"{framed}\nGemini said\n"
                    f"{SentinelEnvelope.start_marker(job_id)}\n"
                    "## Executive Summary\nAll good.\n"
                    f"{SentinelEnvelope.done_marker(job_id)}"
                ),
            }
        )

        def fake_osascript(script, lang="JavaScript", args=None, timeout=10.0):
            nonlocal poll_count
            if script == dw._MACOS_ACTIVATE_AND_CHECK_JXA:
                return json.dumps({"running": True, "windowCount": 1, "focused": True})
            if script == dw._MACOS_PASTE_APPLESCRIPT:
                return ""
            if script == dw._MACOS_SUBMIT_JXA:
                return "clicked_submit"
            if script == dw._MACOS_POLL_AX_JXA:
                poll_count += 1
                if poll_count == 1:
                    return json.dumps({"running": True, "busy": True, "text": "Generating your response..."})
                return complete_payload
            return ""

        tick = 0.0

        def fake_monotonic() -> float:
            nonlocal tick
            tick += 0.6
            return tick

        with mock.patch.object(MacOSGeminiDriver, "_check_screen_locked", return_value="unlocked"), \
             mock.patch.object(MacOSGeminiDriver, "_check_accessibility", return_value="granted"), \
             mock.patch.object(
                 drv,
                 "discover_app",
                 return_value={
                     "app_detected": True,
                     "app_name": "Gemini",
                     "app_path": "/mock/Gemini.app",
                     "bundle_id": "com.google.GeminiMacOS",
                     "app_version": "2.0",
                     "app_running": True,
                 },
             ), \
             mock.patch.object(MacOSGeminiDriver, "_check_orca", return_value=None), \
             mock.patch.object(MacOSGeminiDriver, "_pbpaste_bytes", return_value=b"ORIGINAL_USER_CLIP"), \
             mock.patch.object(MacOSGeminiDriver, "_pbcopy_bytes", side_effect=fake_pbcopy), \
             mock.patch.object(MacOSGeminiDriver, "_run_osascript", side_effect=fake_osascript), \
             mock.patch("desktop_worker.subprocess.run") as mock_sub_run, \
             mock.patch("desktop_worker.time.sleep", return_value=None), \
             mock.patch("desktop_worker.time.monotonic", side_effect=fake_monotonic):

            mock_sub_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            raw_text, meta = drv.execute_prompt(framed, job_id, req, threading.Event())

        # Verify googlegemini://newchat was launched safely via argv list (no shell=True)
        mock_sub_run.assert_called_once()
        open_cmd = mock_sub_run.call_args[0][0]
        self.assertIn("googlegemini://newchat?ext_src=app_shortcut", open_cmd)
        self.assertFalse(mock_sub_run.call_args.kwargs.get("shell", False))

        # Verify clipboard was written with framed prompt AND then restored to ORIGINAL_USER_CLIP
        self.assertEqual(len(pbcopy_calls), 2)
        self.assertEqual(pbcopy_calls[0], framed.encode("utf-8"))
        self.assertEqual(pbcopy_calls[1], b"ORIGINAL_USER_CLIP")
        self.assertTrue(meta["clipboard_restored"])
        self.assertTrue(SentinelEnvelope.has_complete_sentinel(raw_text, job_id))

    def test_macos_driver_restores_clipboard_even_on_exception(self):
        """MacOSGeminiDriver restores prior clipboard inside finally block even when paste fails."""
        drv = MacOSGeminiDriver()
        job_id = "dsk-macos-err-01"
        req = DesktopJobRequest(job_id=job_id, prompt="Test error restore", driver="macos_ax")
        framed = build_sentinel_prompt(job_id, req.prompt)
        pbcopy_calls: list[bytes] = []

        def fake_osascript(script, lang="JavaScript", args=None, timeout=10.0):
            if script == dw._MACOS_ACTIVATE_AND_CHECK_JXA:
                return json.dumps({"running": True, "windowCount": 1, "focused": True})
            if script == dw._MACOS_PASTE_APPLESCRIPT:
                raise TimeoutError("Simulated paste timeout")
            return ""

        with mock.patch.object(MacOSGeminiDriver, "_check_screen_locked", return_value="unlocked"), \
             mock.patch.object(MacOSGeminiDriver, "_check_accessibility", return_value="granted"), \
             mock.patch.object(
                 drv,
                 "discover_app",
                 return_value={
                     "app_detected": True,
                     "app_name": "Gemini",
                     "app_path": "/mock/Gemini.app",
                     "bundle_id": "com.google.GeminiMacOS",
                 },
             ), \
             mock.patch.object(MacOSGeminiDriver, "_check_orca", return_value=None), \
             mock.patch.object(MacOSGeminiDriver, "_pbpaste_bytes", return_value=b"KEEP_ME_SAFE"), \
             mock.patch.object(MacOSGeminiDriver, "_pbcopy_bytes", side_effect=lambda d: pbcopy_calls.append(d) or True), \
             mock.patch.object(MacOSGeminiDriver, "_run_osascript", side_effect=fake_osascript), \
             mock.patch("desktop_worker.subprocess.run") as mock_sub_run, \
             mock.patch("desktop_worker.time.sleep", return_value=None):

            mock_sub_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            with self.assertRaises(TimeoutError):
                drv.execute_prompt(framed, job_id, req, threading.Event())

        self.assertEqual(pbcopy_calls, [framed.encode("utf-8"), b"KEEP_ME_SAFE"])

    def test_windows_driver_discovery_and_env_prompt_file_no_interpolation(self):
        """WindowsGeminiDriver discovers Gemini.exe, passes prompt via AGY_DESKTOP_PROMPT_FILE, and cleans up temp file."""
        with tempfile.TemporaryDirectory() as tmp:
            local_app = Path(tmp) / "LocalAppData"
            exe_path = local_app / "Programs" / "Gemini" / "Gemini.exe"
            exe_path.parent.mkdir(parents=True, exist_ok=True)
            exe_path.write_text("stub", encoding="utf-8")

            drv = WindowsGeminiDriver()
            env_patch = {
                "LOCALAPPDATA": str(local_app),
                "APPDATA": str(Path(tmp) / "AppData"),
                "ProgramData": str(Path(tmp) / "ProgramData"),
            }
            with mock.patch.dict(os.environ, env_patch, clear=False), \
                 mock.patch.object(WindowsGeminiDriver, "_find_powershell", return_value="C:\\Windows\\System32\\powershell.exe"):

                status = drv.doctor()
                self.assertEqual(status.os_platform, "win32")
                self.assertEqual(status.driver_name, "windows_uia")
                self.assertTrue(status.ready)
                self.assertTrue(status.app_detected)
                self.assertEqual(status.app_path, str(exe_path))

                job_id = "dsk-win-01"
                secret_free_prompt = "UNIQUE_WIN_PROMPT_MARKER_9911 $(whoami) `exit`"
                req = DesktopJobRequest(job_id=job_id, prompt=secret_free_prompt, driver="windows_uia")
                framed = build_sentinel_prompt(job_id, req.prompt)

                captured_env: dict[str, str] = {}
                captured_stdin: list[str] = []
                prompt_file_contents_during_exec: list[str] = []

                class FakeProc:
                    def __init__(self, cmd, stdin=None, stdout=None, stderr=None, text=None, encoding=None, env=None):
                        captured_env.update(env or {})
                        self.cmd = cmd
                        self.returncode = 0
                        self._stdin_buf = []

                        class _Stdin:
                            def write(_, s):
                                self._stdin_buf.append(s)

                            def close(_):
                                captured_stdin.append("".join(self._stdin_buf))
                                pfile = captured_env.get("AGY_DESKTOP_PROMPT_FILE")
                                if pfile and os.path.exists(pfile):
                                    prompt_file_contents_during_exec.append(
                                        Path(pfile).read_text(encoding="utf-8")
                                    )

                        class _Stdout:
                            def read(_):
                                return json.dumps(
                                    {
                                        "text": (
                                            f"{SentinelEnvelope.start_marker(job_id)}\n"
                                            "## Executive Summary\nWindows UIA OK\n"
                                            f"{SentinelEnvelope.done_marker(job_id)}"
                                        ),
                                        "clipboard_restored": True,
                                    }
                                )

                        class _Stderr:
                            def read(_):
                                return ""

                        self.stdin = _Stdin()
                        self.stdout = _Stdout()
                        self.stderr = _Stderr()

                    def poll(self):
                        return 0

                with mock.patch("desktop_worker.subprocess.Popen", side_effect=FakeProc):
                    raw_text, meta = drv.execute_prompt(framed, job_id, req, threading.Event())

                self.assertEqual(meta["backend"], "windows_uia")
                self.assertTrue(meta["clipboard_restored"])
                self.assertIn(SentinelEnvelope.done_marker(job_id), raw_text)

                # Verify prompt was passed via AGY_DESKTOP_PROMPT_FILE and NEVER interpolated into PS script
                self.assertIn("AGY_DESKTOP_PROMPT_FILE", captured_env)
                self.assertEqual(prompt_file_contents_during_exec, [framed])
                self.assertNotIn("UNIQUE_WIN_PROMPT_MARKER_9911", captured_stdin[0])
                # Temp file MUST be deleted in finally
                self.assertFalse(os.path.exists(captured_env["AGY_DESKTOP_PROMPT_FILE"]))

    def test_linux_driver_headless_diagnostics_and_wayland_flow(self):
        """LinuxGeminiDriver reports headless remediation and restores clipboard on Wayland/X11."""
        drv = LinuxGeminiDriver()

        # 1. Headless CI diagnostic check (no DISPLAY or WAYLAND_DISPLAY)
        clean_env = dict(os.environ)
        clean_env.pop("DISPLAY", None)
        clean_env.pop("WAYLAND_DISPLAY", None)
        with mock.patch.dict(os.environ, clean_env, clear=True):
            headless = drv.doctor()
        self.assertEqual(headless.os_platform, "linux")
        self.assertEqual(headless.driver_name, "linux_pwa")
        self.assertFalse(headless.ready)
        self.assertEqual(headless.permissions["display"], "missing")
        self.assertTrue(any("--driver mock" in step for step in headless.remediation_steps))

        # 2. Wayland execution flow with mocked wl-copy / wl-paste / wtype / google-chrome
        job_id = "dsk-linux-01"
        req = DesktopJobRequest(job_id=job_id, prompt="Linux PWA test", driver="linux_pwa", poll_interval_ms=100)
        framed = build_sentinel_prompt(job_id, req.prompt)

        clipboard_writes: list[bytes] = []
        clipboard_reads = iter(
            [
                b"PRIOR_LINUX_CLIP",  # initial save
                b"POLL_CLIP_BEFORE_COPY",  # poll 1 save
                (
                    f"{SentinelEnvelope.start_marker(job_id)}\n"
                    "## Executive Summary\nWayland OK\n"
                    f"{SentinelEnvelope.done_marker(job_id)}"
                ).encode("utf-8"),  # poll 1 read
                b"POLL_CLIP_BEFORE_COPY_2",  # poll 2 save
                (
                    f"{SentinelEnvelope.start_marker(job_id)}\n"
                    "## Executive Summary\nWayland OK\n"
                    f"{SentinelEnvelope.done_marker(job_id)}"
                ).encode("utf-8"),  # poll 2 read
            ]
        )
        mono_ticks = iter([0.0, 0.0, 0.1, 0.2, 0.9, 1.5])

        def fake_which(name: str):
            mapping = {
                "google-chrome": "/usr/bin/google-chrome",
                "wl-copy": "/usr/bin/wl-copy",
                "wl-paste": "/usr/bin/wl-paste",
                "wtype": "/usr/bin/wtype",
            }
            return mapping.get(name)

        with mock.patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=False), \
             mock.patch("desktop_worker.shutil.which", side_effect=fake_which), \
             mock.patch.object(LinuxGeminiDriver, "_read_clipboard", side_effect=lambda *a: next(clipboard_reads)), \
             mock.patch.object(LinuxGeminiDriver, "_write_clipboard", side_effect=lambda k, b, d: clipboard_writes.append(d) or True), \
             mock.patch.object(LinuxGeminiDriver, "_send_hotkey", return_value=None), \
             mock.patch("desktop_worker.subprocess.Popen") as mock_popen, \
             mock.patch("desktop_worker.time.sleep", return_value=None), \
             mock.patch("desktop_worker.time.monotonic", side_effect=lambda: next(mono_ticks, 2.0)):

            status = drv.doctor()
            self.assertTrue(status.ready)
            self.assertEqual(status.permissions["clipboard"], "wl")
            self.assertEqual(status.permissions["input"], "wtype")

            raw_text, meta = drv.execute_prompt(framed, job_id, req, threading.Event())

        mock_popen.assert_called_once()
        self.assertIn("--app=https://gemini.google.com", mock_popen.call_args[0][0])
        self.assertEqual(clipboard_writes[0], framed.encode("utf-8"))
        self.assertEqual(clipboard_writes[1], b"PRIOR_LINUX_CLIP")
        self.assertTrue(meta["clipboard_restored"])
        self.assertTrue(SentinelEnvelope.has_complete_sentinel(raw_text, job_id))

    def test_mock_driver_deterministic_and_triggers(self):
        """MockGeminiDriver executes deterministically and honors trigger tags."""
        with mock.patch.dict(os.environ, {"MOCK_DELAY_MS": "0"}, clear=False):
            drv = get_desktop_driver(driver="mock", target_os="darwin")
            self.assertIsInstance(drv, MockGeminiDriver)
            status = drv.doctor()
            self.assertTrue(status.ready)
            self.assertEqual(status.bundle_id, "com.google.GeminiMacOS.mock")

            # Normal execution
            req = DesktopJobRequest(job_id="dsk-mock-01", prompt="Analyze pipeline", driver="mock")
            raw, meta = drv.execute_prompt(build_sentinel_prompt(req.job_id, req.prompt), req.job_id, req, threading.Event())
            self.assertTrue(meta["clipboard_restored"])
            clean, ok = extract_sentinel_response(raw, req.job_id)
            self.assertTrue(ok)
            self.assertIn("## Executive Summary", clean)

            # [MOCK_TIMEOUT]
            with self.assertRaises(TimeoutError):
                drv.execute_prompt("[MOCK_TIMEOUT]", "dsk-mock-t", req, threading.Event())

            # [MOCK_ERROR]
            with self.assertRaises(RuntimeError):
                drv.execute_prompt("[MOCK_ERROR]", "dsk-mock-e", req, threading.Event())

            # [MOCK_CHROME] -> UI chrome stripped cleanly
            chrome_raw, _ = drv.execute_prompt("[MOCK_CHROME] inspect", "dsk-mock-c", req, threading.Event())
            chrome_clean, chrome_ok = extract_sentinel_response(chrome_raw, "dsk-mock-c")
            self.assertTrue(chrome_ok)
            self.assertNotIn("Gemini said", chrome_clean)
            self.assertNotIn("Show thinking", chrome_clean)
            self.assertNotIn("Export to Docs", chrome_clean)

            # [MOCK_PARTIAL] -> missing end sentinel triggers failed status in DesktopWorkerManager
            with tempfile.TemporaryDirectory() as tmp:
                mgr = DesktopWorkerManager(
                    artifacts_dir=Path(tmp) / "artifacts",
                    lock_path=Path(tmp) / "worker.lock",
                )
                partial_res = mgr.execute_job(
                    DesktopJobRequest(job_id="dsk-mock-p", prompt="[MOCK_PARTIAL] test", driver="mock")
                )
                self.assertEqual(partial_res.status, "failed")
                self.assertIn("sentinel missing", (partial_res.error or "").lower())

    def test_validate_app_path_rejects_unapproved_and_accepts_allowlisted(self):
        """validate_app_path rejects Terminal.app/cmd.exe/bash/UNC/flags across macOS, Windows, and Linux."""
        with tempfile.TemporaryDirectory() as tmp:
            # 1. macOS: reject unapproved .app bundle (e.g. Terminal.app), leading dash, and non-.app file
            bad_app = Path(tmp) / "Terminal.app"
            (bad_app / "Contents").mkdir(parents=True)
            (bad_app / "Contents" / "Info.plist").write_bytes(
                plistlib.dumps({"CFBundleIdentifier": "com.apple.Terminal", "CFBundleName": "Terminal"})
            )
            with self.assertRaises(ValueError):
                validate_app_path(str(bad_app), "darwin")
            with self.assertRaises(ValueError):
                MacOSGeminiDriver().discover_app(app_path=str(bad_app))
            with self.assertRaises(ValueError):
                MacOSGeminiDriver().execute_prompt(
                    "prompt", "dsk-bad-mac", DesktopJobRequest(job_id="dsk-bad-mac", prompt="p", app_path=str(bad_app)), threading.Event()
                )
            if Path("/System/Applications/Utilities/Terminal.app").exists():
                with self.assertRaises(ValueError):
                    validate_app_path("/System/Applications/Utilities/Terminal.app", "darwin")
            with self.assertRaises(ValueError):
                validate_app_path("-a", "darwin")
            with self.assertRaises(ValueError):
                validate_app_path("/bin/sh", "darwin")

            # Valid Chrome PWA bundle ID should pass on macOS
            pwa_app = Path(tmp) / "Gemini PWA.app"
            (pwa_app / "Contents").mkdir(parents=True)
            (pwa_app / "Contents" / "Info.plist").write_bytes(
                plistlib.dumps({"CFBundleIdentifier": "com.google.Chrome.app.gemini1234", "CFBundleName": "Gemini"})
            )
            self.assertTrue(validate_app_path(str(pwa_app), "darwin").endswith(".app"))

            # 2. Windows: reject cmd.exe, powershell.exe, UNC paths; accept Gemini.exe / msedge.exe / chrome.exe
            for bad_win in (
                r"C:\Windows\System32\cmd.exe",
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                r"\\evil-smb\share\Gemini.exe",
            ):
                with self.assertRaises(ValueError):
                    validate_app_path(bad_win, "win32")
                with self.assertRaises(ValueError):
                    WindowsGeminiDriver().discover_app(app_path=bad_win)

            fake_cmd = Path(tmp) / "cmd.exe"
            fake_cmd.write_text("stub", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_app_path(str(fake_cmd), "win32")

            win_ok = Path(tmp) / "msedge.exe"
            win_ok.write_text("stub", encoding="utf-8")
            self.assertEqual(Path(validate_app_path(str(win_ok), "win32")).name.lower(), "msedge.exe")

            # 3. Linux: reject bash/xterm/python3; accept chrome/chromium/edge binaries
            for bad_linux in ("/bin/bash", "/usr/bin/xterm", "python3", "-evil"):
                with self.assertRaises(ValueError):
                    validate_app_path(bad_linux, "linux")
                with self.assertRaises(ValueError):
                    LinuxGeminiDriver().discover_app(app_path=bad_linux)
            self.assertEqual(validate_app_path("/usr/bin/google-chrome", "linux"), "/usr/bin/google-chrome")
            self.assertEqual(validate_app_path("chromium-browser", "linux"), "chromium-browser")

    def test_windows_driver_150kb_pipe_and_output_file_cleanup(self):
        """WindowsGeminiDriver handles >150KB stdout/stderr/response without OS pipe deadlock and cleans temp files."""
        with tempfile.TemporaryDirectory() as tmp:
            local_app = Path(tmp) / "LocalAppData"
            exe_path = local_app / "Programs" / "Gemini" / "Gemini.exe"
            exe_path.parent.mkdir(parents=True, exist_ok=True)
            exe_path.write_text("stub", encoding="utf-8")

            drv = WindowsGeminiDriver()
            job_id = "dsk-win-150kb"
            req = DesktopJobRequest(job_id=job_id, prompt="Analyze 150KB payload", driver="windows_uia", timeout_sec=15)
            framed = build_sentinel_prompt(job_id, req.prompt)

            captured_env: dict[str, str] = {}
            real_popen = subprocess.Popen
            child_code = (
                "import json, os, sys\n"
                "_ = sys.stdin.read()\n"
                "sys.stdout.write('X' * 160000); sys.stdout.flush()\n"
                "sys.stderr.write('Y' * 80000); sys.stderr.flush()\n"
                "jid = os.environ['AGY_DESKTOP_JOB_ID']\n"
                "out_p = os.environ['AGY_DESKTOP_OUTPUT_FILE']\n"
                "body = '<<<AGY_DESKTOP_START:' + jid + '>>>\\n' + ('Z' * 155000) + '\\n<<<AGY_DESKTOP_DONE:' + jid + '>>>'\n"
                "tmp_p = out_p + '.tmp'\n"
                "with open(tmp_p, 'w', encoding='utf-8') as f: json.dump({'text': body, 'clipboard_restored': True}, f)\n"
                "os.replace(tmp_p, out_p)\n"
            )

            def popen_wrapper(cmd, stdin=None, stdout=None, stderr=None, text=None, encoding=None, env=None):
                captured_env.update(env or {})
                return real_popen(
                    [sys.executable, "-c", child_code],
                    stdin=stdin,
                    stdout=stdout,
                    stderr=stderr,
                    text=text,
                    encoding=encoding,
                    env=env,
                )

            with mock.patch.dict(os.environ, {"LOCALAPPDATA": str(local_app)}, clear=False), \
                 mock.patch.object(WindowsGeminiDriver, "_find_powershell", return_value="powershell.exe"), \
                 mock.patch("desktop_worker.subprocess.Popen", side_effect=popen_wrapper):
                raw_text, meta = drv.execute_prompt(framed, job_id, req, threading.Event())

            self.assertGreater(len(raw_text), 150_000)
            self.assertTrue(SentinelEnvelope.has_complete_sentinel(raw_text, job_id))
            self.assertTrue(meta["clipboard_restored"])
            self.assertIn("AGY_DESKTOP_PROMPT_FILE", captured_env)
            self.assertIn("AGY_DESKTOP_OUTPUT_FILE", captured_env)
            self.assertFalse(os.path.exists(captured_env["AGY_DESKTOP_PROMPT_FILE"]))
            self.assertFalse(os.path.exists(captured_env["AGY_DESKTOP_OUTPUT_FILE"]))

    def test_linux_driver_clears_empty_clipboard_on_restore(self):
        """LinuxGeminiDriver clears clipboard in finally when prior clipboard was empty (None)."""
        drv = LinuxGeminiDriver()
        job_id = "dsk-linux-empty-clip"
        req = DesktopJobRequest(job_id=job_id, prompt="Test empty clip", driver="linux_pwa", poll_interval_ms=100)
        framed = build_sentinel_prompt(job_id, req.prompt)

        clear_calls: list[str] = []
        reads = iter([
            None,  # initial clipboard empty
            None,  # poll save empty
            (
                f"{SentinelEnvelope.start_marker(job_id)}\n"
                "## Executive Summary\nOK\n"
                f"{SentinelEnvelope.done_marker(job_id)}"
            ).encode("utf-8"),
            None,
            (
                f"{SentinelEnvelope.start_marker(job_id)}\n"
                "## Executive Summary\nOK\n"
                f"{SentinelEnvelope.done_marker(job_id)}"
            ).encode("utf-8"),
        ])
        mono_ticks = iter([0.0, 0.0, 0.1, 0.2, 0.9, 1.5])

        def fake_which(name: str):
            return {
                "google-chrome": "/usr/bin/google-chrome",
                "wl-copy": "/usr/bin/wl-copy",
                "wl-paste": "/usr/bin/wl-paste",
                "wtype": "/usr/bin/wtype",
            }.get(name)

        with mock.patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=False), \
             mock.patch("desktop_worker.shutil.which", side_effect=fake_which), \
             mock.patch.object(LinuxGeminiDriver, "_read_clipboard", side_effect=lambda *a: next(reads)), \
             mock.patch.object(LinuxGeminiDriver, "_write_clipboard", return_value=True), \
             mock.patch.object(LinuxGeminiDriver, "_clear_clipboard", side_effect=lambda k, b: clear_calls.append(k) or True), \
             mock.patch.object(LinuxGeminiDriver, "_send_hotkey", return_value=None), \
             mock.patch("desktop_worker.subprocess.Popen"), \
             mock.patch("desktop_worker.time.sleep", return_value=None), \
             mock.patch("desktop_worker.time.monotonic", side_effect=lambda: next(mono_ticks, 2.0)):
            _, meta = drv.execute_prompt(framed, job_id, req, threading.Event())

        self.assertTrue(meta["clipboard_restored"])
        self.assertGreaterEqual(len(clear_calls), 2)


class TestSentinelAndSecretRedactor(unittest.TestCase):
    """2. Split-Literal Sentinel Framing, Echo Immunity & SecretRedactor."""

    def test_build_sentinel_prompt_split_literal_echo_immunity(self):
        """build_sentinel_prompt never embeds contiguous <<<AGY_DESKTOP_DONE:{job_id}>>>."""
        job_id = "dsk-echo-42"
        built = build_sentinel_prompt(job_id, "Review spec", metadata={"task_id": "TASK-26"})
        self.assertIn(SentinelEnvelope.start_marker(job_id), built)
        self.assertIn(SentinelEnvelope.PROMPT_BOUNDARY, built)
        self.assertIn("- task_id: TASK-26", built)
        self.assertNotIn(f"<<<AGY_DESKTOP_DONE:{job_id}>>>", built)

    def test_has_complete_sentinel_ignores_prompt_echo_and_requires_order(self):
        """has_complete_sentinel ignores prompt echo, waits for contiguous sentinel after boundary."""
        job_id = "dsk-order-99"
        built = build_sentinel_prompt(job_id, "Inspect router")
        start_tok = SentinelEnvelope.start_marker(job_id)
        done_tok = SentinelEnvelope.done_marker(job_id)

        # 1. Only prompt in window -> False
        self.assertFalse(SentinelEnvelope.has_complete_sentinel(built, job_id))

        # 2. Assistant started streaming without done marker -> False
        streaming = f"{built}\nGemini said\n{start_tok}\n## Executive Summary\nStreaming..."
        self.assertFalse(SentinelEnvelope.has_complete_sentinel(streaming, job_id))

        # 3. Done marker appeared before start marker -> False
        out_of_order = f"{built}\n{done_tok}\n{start_tok}"
        self.assertFalse(SentinelEnvelope.has_complete_sentinel(out_of_order, job_id))

        # 4. Complete response after boundary -> True
        complete = f"{streaming}\nAll done.\n{done_tok}\nSend feedback"
        self.assertTrue(SentinelEnvelope.has_complete_sentinel(complete, job_id))

        # 5. assistant_only=True ignores prompt boundary requirement
        self.assertTrue(
            SentinelEnvelope.has_complete_sentinel(
                f"{start_tok}\nResult\n{done_tok}",
                job_id,
                assistant_only=True,
            )
        )

    def test_extract_sentinel_response_strips_ui_chrome(self):
        """extract_sentinel_response extracts clean markdown and strips UI chrome lines."""
        job_id = "dsk-chrome-77"
        built = build_sentinel_prompt(job_id, "Prompt text")
        raw = (
            f"{built}\n"
            "Show thinking\n"
            "Gemini said\n"
            f"{SentinelEnvelope.start_marker(job_id)}\n"
            "Show thinking\n"
            "## Executive Summary\nClean output line.\n"
            "Copy\n"
            "Export to Docs\n"
            f"{SentinelEnvelope.done_marker(job_id)}\n"
            "Send feedback\n"
        )
        clean, matched = extract_sentinel_response(raw, job_id)
        self.assertTrue(matched)
        self.assertEqual(clean, "## Executive Summary\nClean output line.")

    def test_secret_redactor_patterns_and_strict_exception(self):
        """SecretRedactor scrubs API keys, JWTs, PEM blocks, DSNs, and raises on strict mode."""
        # Construct realistic synthetic secret tokens without embedding real credentials
        g_key = "AIza" + "SyA1234567890abcdefghijkLMNOPQRSTUV"
        oai_key = "sk-proj-" + "AbCdEfGhIjKlMnOpQrStUvWxYz123456"
        gh_tok = "ghp_" + "1234567890abcdefghijklmnopqrstuvwxyz"
        aws_key = "AKIA" + "IOSFODNN7EXAMPLE"
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAtokenbody\n-----END RSA PRIVATE KEY-----"
        dsn = "postgresql://admin:supersecretpass@db.internal:5432/prod"
        bearer = "Authorization: Bearer super_secret_token_value_12345"

        sample = "\n".join([g_key, oai_key, gh_tok, aws_key, jwt, pem, dsn, bearer])
        sanitized, counts, blocked = redact_secrets(sample, strict=False, redact=True)

        self.assertFalse(blocked)
        self.assertNotIn(g_key, sanitized)
        self.assertNotIn(oai_key, sanitized)
        self.assertNotIn(gh_tok, sanitized)
        self.assertNotIn(aws_key, sanitized)
        self.assertNotIn(jwt, sanitized)
        self.assertNotIn("MIIEowIBAAKCAQEAtokenbody", sanitized)
        self.assertNotIn("supersecretpass", sanitized)
        self.assertNotIn("super_secret_token_value_12345", sanitized)

        for expected_cat in (
            "google_api_key",
            "openai_anthropic_key",
            "github_token",
            "aws_access_key",
            "jwt_token",
            "private_key_pem",
            "dsn_credentials",
            "bearer_or_secret_kv",
        ):
            self.assertGreaterEqual(counts.get(expected_cat, 0), 1, f"Missing redaction category {expected_cat}")

        # Strict mode with raise_on_strict=True raises SecretRedactionError
        with self.assertRaises(SecretRedactionError) as ctx:
            redact_secrets(f"leak={g_key}", strict=True, redact=True, raise_on_strict=True)
        self.assertGreaterEqual(ctx.exception.total_redactions, 1)

        # JSON-quoted key-value secret pattern is also scrubbed
        json_secret_text = '{"api_key": "secret_value_1234", "token": "my_secret_tok_9999"}'
        scrubbed_json, json_counts, _ = redact_secrets(json_secret_text, strict=False, redact=True)
        self.assertNotIn("secret_value_1234", scrubbed_json)
        self.assertNotIn("my_secret_tok_9999", scrubbed_json)
        self.assertGreaterEqual(json_counts.get("bearer_or_secret_kv", 0), 2)

        # DesktopWorkerManager strictly rejects secrets without invoking driver.execute_prompt
        with tempfile.TemporaryDirectory() as tmp:
            mgr = DesktopWorkerManager(
                artifacts_dir=Path(tmp) / "artifacts",
                lock_path=Path(tmp) / "worker.lock",
            )
            with mock.patch.object(MockGeminiDriver, "execute_prompt") as mock_exec:
                res = mgr.execute_job(
                    DesktopJobRequest(
                        job_id="dsk-strict-01",
                        prompt=f"Analyze with key {g_key}",
                        driver="mock",
                        strict_secrets=True,
                    )
                )
            mock_exec.assert_not_called()
            self.assertEqual(res.status, "rejected_secrets")
            self.assertGreaterEqual(res.redactions.get("google_api_key", 0), 1)


class TestDesktopManagerMutexCancellationAndArtifacts(unittest.TestCase):
    """3. Single-Window Concurrency Mutex, Cancellation & Artifact Path Guard."""

    def test_concurrency_mutex_serializes_threads(self):
        """3 concurrent execute_job calls execute strictly sequentially (max_concurrent == 1)."""
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.dict(os.environ, {"MOCK_DELAY_MS": "30"}, clear=False):
            mgr = DesktopWorkerManager(
                artifacts_dir=Path(tmp) / "artifacts",
                lock_path=Path(tmp) / "worker.lock",
            )

            active = 0
            max_active = 0
            counter_lock = threading.Lock()
            orig_exec = MockGeminiDriver.execute_prompt

            def tracked_exec(self_drv, framed, job_id, req, cancel_ev):
                nonlocal active, max_active
                with counter_lock:
                    active += 1
                    max_active = max(max_active, active)
                try:
                    return orig_exec(self_drv, framed, job_id, req, cancel_ev)
                finally:
                    with counter_lock:
                        active -= 1

            results: list[DesktopJobResult] = []
            errors: list[Exception] = []

            def worker(idx: int):
                try:
                    r = mgr.execute_job(
                        DesktopJobRequest(job_id=f"dsk-conc-{idx}", prompt=f"Job {idx}", driver="mock")
                    )
                    results.append(r)
                except Exception as exc:
                    errors.append(exc)

            with mock.patch.object(MockGeminiDriver, "execute_prompt", tracked_exec):
                threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(timeout=10)

            self.assertEqual(errors, [])
            self.assertEqual(len(results), 3)
            self.assertEqual(max_active, 1)
            self.assertTrue(all(r.status == "completed" for r in results))

    def test_cancellation_aborts_cleanly(self):
        """Setting cancel_event before or during execution returns status='cancelled'."""
        with tempfile.TemporaryDirectory() as tmp:
            mgr = DesktopWorkerManager(
                artifacts_dir=Path(tmp) / "artifacts",
                lock_path=Path(tmp) / "worker.lock",
            )
            ev = threading.Event()
            ev.set()
            res = mgr.execute_job(
                DesktopJobRequest(job_id="dsk-cancel-01", prompt="Will cancel", driver="mock"),
                cancel_event=ev,
            )
            self.assertEqual(res.status, "cancelled")

    def test_write_desktop_artifact_path_traversal_guard(self):
        """write_desktop_artifact rejects ../../ traversal and absolute escapes outside output_dir."""
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "reports"
            out_dir.mkdir()
            req_bad = DesktopJobRequest(job_id="dsk-trav-1", prompt="x", output_path="../../evil.md")
            with self.assertRaises(ValueError):
                write_desktop_artifact(
                    "dsk-trav-1", "# bad", req_bad, "mock", "darwin", 10, {}, 0.0, output_dir=out_dir
                )

            req_abs_bad = DesktopJobRequest(job_id="dsk-trav-2", prompt="x", output_path="/tmp/evil.md")
            with self.assertRaises(ValueError):
                write_desktop_artifact(
                    "dsk-trav-2", "# bad", req_abs_bad, "mock", "darwin", 10, {}, 0.0, output_dir=out_dir
                )

            req_ok = DesktopJobRequest(job_id="dsk-ok-1", prompt="x", task_id="TASK-26")
            artifact = write_desktop_artifact(
                "dsk-ok-1",
                "## Executive Summary\nValid report.",
                req_ok,
                "mock",
                "darwin",
                25,
                {"github_token": 1},
                0.0125,
                output_dir=out_dir,
            )
            written = Path(artifact)
            self.assertTrue(written.exists())
            content = written.read_text(encoding="utf-8")
            self.assertIn("job_id: dsk-ok-1", content)
            self.assertIn("task_id: TASK-26", content)
            self.assertIn("## Executive Summary", content)


class TestExternalWorkerCostAndHybridRouter(unittest.TestCase):
    """4. External Worker Catalog, $0.00 Cost, Quota Saved Math & Hybrid Router Rule 1.5."""

    def test_external_workers_catalog_and_zero_api_cost(self):
        """MODEL_REGISTRY preserves 5 API tiers; gemini-desktop-app lives in EXTERNAL_WORKERS with $0.00 cost."""
        self.assertEqual(len(MODEL_REGISTRY), 5)
        self.assertIn("gemini-desktop-app", EXTERNAL_WORKERS)
        self.assertNotIn("gemini-desktop-app", MODEL_REGISTRY)

        catalog = get_all_models_catalog()
        self.assertIn("gemini-desktop-app", catalog)
        self.assertTrue(is_external_worker("gemini-desktop-app"))
        self.assertTrue(is_external_worker("desktop"))
        self.assertTrue(is_external_worker("gui-worker"))
        self.assertFalse(is_external_worker("gemini-4-hydrogen"))

        self.assertEqual(normalize_model_name("desktop-worker"), "gemini-desktop-app")
        self.assertEqual(PRICING_TABLE["gemini-desktop-app"], {"in": 0.0, "out": 0.0, "cache": 0.0})
        meta = get_model_metadata("gemini-desktop-app")
        self.assertEqual(meta["execution_mode"], "desktop_bridge")
        self.assertEqual(validate_reasoning_effort("gemini-desktop-app", None), (True, None))

        cost = compute_cost("gemini-desktop-app", 500_000, 100_000, 200_000)
        self.assertEqual(cost["usd"], 0.0)
        self.assertEqual(cost["vnd"], 0)
        self.assertEqual(cost["saved_usd"], 0.0)
        self.assertEqual(cost["saved_vnd"], 0)

    def test_compute_desktop_quota_saved_math(self):
        """compute_desktop_quota_saved approximates ceil(chars/4) tokens against Carbon baseline."""
        # 40,000 input chars = 10,000 tokens; 8,000 output chars = 2,000 tokens
        # Carbon rates: $2.00/1M in, $10.00/1M out => 0.01*2 + 0.002*10 = $0.0400 -> 1016 VND
        quota = compute_desktop_quota_saved(40_000, 8_000, baseline_model="gemini-4-carbon")
        self.assertEqual(quota["est_input_tokens"], 10_000)
        self.assertEqual(quota["est_output_tokens"], 2_000)
        self.assertEqual(quota["est_total_tokens"], 12_000)
        self.assertEqual(quota["baseline_model"], "gemini-4-carbon")
        self.assertEqual(quota["saved_usd"], 0.04)
        self.assertEqual(quota["saved_vnd"], round(0.04 * USD_TO_VND_RATE))

    def test_hybrid_desktop_routing_rule_1_5_and_guardrails(self):
        """Rule 1.5 offloads eligible heavy non-mutating synthesis while preserving Rule 1 & Rule 2."""
        # 1. spec-engineer (high) in hybrid_desktop with desktop_available=True -> gemini-desktop-app
        r1 = recommend_model(
            agent_type="spec-engineer",
            complexity="high",
            budget_mode="hybrid_desktop",
            desktop_available=True,
        )["recommendation"]
        self.assertEqual(r1["model"], "gemini-desktop-app")
        self.assertEqual(r1["execution_mode"], "desktop_bridge")
        self.assertEqual(r1["estimated_cost_tier"], "$0")
        self.assertEqual(r1["fallback_model"], "gemini-4-argon")

        # 2. task-planner (medium) in offload_heavy_to_desktop -> gemini-desktop-app
        r2 = recommend_model(
            agent_type="task-planner",
            complexity="medium",
            budget_mode="offload_heavy_to_desktop",
            desktop_available=True,
        )["recommendation"]
        self.assertEqual(r2["model"], "gemini-desktop-app")

        # 3. code-reviewer with read_only=True even if file_count > 0 -> gemini-desktop-app
        r3 = recommend_model(
            agent_type="code-reviewer",
            complexity="high",
            file_count=5,
            read_only=True,
            budget_mode="hybrid_desktop",
            desktop_available=True,
        )["recommendation"]
        self.assertEqual(r3["model"], "gemini-desktop-app")

        # 4. builder NEVER offloads to desktop (remains on gemini-4-hydrogen)
        r4 = recommend_model(
            agent_type="builder",
            complexity="medium",
            budget_mode="offload_heavy_to_desktop",
            desktop_available=True,
            prefer_desktop=True,
        )["recommendation"]
        self.assertEqual(r4["model"], "gemini-4-hydrogen")

        # 5. desktop_available=False falls back cleanly to API fleet (Argon)
        r5 = recommend_model(
            agent_type="spec-engineer",
            complexity="high",
            budget_mode="hybrid_desktop",
            desktop_available=False,
        )["recommendation"]
        self.assertEqual(r5["model"], "gemini-4-argon")

        # 6. Rule 1 Security Guardrail NEVER bypassed by desktop modes
        r_sec = recommend_model(
            agent_type="spec-engineer",
            complexity="high",
            scope="auth jwt rbac audit",
            has_security_impact=True,
            budget_mode="offload_heavy_to_desktop",
            desktop_available=True,
            prefer_desktop=True,
        )["recommendation"]
        self.assertEqual(r_sec["model"], "gemini-4-carbon")
        self.assertEqual(r_sec["reasoning_effort"], "high")

        # 7. Rule 2 Circuit Breaker (retry_count >= 2) NEVER bypassed by desktop modes
        r_cb = recommend_model(
            agent_type="spec-engineer",
            complexity="high",
            budget_mode="offload_heavy_to_desktop",
            desktop_available=True,
            retry_count=2,
        )["recommendation"]
        self.assertEqual(r_cb["model"], "gemini-4-carbon")
        self.assertEqual(r_cb["circuit_breaker"]["status"], "tripped")

    def test_analytics_and_audit_report_include_desktop_jobs(self):
        """compute_model_analytics & generate_audit_report aggregate desktop_jobs metrics cleanly."""
        desktop_jobs = [
            {
                "job_id": "dsk-ana-1",
                "task_id": "TASK-26",
                "driver_name": "mock",
                "os_platform": "darwin",
                "status": "completed",
                "prompt_chars": 40_000,
                "output_chars": 8_000,
                "duration_ms": 120,
                "redaction_count": 1,
                "estimated_saved_usd": 0.04,
                "estimated_saved_vnd": 1016,
                "artifact_path": "docs/reports/desktop_worker/dsk-ana-1.md",
            }
        ]
        analytics = compute_model_analytics([], desktop_jobs=desktop_jobs)
        self.assertIn("gemini-desktop-app", analytics["models"])
        self.assertEqual(analytics["models"]["gemini-desktop-app"]["cost_usd"], 0.0)
        self.assertEqual(analytics["summary"]["desktop_jobs_count"], 1)
        self.assertEqual(analytics["summary"]["desktop_completed_count"], 1)
        self.assertEqual(analytics["summary"]["desktop_saved_usd"], 0.04)
        self.assertEqual(analytics["summary"]["desktop_saved_vnd"], 1016)

        md = generate_audit_report([], [], {"total": 0, "completed": 0}, format="markdown", desktop_jobs=desktop_jobs)
        self.assertIn("2b. Gemini Desktop Worker Offload Ledger", md)
        self.assertIn("dsk-ana-1", md)


class TestDesktopServerRESTSSEAndDashboard(unittest.TestCase):
    """5. Ephemeral Server SQLite desktop_jobs, REST Endpoints, Path Guard, SSE & Dashboard."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "desktop_server_test.db")
        cls.env_patcher = mock.patch.dict(
            os.environ,
            {
                "ORCHESTRATOR_WORKSPACE": cls.temp_dir.name,
                "MOCK_DELAY_MS": "20",
            },
            clear=False,
        )
        cls.env_patcher.start()

        cls.original_db = GLOBAL_STORE.db_path
        cls.original_mgr = GLOBAL_STORE._desktop_manager
        GLOBAL_STORE.db_path = cls.db_path
        GLOBAL_STORE._desktop_manager = None
        GLOBAL_STORE._init_db()
        GLOBAL_STORE.reset()

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), OrchestratorHandler)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2.0)
        GLOBAL_STORE.db_path = cls.original_db
        GLOBAL_STORE._desktop_manager = cls.original_mgr
        cls.env_patcher.stop()
        cls.temp_dir.cleanup()

    def setUp(self):
        GLOBAL_STORE.reset()

    def _request(self, method: str, path: str, payload: dict | None = None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                ct = resp.headers.get("Content-Type", "")
                raw = resp.read().decode("utf-8")
                body = json.loads(raw) if "application/json" in ct else raw
                return resp.status, ct, body
        except urllib.error.HTTPError as err:
            try:
                ct = err.headers.get("Content-Type", "")
                raw = err.read().decode("utf-8", errors="replace")
                body = json.loads(raw) if "application/json" in ct and raw else raw
                return err.code, ct, body
            finally:
                err.close()

    def test_get_models_and_desktop_status(self):
        """GET /api/models returns external_workers; GET /api/desktop/status probes mock and rejects invalid driver."""
        st_m, _, models_data = self._request("GET", "/api/models")
        self.assertEqual(st_m, 200)
        self.assertIn("gemini-desktop-app", models_data["external_workers"])
        self.assertEqual(len(models_data["models"]), 5)

        st_d, _, doc_data = self._request("GET", "/api/desktop/status?driver=mock")
        self.assertEqual(st_d, 200)
        self.assertEqual(doc_data["status"], "ok")
        self.assertTrue(doc_data["desktop"]["ready"])
        self.assertEqual(doc_data["desktop"]["driver_name"], "mock")

        st_bad, _, bad_data = self._request("GET", "/api/desktop/status?driver=unknown_drv")
        self.assertEqual(st_bad, 400)
        self.assertIn("error", bad_data)

    def test_dispatch_mock_sync_async_jobs_analytics_and_audit(self):
        """POST /api/desktop/dispatch (sync & async) persists SQLite desktop_jobs, scrubs secrets, and updates analytics/audit."""
        gh_tok = "ghp_" + "AbCdEf1234567890AbCdEf1234567890AbCd"
        st, _, sync_res = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "job_id": "dsk-e2e-sync-01",
                "task_id": "TASK-26",
                "driver": "mock",
                "async_mode": False,
                "prompt": f"[MOCK_CHROME] Synthesize architecture without leaking {gh_tok}",
            },
        )
        self.assertEqual(st, 200)
        self.assertEqual(sync_res["status"], "ok")
        job = sync_res["job"]
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["driver_name"], "mock")
        self.assertGreaterEqual(job["redaction_count"], 1)
        self.assertNotIn(gh_tok, job["prompt_preview"])
        self.assertTrue(job["clipboard_restored"])
        self.assertGreater(job["estimated_saved_usd"], 0.0)
        self.assertTrue(job["artifact_path"])
        self.assertTrue(Path(job["artifact_path"]).exists())

        # GET /api/desktop/jobs & GET /api/desktop/jobs/{id}
        st_j, _, jobs_res = self._request("GET", "/api/desktop/jobs")
        self.assertEqual(st_j, 200)
        self.assertEqual(jobs_res["summary"]["completed"], 1)
        self.assertEqual(jobs_res["jobs"][0]["job_id"], "dsk-e2e-sync-01")

        st_one, _, one_res = self._request("GET", "/api/desktop/jobs/dsk-e2e-sync-01")
        self.assertEqual(st_one, 200)
        self.assertEqual(one_res["job"]["job_id"], "dsk-e2e-sync-01")

        # GET /api/analytics/models & /api/audit/export include desktop offload
        st_a, _, ana_res = self._request("GET", "/api/analytics/models")
        self.assertEqual(st_a, 200)
        self.assertIn("gemini-desktop-app", ana_res["models"])
        self.assertEqual(ana_res["summary"]["desktop_jobs_count"], 1)

        st_exp_json, _, exp_json = self._request("GET", "/api/audit/export?format=json")
        self.assertEqual(st_exp_json, 200)
        self.assertEqual(exp_json["desktop_jobs_count"], 1)

        st_exp_md, _, exp_md = self._request("GET", "/api/audit/export?format=markdown")
        self.assertEqual(st_exp_md, 200)
        self.assertIn("2b. Gemini Desktop Worker Offload Ledger", exp_md)

        # Async dispatch returns 202 Accepted and completes in background
        st_as, _, async_res = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "job_id": "dsk-e2e-async-01",
                "driver": "mock",
                "async_mode": True,
                "prompt": "Async architecture synthesis",
            },
        )
        self.assertEqual(st_as, 202)
        self.assertEqual(async_res["status"], "queued")

        deadline = time.monotonic() + 5.0
        final_status = "queued"
        while time.monotonic() < deadline:
            _, _, poll_res = self._request("GET", "/api/desktop/jobs/dsk-e2e-async-01")
            final_status = poll_res["job"]["status"]
            if final_status == "completed":
                break
            time.sleep(0.05)
        self.assertEqual(final_status, "completed")

    def test_strict_secrets_and_path_traversal_and_validation_guards(self):
        """strict_secrets=True rejects secrets cleanly; path traversal output_path returns HTTP 400."""
        g_key = "AIza" + "SyB9876543210abcdefghijkLMNOPQRSTUV"
        st_sec, _, sec_res = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "job_id": "dsk-sec-reject-01",
                "driver": "mock",
                "strict_secrets": True,
                "async_mode": False,
                "prompt": f"Evaluate token {g_key}",
            },
        )
        self.assertEqual(st_sec, 200)
        self.assertEqual(sec_res["status"], "rejected_secrets")
        self.assertEqual(sec_res["job"]["status"], "rejected_secrets")
        self.assertGreaterEqual(sec_res["job"]["redaction_count"], 1)
        self.assertIsNone(sec_res["job"]["artifact_path"])

        # Path traversal output_path -> 400 Bad Request
        st_trav, _, trav_res = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "driver": "mock",
                "prompt": "Try traversal",
                "output_path": "../../evil.md",
            },
        )
        self.assertEqual(st_trav, 400)
        self.assertIn("error", trav_res)

        # Invalid job_id -> 400 Bad Request
        st_jid, _, _ = self._request(
            "POST",
            "/api/desktop/dispatch",
            {"job_id": "../bad", "driver": "mock", "prompt": "hi"},
        )
        self.assertEqual(st_jid, 400)

        # Empty prompt -> 400 Bad Request
        st_empty, _, _ = self._request(
            "POST",
            "/api/desktop/dispatch",
            {"driver": "mock", "prompt": "   "},
        )
        self.assertEqual(st_empty, 400)

    def test_desktop_http_app_path_csrf_cors_and_loopback_guards(self):
        """HTTP /api/desktop/* enforces app_path disable/allowlist, JSON Content-Type CSRF guard, CORS, and loopback/token checks."""
        # 1. Client-supplied app_path is rejected with 403 by default on dispatch and status
        st_app_post, _, err_app_post = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "driver": "mock",
                "prompt": "Try app_path override",
                "app_path": "/System/Applications/Utilities/Terminal.app",
            },
        )
        self.assertEqual(st_app_post, 403)
        self.assertIn("app_path", err_app_post.get("error", ""))

        st_app_get, _, _ = self._request(
            "GET",
            "/api/desktop/status?driver=mock&app_path=/System/Applications/Utilities/Terminal.app",
        )
        self.assertEqual(st_app_get, 403)

        # 2. Even with ORCHESTRATOR_ALLOW_CUSTOM_APP_PATH=1, unapproved app_path is rejected (400)
        with mock.patch.dict(os.environ, {"ORCHESTRATOR_ALLOW_CUSTOM_APP_PATH": "1"}, clear=False):
            st_bad_mac, _, _ = self._request(
                "POST",
                "/api/desktop/dispatch",
                {
                    "driver": "mock",
                    "target_os": "darwin",
                    "prompt": "Try Terminal",
                    "app_path": "/System/Applications/Utilities/Terminal.app",
                },
            )
            self.assertEqual(st_bad_mac, 400)

            st_bad_win, _, _ = self._request(
                "POST",
                "/api/desktop/dispatch",
                {
                    "driver": "mock",
                    "target_os": "win32",
                    "prompt": "Try cmd.exe",
                    "app_path": r"C:\Windows\System32\cmd.exe",
                },
            )
            self.assertEqual(st_bad_win, 400)

        # 3. CSRF Content-Type guard: text/plain and form-urlencoded POSTs rejected with 415
        for bad_ct in ("text/plain", "application/x-www-form-urlencoded", ""):
            conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
            headers = {"Content-Type": bad_ct} if bad_ct else {}
            conn.request(
                "POST",
                "/api/desktop/dispatch",
                body=json.dumps({"driver": "mock", "prompt": "CSRF"}).encode("utf-8"),
                headers=headers,
            )
            resp = conn.getresponse()
            resp.read()
            conn.close()
            self.assertEqual(resp.status, 415, f"Expected 415 for Content-Type={bad_ct!r}, got {resp.status}")

        conn_c = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn_c.request(
            "POST",
            "/api/desktop/cancel",
            body=json.dumps({"job_id": "dsk-1"}).encode("utf-8"),
            headers={"Content-Type": "text/plain"},
        )
        resp_c = conn_c.getresponse()
        resp_c.read()
        conn_c.close()
        self.assertEqual(resp_c.status, 415)

        # 4. CORS on /api/desktop/* omits '*' and only echoes loopback Origins; non-loopback Origin is 403
        conn_opt_evil = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn_opt_evil.request("OPTIONS", "/api/desktop/dispatch", headers={"Origin": "https://evil.example"})
        r_evil = conn_opt_evil.getresponse()
        r_evil.read()
        conn_opt_evil.close()
        self.assertIsNone(r_evil.getheader("Access-Control-Allow-Origin"))

        conn_opt_ok = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn_opt_ok.request("OPTIONS", "/api/desktop/dispatch", headers={"Origin": "http://localhost:8484"})
        r_ok = conn_opt_ok.getresponse()
        r_ok.read()
        conn_opt_ok.close()
        self.assertEqual(r_ok.getheader("Access-Control-Allow-Origin"), "http://localhost:8484")

        conn_post_evil = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn_post_evil.request(
            "POST",
            "/api/desktop/dispatch",
            body=json.dumps({"driver": "mock", "prompt": "hi"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Origin": "https://evil.example"},
        )
        r_post_evil = conn_post_evil.getresponse()
        r_post_evil.read()
        conn_post_evil.close()
        self.assertEqual(r_post_evil.status, 403)

        # 5. Content-Length > 2 MB rejected with 413 pre-read
        conn_big = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn_big.putrequest("POST", "/api/desktop/dispatch")
        conn_big.putheader("Content-Type", "application/json")
        conn_big.putheader("Content-Length", str(3 * 1024 * 1024))
        conn_big.endheaders()
        r_big = conn_big.getresponse()
        r_big.read()
        conn_big.close()
        self.assertEqual(r_big.status, 413)

        # 6. Non-loopback client IP requires matching ORCHESTRATOR_DESKTOP_TOKEN
        with mock.patch.dict(os.environ, {"ORCHESTRATOR_DESKTOP_TOKEN": "top-secret-desktop-tok"}, clear=False):
            with mock.patch.object(OrchestratorHandler, "address_string", return_value="10.0.0.50"):
                fake_handler = OrchestratorHandler.__new__(OrchestratorHandler)
                fake_handler.client_address = ("10.0.0.50", 54321)
                fake_handler.headers = {"Content-Type": "application/json"}
                fake_handler.path = "/api/desktop/dispatch"
                sent: list[tuple[int, dict]] = []
                fake_handler._send_json = lambda st, data: sent.append((int(st), data))
                self.assertFalse(fake_handler._check_desktop_access())
                self.assertEqual(sent[-1][0], 403)

                fake_handler.headers = {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer top-secret-desktop-tok",
                }
                self.assertTrue(fake_handler._check_desktop_access())

    def test_custom_output_path_and_symlink_escape_end_to_end(self):
        """Custom output_path='docs/reports/custom_arch_review.md' succeeds via HTTP; symlink escape is rejected."""
        st, _, res = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "job_id": "dsk-custom-out-01",
                "driver": "mock",
                "async_mode": False,
                "prompt": "Architecture review with custom output path",
                "output_path": "docs/reports/custom_arch_review.md",
            },
        )
        self.assertEqual(st, 200)
        self.assertEqual(res["status"], "ok")
        job = res["job"]
        self.assertEqual(job["status"], "completed")
        expected_file = (Path(self.temp_dir.name) / "docs" / "reports" / "custom_arch_review.md").resolve()
        self.assertTrue(expected_file.exists())
        self.assertEqual(Path(job["artifact_path"]).resolve(), expected_file)
        self.assertIn("job_id: dsk-custom-out-01", expected_file.read_text(encoding="utf-8"))

        # Symlink inside docs/reports pointing outside docs/reports must be rejected (HTTP 400)
        outside_target = Path(self.temp_dir.name) / "outside_secret.md"
        outside_target.write_text("do not overwrite", encoding="utf-8")
        sym_path = Path(self.temp_dir.name) / "docs" / "reports" / "escape_link.md"
        sym_path.parent.mkdir(parents=True, exist_ok=True)
        if sym_path.exists() or sym_path.is_symlink():
            sym_path.unlink()
        os.symlink(outside_target, sym_path)

        st_sym, _, _ = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "driver": "mock",
                "async_mode": False,
                "prompt": "Try symlink escape",
                "output_path": "docs/reports/escape_link.md",
            },
        )
        self.assertEqual(st_sym, 400)
        self.assertEqual(outside_target.read_text(encoding="utf-8"), "do not overwrite")

    def test_cancel_desktop_job_endpoints(self):
        """POST /api/desktop/cancel and /api/desktop/jobs/{id}/cancel cancel active jobs and return 404 for unknown."""
        with mock.patch.dict(os.environ, {"MOCK_DELAY_MS": "1500"}, clear=False):
            st, _, q_res = self._request(
                "POST",
                "/api/desktop/dispatch",
                {
                    "job_id": "dsk-cancel-http-01",
                    "driver": "mock",
                    "async_mode": True,
                    "prompt": "Slow task to cancel",
                },
            )
            self.assertEqual(st, 202)

            st_c, _, c_res = self._request("POST", "/api/desktop/cancel", {"job_id": "dsk-cancel-http-01"})
            self.assertEqual(st_c, 200)
            self.assertEqual(c_res["job"]["status"], "cancelled")

            # Wait briefly for worker loop to settle before restoring MOCK_DELAY_MS
            time.sleep(0.05)

        st_404, _, _ = self._request("POST", "/api/desktop/jobs/non-existent-job/cancel", {})
        self.assertEqual(st_404, 404)

    def test_sse_stream_emits_desktop_job_events(self):
        """GET /events streams desktop_job_queued, desktop_job_started, and desktop_job_completed."""
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/events")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)

        seen_events: list[str] = []

        def read_until_completed():
            cur_event = None
            while len(seen_events) < 10:
                raw = resp.fp.readline()
                if not raw:
                    break
                line = raw.decode("utf-8", errors="replace").strip()
                if line.startswith("event: "):
                    cur_event = line[len("event: "):]
                elif line.startswith("data: ") and cur_event:
                    seen_events.append(cur_event)
                    if cur_event == "desktop_job_completed":
                        break
                    cur_event = None

        reader = threading.Thread(target=read_until_completed, daemon=True)
        reader.start()
        time.sleep(0.05)

        st, _, _ = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "job_id": "dsk-sse-01",
                "driver": "mock",
                "async_mode": True,
                "prompt": "SSE event test",
            },
        )
        self.assertEqual(st, 202)
        reader.join(timeout=4.0)
        conn.close()

        self.assertIn("initial_state", seen_events)
        self.assertIn("desktop_job_queued", seen_events)
        self.assertIn("desktop_job_started", seen_events)
        self.assertIn("desktop_job_completed", seen_events)

    def test_router_recommend_and_dashboard_html_desktop_markers(self):
        """POST /api/router/recommend supports hybrid_desktop; GET / includes Desktop UI & preserves legacy markers."""
        st_r, _, rec_res = self._request(
            "POST",
            "/api/router/recommend",
            {
                "agent_type": "spec-engineer",
                "complexity": "high",
                "budget_mode": "hybrid_desktop",
                "desktop_available": True,
            },
        )
        self.assertEqual(st_r, 200)
        self.assertEqual(rec_res["recommendation"]["model"], "gemini-desktop-app")

        st_h, ct, html = self._request("GET", "/")
        self.assertEqual(st_h, 200)
        self.assertIn("text/html", ct)
        for marker in (
            "desktop-status-pill",
            "desktop-worker-modal",
            "metric-desktop-saved-usd",
            "hybrid_desktop",
            "offload_heavy_to_desktop",
            "desktop_job_queued",
            "desktop_job_completed",
            "openDesktopModal",
            "dispatchDesktopJob",
            "escapeHtml",
            # Legacy invariants
            "Gemini 4 Carbon",
            "Gemini 4 Hydrogen",
            "connectSSE",
            "XHigh",
        ):
            self.assertIn(marker, html, f"Dashboard HTML missing marker: {marker}")


class TestDesktopSDKAndCLISubprocess(unittest.TestCase):
    """6. Python SDK & CLI Subprocess End-to-End (client.py & desktop_worker.py)."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "desktop_cli_test.db")
        cls.env_patcher = mock.patch.dict(
            os.environ,
            {
                "ORCHESTRATOR_WORKSPACE": cls.temp_dir.name,
                "MOCK_DELAY_MS": "10",
            },
            clear=False,
        )
        cls.env_patcher.start()

        cls.original_db = GLOBAL_STORE.db_path
        cls.original_mgr = GLOBAL_STORE._desktop_manager
        GLOBAL_STORE.db_path = cls.db_path
        GLOBAL_STORE._desktop_manager = None
        GLOBAL_STORE._init_db()
        GLOBAL_STORE.reset()

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), OrchestratorHandler)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2.0)
        GLOBAL_STORE.db_path = cls.original_db
        GLOBAL_STORE._desktop_manager = cls.original_mgr
        cls.env_patcher.stop()
        cls.temp_dir.cleanup()

    def setUp(self):
        GLOBAL_STORE.reset()

    def test_sdk_desktop_methods(self):
        """Verify OrchestratorClient desktop_status, desktop_dispatch, desktop_jobs, desktop_cancel, recommend_model."""
        client = OrchestratorClient(base_url=self.base_url)

        doc = client.desktop_status(driver="mock")
        self.assertEqual(doc["status"], "ok")
        self.assertTrue(doc["desktop"]["ready"])

        disp = client.desktop_dispatch(
            prompt="SDK desktop dispatch check",
            task_id="TASK-26",
            driver="mock",
            async_mode=False,
        )
        self.assertEqual(disp["status"], "ok")
        job_id = disp["job"]["job_id"]
        self.assertEqual(disp["job"]["status"], "completed")

        jobs = client.desktop_jobs(job_id=job_id)
        self.assertEqual(jobs["status"], "ok")
        self.assertEqual(len(jobs["jobs"]), 1)

        rec = client.recommend_model(
            agent_type="spec-engineer",
            complexity="high",
            budget_mode="hybrid_desktop",
            desktop_available=True,
        )
        self.assertEqual(rec["recommendation"]["model"], "gemini-desktop-app")

        cancel_404 = client.desktop_cancel("missing-job-999")
        self.assertIn("error", cancel_404)

    def test_cli_subprocess_client_and_standalone_desktop_worker(self):
        """Verify client.py desktop-* / recommend CLI and standalone desktop_worker.py CLI via subprocess."""
        client_cli = str(ORCH_DIR / "client.py")
        worker_cli = str(ORCH_DIR / "desktop_worker.py")

        # 1. client.py desktop-doctor --driver mock --json
        p1 = subprocess.run(
            [sys.executable, client_cli, "--url", self.base_url, "desktop-doctor", "--driver", "mock", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        d1 = json.loads(p1.stdout)
        self.assertEqual(d1["status"], "ok")
        self.assertTrue(d1["desktop"]["ready"])

        # 2. client.py desktop-ask --driver mock --prompt "..." --json
        p2 = subprocess.run(
            [
                sys.executable,
                client_cli,
                "--url",
                self.base_url,
                "desktop-ask",
                "--driver",
                "mock",
                "--task",
                "TASK-26",
                "--prompt",
                "CLI desktop ask check",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        d2 = json.loads(p2.stdout)
        self.assertEqual(d2["status"], "ok")
        self.assertEqual(d2["job"]["status"], "completed")

        # 3. client.py desktop-jobs --json
        p3 = subprocess.run(
            [sys.executable, client_cli, "--url", self.base_url, "desktop-jobs", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        d3 = json.loads(p3.stdout)
        self.assertEqual(d3["summary"]["completed"], 1)

        # 4. client.py recommend --budget-mode hybrid_desktop --desktop-available --agent spec-engineer --complexity high --json
        p4 = subprocess.run(
            [
                sys.executable,
                client_cli,
                "--url",
                self.base_url,
                "recommend",
                "--budget-mode",
                "hybrid_desktop",
                "--desktop-available",
                "--agent",
                "spec-engineer",
                "--complexity",
                "high",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        d4 = json.loads(p4.stdout)
        self.assertEqual(d4["recommendation"]["model"], "gemini-desktop-app")

        # 5. standalone desktop_worker.py doctor --json
        p5 = subprocess.run(
            [sys.executable, worker_cli, "doctor", "--driver", "mock", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        d5 = json.loads(p5.stdout)
        self.assertTrue(d5["ready"])
        self.assertEqual(d5["driver_name"], "mock")

        # 6. standalone desktop_worker.py ask --driver mock --prompt "..." --json (cwd=temp_dir so zero repo pollution)
        p6 = subprocess.run(
            [sys.executable, worker_cli, "ask", "--driver", "mock", "--prompt", "Standalone ask", "--json"],
            cwd=self.temp_dir.name,
            capture_output=True,
            text=True,
            check=True,
        )
        d6 = json.loads(p6.stdout)
        self.assertEqual(d6["status"], "completed")
        self.assertTrue((Path(self.temp_dir.name) / d6["artifact_path"]).exists())


if __name__ == "__main__":
    unittest.main()
