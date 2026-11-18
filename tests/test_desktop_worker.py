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

import ctypes
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import plistlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any
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
            background=False,
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
        req = DesktopJobRequest(job_id=job_id, prompt="Test error restore", driver="macos_ax", background=False)
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

    def test_macos_driver_native_ax_bridge_and_copy_button_restore(self):
        """MacOSGeminiDriver uses _MacOSAXBridge when live PID exists and restores clipboard after copy-button."""
        drv = MacOSGeminiDriver()
        job_id = "dsk-macos-native-01"
        req = DesktopJobRequest(
            job_id=job_id,
            prompt="Summarize architecture",
            driver="macos_ax",
            timeout_sec=10,
            poll_interval_ms=50,
            restore_clipboard=True,
            new_chat=True,
            background=False,
        )
        framed = build_sentinel_prompt(job_id, req.prompt)
        copied_md = (
            f"{SentinelEnvelope.start_marker(job_id)}\n"
            "## Executive Summary\nNative AX Markdown.\n"
            f"{SentinelEnvelope.done_marker(job_id)}"
        )
        clipboard_state = {"bytes": b"USER_CLIPBOARD_ORIG"}
        pbcopy_history: list[bytes] = []

        class FakeNativeAX:
            def __init__(self) -> None:
                self.polls = 0
                self.copy_pressed = False

            def has_window(self, pid: int) -> bool:
                return pid == 4242

            def write_prompt_and_submit(self, pid: int, text: str) -> tuple[bool, bool]:
                return (pid == 4242 and text == framed, True)

            def poll_chat(self, pid: int) -> dict[str, Any]:
                self.polls += 1
                if self.polls == 1:
                    return {"has_window": False, "busy": False, "text": "", "has_copy_button": False}
                if self.polls == 2:
                    return {"has_window": True, "busy": True, "text": "", "has_copy_button": False}
                return {
                    "has_window": True,
                    "busy": False,
                    "text": copied_md,
                    "has_copy_button": True,
                }

            def press_copy_response(self, pid: int) -> bool:
                self.copy_pressed = True
                clipboard_state["bytes"] = copied_md.encode("utf-8")
                return True

        fake_ax = FakeNativeAX()

        def fake_pbpaste() -> bytes:
            return clipboard_state["bytes"]

        def fake_pbcopy(data: bytes) -> bool:
            pbcopy_history.append(data)
            clipboard_state["bytes"] = data
            return True

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
                     "app_path": "/Applications/Gemini.app",
                     "bundle_id": "com.google.GeminiMacOS",
                     "app_version": "1.144.4.1467",
                     "app_running": True,
                 },
             ), \
             mock.patch.object(MacOSGeminiDriver, "_check_orca", return_value=None), \
             mock.patch.object(MacOSGeminiDriver, "_find_running_pid", return_value=4242), \
             mock.patch.object(dw._MacOSAXBridge, "get_instance", return_value=fake_ax), \
             mock.patch.object(MacOSGeminiDriver, "_pbpaste_bytes", side_effect=fake_pbpaste), \
             mock.patch.object(MacOSGeminiDriver, "_pbcopy_bytes", side_effect=fake_pbcopy), \
             mock.patch.object(MacOSGeminiDriver, "_run_osascript", return_value="ok"), \
             mock.patch("desktop_worker.subprocess.run") as mock_sub_run, \
             mock.patch("desktop_worker.time.sleep", return_value=None), \
             mock.patch("desktop_worker.time.monotonic", side_effect=fake_monotonic):

            mock_sub_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            raw_text, meta = drv.execute_prompt(framed, job_id, req, threading.Event())

        self.assertTrue(fake_ax.copy_pressed)
        self.assertEqual(raw_text, copied_md)
        self.assertTrue(meta["clipboard_restored"])
        self.assertEqual(clipboard_state["bytes"], b"USER_CLIPBOARD_ORIG")
        self.assertEqual(pbcopy_history[0], b"")
        self.assertEqual(pbcopy_history[-1], b"USER_CLIPBOARD_ORIG")

    def test_macos_ax_bridge_find_window_ensure_mode_and_folders_cgevent(self):
        """_MacOSAXBridge filters phantom AXApplication, toggles mode via AXSelected/AXPress, and binds Folders via non-blocking CGEvent."""
        with tempfile.TemporaryDirectory() as tmp_ws, tempfile.TemporaryDirectory() as other_ws:
            target_ws = os.path.realpath(tmp_ws)
            other_dir = os.path.realpath(other_ws)

            def _build_fake_bridge(nodes: dict[int, dict[str, Any]], on_cgevent_click=None):
                bridge = dw._MacOSAXBridge.__new__(dw._MacOSAXBridge)
                handles: dict[int, tuple[str, Any]] = {}
                next_id = [9000]
                press_calls: list[tuple[int, str]] = []
                mouse_posts: list[tuple[int, float, float]] = []
                key_posts: list[tuple[int, int, bool]] = []
                event_meta: dict[int, dict[str, Any]] = {}

                def alloc(kind: str, val: Any) -> int:
                    next_id[0] += 1
                    hid = next_id[0]
                    handles[hid] = (kind, val)
                    return hid

                attr_names = (
                    "AXWindows",
                    "AXChildren",
                    "AXRole",
                    "AXSubrole",
                    "AXIdentifier",
                    "AXDescription",
                    "AXTitle",
                    "AXValue",
                    "AXFocused",
                    "AXEnabled",
                    "AXSelected",
                    "AXPosition",
                    "AXSize",
                    "AXFrontmost",
                    "AXSheets",
                    "AXPress",
                )
                bridge._attrs = {name: alloc("attr", name) for name in attr_names}
                bridge._k_true = alloc("bool", True)

                class FakeCF:
                    def CFGetTypeID(self, ref: int) -> int:
                        kind, _ = handles.get(ref, ("", None))
                        return {"str": 1, "arr": 2, "bool": 3}.get(kind, 0)

                    def CFStringGetTypeID(self) -> int:
                        return 1

                    def CFArrayGetTypeID(self) -> int:
                        return 2

                    def CFBooleanGetTypeID(self) -> int:
                        return 3

                    def CFStringCreateWithCString(self, _alloc, raw_bytes: bytes, _enc: int) -> int:
                        return alloc("str", raw_bytes.decode("utf-8"))

                    def CFStringGetLength(self, ref: int) -> int:
                        _, val = handles[ref]
                        return len(val)

                    def CFStringGetMaximumSizeForEncoding(self, length: int, _enc: int) -> int:
                        return length * 4 + 1

                    def CFStringGetCString(self, ref: int, buf, max_bytes: int, _enc: int) -> bool:
                        _, val = handles[ref]
                        raw = val.encode("utf-8")[: max_bytes - 1]
                        buf[0 : len(raw) + 1] = raw + b"\x00"
                        return True

                    def CFBooleanGetValue(self, ref: int) -> bool:
                        _, val = handles[ref]
                        return bool(val)

                    def CFArrayGetCount(self, ref: int) -> int:
                        _, val = handles[ref]
                        return len(val)

                    def CFArrayGetValueAtIndex(self, ref: int, idx: int) -> int:
                        _, val = handles[ref]
                        return int(val[idx])

                    def CFRetain(self, ref: int) -> int:
                        return ref

                    def CFRelease(self, _ref: int) -> None:
                        return None

                class FakeAX:
                    def AXUIElementCreateApplication(self, _pid: int) -> int:
                        return 100

                    def AXUIElementSetMessagingTimeout(self, _app_el: int, _timeout: float) -> int:
                        return 0

                    def AXUIElementCopyAttributeValue(self, el: int, attr_ref: int, out_ref) -> int:
                        _, attr_name = handles[attr_ref]
                        node = nodes.get(el, {})
                        if attr_name not in node:
                            return -25212
                        val = node[attr_name]
                        if isinstance(val, bool):
                            out_ref._obj.value = alloc("bool", val)
                        elif isinstance(val, str):
                            out_ref._obj.value = alloc("str", val)
                        elif isinstance(val, list):
                            out_ref._obj.value = alloc("arr", val)
                        elif isinstance(val, tuple) and len(val) == 2:
                            out_ref._obj.value = alloc(
                                "pos" if attr_name == "AXPosition" else "size", val
                            )
                        else:
                            return -25212
                        return 0

                    def AXUIElementSetAttributeValue(self, el: int, attr_ref: int, val_ref: int) -> int:
                        _, attr_name = handles[attr_ref]
                        if attr_name == "AXFrontmost":
                            return 0
                        kind, val = handles.get(val_ref, ("", None))
                        if el in nodes and kind in ("str", "bool"):
                            nodes[el][attr_name] = val
                        return 0

                    def AXUIElementPerformAction(self, el: int, action_ref: int) -> int:
                        _, act_name = handles[action_ref]
                        press_calls.append((el, act_name))
                        node = nodes.get(el, {})
                        cb = node.get("_on_press")
                        if callable(cb):
                            cb(node)
                        return 0

                    def AXValueGetValue(self, ref: int, val_type: int, out_struct) -> bool:
                        kind, val = handles.get(ref, ("", None))
                        if val_type == 1 and kind == "pos":
                            out_struct._obj.x = float(val[0])
                            out_struct._obj.y = float(val[1])
                            return True
                        if val_type == 2 and kind == "size":
                            out_struct._obj.width = float(val[0])
                            out_struct._obj.height = float(val[1])
                            return True
                        return False

                class FakeCG:
                    def CGEventCreateMouseEvent(self, _src, ev_type: int, pt, _btn: int) -> int:
                        ev_id = alloc("mouse", (ev_type, float(pt.x), float(pt.y)))
                        event_meta[ev_id] = {"kind": "mouse", "type": ev_type, "x": float(pt.x), "y": float(pt.y)}
                        return ev_id

                    def CGEventCreateKeyboardEvent(self, _src, keycode: int, key_down: bool) -> int:
                        ev_id = alloc("key", (int(keycode), bool(key_down)))
                        event_meta[ev_id] = {"kind": "key", "keycode": int(keycode), "down": bool(key_down), "flags": 0}
                        return ev_id

                    def CGEventSetFlags(self, ev_id: int, flags: int) -> None:
                        if ev_id in event_meta:
                            event_meta[ev_id]["flags"] = int(flags)

                    def CGEventPost(self, _tap: int, ev_id: int) -> None:
                        meta = event_meta.get(ev_id)
                        if not meta:
                            return
                        if meta["kind"] == "mouse":
                            mouse_posts.append((meta["type"], meta["x"], meta["y"]))
                            if meta["type"] == dw._MacOSAXBridge._K_CG_EVENT_LEFT_MOUSE_UP and callable(on_cgevent_click):
                                on_cgevent_click(meta["x"], meta["y"])
                        elif meta["kind"] == "key" and meta["down"]:
                            key_posts.append((meta["keycode"], meta["flags"], meta["down"]))

                bridge.cf = FakeCF()
                bridge.ax = FakeAX()
                bridge.cg = FakeCG()
                return bridge, press_calls, mouse_posts, key_posts

            # 1. Phantom AXApplication element in AXWindows must be ignored; AXWindow returned
            nodes_phantom = {
                100: {"AXWindows": [200, 201]},
                200: {"AXRole": "AXApplication", "AXSubrole": "AXStandardWindow", "AXTitle": "Phantom"},
                201: {"AXRole": "AXWindow", "AXSubrole": "AXStandardWindow", "AXTitle": "Gemini"},
            }
            br_ph, _, _, _ = _build_fake_bridge(nodes_phantom)
            self.assertEqual(br_ph._find_window(100), 201)

            nodes_only_phantom = {
                100: {"AXWindows": [200]},
                200: {"AXRole": "AXApplication", "AXSubrole": "AXStandardWindow", "AXTitle": "Phantom"},
            }
            br_none, _, _, _ = _build_fake_bridge(nodes_only_phantom)
            self.assertIsNone(br_none._find_window(100))

            # 2. _ensure_mode("task"): presses chat-input-mode-assign when AXSelected=False; skips when True
            def _activate_task(node):
                node["AXSelected"] = True
                nodes_mode[302]["AXDescription"] = "Assign a task"

            nodes_mode = {
                100: {"AXWindows": [201]},
                201: {"AXRole": "AXWindow", "AXSubrole": "AXStandardWindow", "AXChildren": [301, 302]},
                301: {
                    "AXRole": "AXButton",
                    "AXIdentifier": "chat-input-mode-assign",
                    "AXDescription": "Task",
                    "AXSelected": False,
                    "_on_press": _activate_task,
                },
                302: {"AXRole": "AXTextArea", "AXDescription": "Ask Gemini", "AXValue": ""},
            }
            br_mode, press_calls_mode, _, key_posts_mode = _build_fake_bridge(nodes_mode)
            with mock.patch("desktop_worker.time.sleep", return_value=None):
                self.assertTrue(br_mode._ensure_mode(4242, 201, "task"))
            self.assertEqual(press_calls_mode, [(301, "AXPress")])
            self.assertEqual(key_posts_mode, [])

            # When already AXSelected=True, _ensure_mode skips AXPress completely
            press_calls_mode.clear()
            with mock.patch("desktop_worker.time.sleep", return_value=None):
                self.assertTrue(br_mode._ensure_mode(4242, 201, "task"))
            self.assertEqual(press_calls_mode, [])

            # 3a. _attach_workspace_folder: non-blocking CGEvent on Folders -> matching AXMenuItem
            menu_open = {"active": False, "selected_item": None}

            def _on_click_match(x: float, y: float) -> None:
                # Folders button center is (100+40/2, 200+20/2) = (120.0, 210.0)
                if abs(x - 120.0) < 5.0 and abs(y - 210.0) < 5.0:
                    menu_open["active"] = True
                    nodes_attach[201]["AXChildren"] = [401, 500]
                # Matching AXMenuItem center is (120+80/2, 250+20/2) = (160.0, 260.0)
                elif abs(x - 160.0) < 5.0 and abs(y - 260.0) < 5.0:
                    menu_open["selected_item"] = 501

            nodes_attach = {
                100: {"AXWindows": [201]},
                201: {"AXRole": "AXWindow", "AXSubrole": "AXStandardWindow", "AXChildren": [401]},
                401: {
                    "AXRole": "AXButton",
                    "AXDescription": "Folders",
                    "AXTitle": "Folders",
                    "AXPosition": (100.0, 200.0),
                    "AXSize": (40.0, 20.0),
                },
                500: {"AXRole": "AXMenu", "AXChildren": [501, 502]},
                501: {
                    "AXRole": "AXMenuItem",
                    "AXTitle": target_ws,
                    "AXPosition": (120.0, 250.0),
                    "AXSize": (80.0, 20.0),
                },
                502: {
                    "AXRole": "AXMenuItem",
                    "AXIdentifier": "performAction",
                    "AXTitle": "Add new folder…",
                    "AXPosition": (120.0, 280.0),
                    "AXSize": (80.0, 20.0),
                },
            }
            br_attach, press_calls_attach, mouse_posts_attach, _ = _build_fake_bridge(
                nodes_attach, on_cgevent_click=_on_click_match
            )
            with mock.patch("desktop_worker.time.sleep", return_value=None):
                attached = br_attach._attach_workspace_folder(4242, 201, target_ws, restore_clipboard=True)
            self.assertTrue(attached)
            self.assertTrue(menu_open["active"])
            self.assertEqual(menu_open["selected_item"], 501)
            # CRITICAL: Folders button (401) must NEVER receive synchronous AXPress
            self.assertNotIn((401, "AXPress"), press_calls_attach)
            self.assertTrue(any(abs(x - 120.0) < 1.0 and abs(y - 210.0) < 1.0 for _, x, y in mouse_posts_attach))

            # 3a-ii. Scroll-container wrapper AXMenuItem (ConnectedFolderScrollMenuItem) must be skipped
            # so the leaf folder AXMenuItem (501) is clicked instead of the container (550).
            container_selected = {"target": None}

            def _on_click_scroll(x: float, y: float) -> None:
                if abs(x - 120.0) < 5.0 and abs(y - 210.0) < 5.0:
                    nodes_scroll[201]["AXChildren"] = [401, 500]
                elif abs(x - 160.0) < 5.0 and abs(y - 245.0) < 5.0:
                    container_selected["target"] = 501
                elif abs(x - 160.0) < 5.0 and abs(y - 265.0) < 5.0:
                    container_selected["target"] = 550  # container midpoint -> wrong sibling!

            nodes_scroll = {
                100: {"AXWindows": [201]},
                201: {"AXRole": "AXWindow", "AXSubrole": "AXStandardWindow", "AXChildren": [401]},
                401: {
                    "AXRole": "AXButton",
                    "AXDescription": "Folders",
                    "AXTitle": "Folders",
                    "AXPosition": (100.0, 200.0),
                    "AXSize": (40.0, 20.0),
                },
                500: {"AXRole": "AXMenu", "AXChildren": [550, 502]},
                550: {
                    "AXRole": "AXMenuItem",
                    "AXChildren": [551],
                    "AXPosition": (120.0, 235.0),
                    "AXSize": (80.0, 60.0),
                },
                551: {
                    "AXRole": "AXScrollArea",
                    "AXChildren": [501, 503],
                },
                501: {
                    "AXRole": "AXMenuItem",
                    "AXTitle": "target_ws",
                    "AXValue": target_ws,
                    "AXPosition": (120.0, 235.0),
                    "AXSize": (80.0, 20.0),
                },
                503: {
                    "AXRole": "AXMenuItem",
                    "AXTitle": "other-repo",
                    "AXValue": "/tmp/other-repo",
                    "AXPosition": (120.0, 275.0),
                    "AXSize": (80.0, 20.0),
                },
                502: {
                    "AXRole": "AXMenuItem",
                    "AXIdentifier": "performAction",
                    "AXTitle": "Add new folder…",
                    "AXPosition": (120.0, 305.0),
                    "AXSize": (80.0, 20.0),
                },
            }
            br_scroll, _, _, _ = _build_fake_bridge(nodes_scroll, on_cgevent_click=_on_click_scroll)
            with mock.patch("desktop_worker.time.sleep", return_value=None):
                self.assertTrue(br_scroll._attach_workspace_folder(4242, 201, target_ws, restore_clipboard=True))
            self.assertEqual(container_selected["target"], 501)

            # 3b. _attach_workspace_folder: Add new folder… fallback when target_ws absent from popup
            add_new_clicked = {"hit": False}
            clip_state = {"bytes": b"ORIG_CLIP_SAFE"}
            pbcopy_seq: list[bytes] = []

            def _on_click_fallback(x: float, y: float) -> None:
                if abs(x - 120.0) < 5.0 and abs(y - 210.0) < 5.0:
                    nodes_fb[201]["AXChildren"] = [401, 500]
                elif abs(x - 160.0) < 5.0 and abs(y - 290.0) < 5.0:
                    add_new_clicked["hit"] = True
                    nodes_fb[201]["AXSheets"] = [600]

            nodes_fb = {
                100: {"AXWindows": [201]},
                201: {"AXRole": "AXWindow", "AXSubrole": "AXStandardWindow", "AXChildren": [401], "AXSheets": []},
                401: {
                    "AXRole": "AXButton",
                    "AXDescription": "Folders",
                    "AXPosition": (100.0, 200.0),
                    "AXSize": (40.0, 20.0),
                },
                500: {"AXRole": "AXMenu", "AXChildren": [501, 502]},
                501: {
                    "AXRole": "AXMenuItem",
                    "AXTitle": other_dir,
                    "AXPosition": (120.0, 250.0),
                    "AXSize": (80.0, 20.0),
                },
                502: {
                    "AXRole": "AXMenuItem",
                    "AXIdentifier": "performAction",
                    "AXTitle": "Add new folder…",
                    "AXPosition": (120.0, 280.0),
                    "AXSize": (80.0, 20.0),
                },
                600: {"AXRole": "AXSheet", "AXChildren": []},
            }
            br_fb, press_calls_fb, _, key_posts_fb = _build_fake_bridge(
                nodes_fb, on_cgevent_click=_on_click_fallback
            )

            def _fake_fb_pbpaste() -> bytes:
                return clip_state["bytes"]

            def _fake_fb_pbcopy(data: bytes) -> bool:
                pbcopy_seq.append(data)
                clip_state["bytes"] = data
                return True

            with mock.patch.object(br_fb, "_pbpaste_bytes", side_effect=_fake_fb_pbpaste), \
                 mock.patch.object(br_fb, "_pbcopy_bytes", side_effect=_fake_fb_pbcopy), \
                 mock.patch("desktop_worker.time.sleep", return_value=None):
                fb_ok = br_fb._attach_workspace_folder(4242, 201, target_ws, restore_clipboard=True, background=False)
            self.assertTrue(fb_ok)
            self.assertTrue(add_new_clicked["hit"])
            self.assertNotIn((401, "AXPress"), press_calls_fb)
            # Cmd+Shift+G, Cmd+V, Return, Return
            cmd_shift = dw._MacOSAXBridge._K_CG_EVENT_FLAG_COMMAND | dw._MacOSAXBridge._K_CG_EVENT_FLAG_SHIFT
            self.assertIn((dw._MacOSAXBridge._KVK_ANSI_G, cmd_shift, True), key_posts_fb)
            self.assertIn((dw._MacOSAXBridge._KVK_ANSI_V, dw._MacOSAXBridge._K_CG_EVENT_FLAG_COMMAND, True), key_posts_fb)
            self.assertGreaterEqual(
                sum(1 for kc, _, _ in key_posts_fb if kc == dw._MacOSAXBridge._KVK_RETURN),
                2,
            )
            self.assertEqual(pbcopy_seq[0], target_ws.encode("utf-8"))
            self.assertEqual(clip_state["bytes"], b"ORIG_CLIP_SAFE")

            # 4. MacOSGeminiDriver._execute_via_native_ax sets workspace_attached=True when attach succeeds
            drv = MacOSGeminiDriver()
            job_id = "dsk-task-ws-01"
            req = DesktopJobRequest(
                job_id=job_id,
                prompt="Inspect workspace",
                driver="macos_ax",
                mode="task",
                workspace_path=target_ws,
                timeout_sec=10,
                poll_interval_ms=50,
                background=False,
            )
            framed = build_sentinel_prompt(job_id, req.prompt, mode="task", workspace_path=target_ws)
            done_text = (
                f"{SentinelEnvelope.start_marker(job_id)}\n"
                "## Executive Summary\nWorkspace analyzed.\n"
                f"{SentinelEnvelope.done_marker(job_id)}"
            )

            class FakeTaskAX:
                def __init__(self) -> None:
                    self.mode_called: str | None = None
                    self.attached_ws: str | None = None

                def has_window(self, pid: int) -> bool:
                    return True

                def ensure_mode(self, pid: int, mode: str) -> bool:
                    self.mode_called = mode
                    return True

                def attach_workspace_folder(self, pid: int, ws: str, restore_clipboard: bool = True) -> bool:
                    self.attached_ws = ws
                    return True

                def write_prompt_and_submit(self, pid: int, text: str) -> tuple[bool, bool]:
                    return True, True

                def poll_chat(self, pid: int) -> dict[str, Any]:
                    return {"has_window": True, "busy": False, "text": done_text, "has_copy_button": False}

            fake_task_ax = FakeTaskAX()
            tick = [0.0]

            def _fake_mono() -> float:
                tick[0] += 0.6
                return tick[0]

            with mock.patch.object(MacOSGeminiDriver, "_check_screen_locked", return_value="unlocked"), \
                 mock.patch.object(MacOSGeminiDriver, "_check_accessibility", return_value="granted"), \
                 mock.patch.object(
                     drv,
                     "discover_app",
                     return_value={
                         "app_detected": True,
                         "app_name": "Gemini",
                         "app_path": "/Applications/Gemini.app",
                         "bundle_id": "com.google.GeminiMacOS",
                         "app_version": "2.0",
                         "app_running": True,
                     },
                 ), \
                 mock.patch.object(MacOSGeminiDriver, "_check_orca", return_value=None), \
                 mock.patch.object(MacOSGeminiDriver, "_find_running_pid", return_value=4242), \
                 mock.patch.object(dw._MacOSAXBridge, "get_instance", return_value=fake_task_ax), \
                 mock.patch.object(MacOSGeminiDriver, "_pbpaste_bytes", return_value=b"ORIG"), \
                 mock.patch.object(MacOSGeminiDriver, "_pbcopy_bytes", return_value=True), \
                 mock.patch("desktop_worker.subprocess.run") as mock_sub, \
                 mock.patch("desktop_worker.time.sleep", return_value=None), \
                 mock.patch("desktop_worker.time.monotonic", side_effect=_fake_mono):
                mock_sub.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
                _, meta = drv.execute_prompt(framed, job_id, req, threading.Event())

            self.assertEqual(fake_task_ax.mode_called, "task")
            self.assertEqual(fake_task_ax.attached_ws, target_ws)
            self.assertEqual(meta["mode"], "task")
            self.assertEqual(meta["workspace_path"], target_ws)
            self.assertTrue(meta["workspace_attached"])

    def test_macos_confirmation_card_fast_fail(self):
        """Confirmation/elicitation AX cards (ActionCardRemyConfirmationCard / AgentWaitingForInputRow) trigger immediate fast-fail."""
        # 1. Verify _MacOSAXBridge.poll_chat detects both card identifiers
        for card_ident in ("ActionCardRemyConfirmationCard", "AgentWaitingForInputRow"):
            bridge = dw._MacOSAXBridge.__new__(dw._MacOSAXBridge)
            handles: dict[int, tuple[str, Any]] = {}
            next_id = [8000]

            def _alloc(kind: str, val: Any) -> int:
                next_id[0] += 1
                handles[next_id[0]] = (kind, val)
                return next_id[0]

            bridge._attrs = {
                name: _alloc("attr", name)
                for name in ("AXWindows", "AXChildren", "AXRole", "AXSubrole", "AXIdentifier", "AXDescription", "AXTitle", "AXValue")
            }
            bridge._k_true = _alloc("bool", True)
            nodes = {
                100: {"AXWindows": [201]},
                201: {"AXRole": "AXWindow", "AXSubrole": "AXStandardWindow", "AXChildren": [301]},
                301: {"AXRole": "AXGroup", "AXIdentifier": f"prefix_{card_ident}_suffix", "AXChildren": []},
            }

            class _CF:
                def CFGetTypeID(self, ref: int) -> int:
                    return {"str": 1, "arr": 2}.get(handles.get(ref, ("", None))[0], 0)

                def CFStringGetTypeID(self) -> int:
                    return 1

                def CFArrayGetTypeID(self) -> int:
                    return 2

                def CFBooleanGetTypeID(self) -> int:
                    return 3

                def CFStringGetLength(self, ref: int) -> int:
                    return len(handles[ref][1])

                def CFStringGetMaximumSizeForEncoding(self, length: int, _enc: int) -> int:
                    return length * 4 + 1

                def CFStringGetCString(self, ref: int, buf, max_bytes: int, _enc: int) -> bool:
                    raw = handles[ref][1].encode("utf-8")[: max_bytes - 1]
                    buf[0 : len(raw) + 1] = raw + b"\x00"
                    return True

                def CFArrayGetCount(self, ref: int) -> int:
                    return len(handles[ref][1])

                def CFArrayGetValueAtIndex(self, ref: int, idx: int) -> int:
                    return int(handles[ref][1][idx])

                def CFRetain(self, ref: int) -> int:
                    return ref

                def CFRelease(self, _ref: int) -> None:
                    return None

            class _AX:
                def AXUIElementCreateApplication(self, _pid: int) -> int:
                    return 100

                def AXUIElementSetMessagingTimeout(self, _app: int, _t: float) -> int:
                    return 0

                def AXUIElementCopyAttributeValue(self, el: int, attr_ref: int, out_ref) -> int:
                    attr_name = handles[attr_ref][1]
                    node = nodes.get(el, {})
                    if attr_name not in node:
                        return -25212
                    val = node[attr_name]
                    out_ref._obj.value = _alloc("str" if isinstance(val, str) else "arr", val)
                    return 0

            bridge.cf = _CF()
            bridge.ax = _AX()
            bridge.cg = None
            polled = bridge.poll_chat(4242)
            self.assertTrue(polled["has_window"])
            self.assertEqual(polled["confirmation_card"], card_ident)

        # 1b. Verify poll_chat prefers AXDescription when SwiftUI strips sentinel tags in AXValue ('<<>>')
        nodes["dummy_unused"] = {}
        nodes.clear()
        nodes.update({
            100: {"AXWindows": [201]},
            201: {"AXRole": "AXWindow", "AXSubrole": "AXStandardWindow", "AXChildren": [301]},
            301: {
                "AXRole": "AXStaticText",
                "AXValue": "<<>>\nExecutive Summary\nAll good.\n<<>>",
                "AXDescription": (
                    "<<<AGY_DESKTOP_START:dsk-desc-01>>>\n"
                    "## Executive Summary\nAll good.\n"
                    "<<<AGY_DESKTOP_DONE:dsk-desc-01>>>"
                ),
            },
        })
        polled_desc = bridge.poll_chat(4242)
        self.assertTrue(SentinelEnvelope.has_complete_sentinel(polled_desc["text"], "dsk-desc-01"))

        # 1c. Verify poll_chat extracts Task-mode AXButton ('copy-button-copy-button') AXDescription verbatim
        nodes.clear()
        nodes.update({
            100: {"AXWindows": [201]},
            201: {"AXRole": "AXWindow", "AXSubrole": "AXStandardWindow", "AXChildren": [301, 302, 303, 304]},
            301: {
                "AXRole": "AXHeading",
                "AXIdentifier": "userMessage.expandButton-userMessage.expandButton",
                "AXDescription": "[AGY_DESKTOP_WORKER_TASK job_id=dsk-task-btn-01]\nPrompt text",
            },
            302: {
                "AXRole": "AXButton",
                "AXDescription": "Analyzed repository structure.",
                "AXValue": "Collapsed",
            },
            303: {
                "AXRole": "AXButton",
                "AXIdentifier": "copy-button-copy-button",
                "AXValue": "<<>>\nExecutive Summary\nTask mode works.\n<<>>",
                "AXDescription": (
                    "<<<AGY_DESKTOP_START:dsk-task-btn-01>>>\n"
                    "## Executive Summary\nTask mode works.\n"
                    "<<<AGY_DESKTOP_DONE:dsk-task-btn-01>>>"
                ),
            },
            304: {
                "AXRole": "AXButton",
                "AXIdentifier": "copy-button",
                "AXDescription": "Copy response",
            },
        })
        polled_task_btn = bridge.poll_chat(4242)
        self.assertTrue(polled_task_btn["has_copy_button"])
        self.assertTrue(SentinelEnvelope.has_complete_sentinel(polled_task_btn["text"], "dsk-task-btn-01"))
        self.assertNotIn("Prompt text", polled_task_btn["text"])
        self.assertNotIn("Analyzed repository structure", polled_task_btn["text"])

        # 2. Verify MacOSGeminiDriver fast-fails on first poll without hanging until timeout_sec
        drv = MacOSGeminiDriver()
        req = DesktopJobRequest(
            job_id="dsk-confirm-fastfail",
            prompt="Run read-only check",
            driver="macos_ax",
            mode="task",
            timeout_sec=180,
            poll_interval_ms=50,
        )

        class ConfirmAX:
            def __init__(self) -> None:
                self.poll_calls = 0

            def has_window(self, _pid: int) -> bool:
                return True

            def ensure_mode(self, _pid: int, _mode: str) -> bool:
                return True

            def write_prompt_and_submit(self, _pid: int, _text: str) -> tuple[bool, bool]:
                return True, True

            def poll_chat(self, _pid: int) -> dict[str, Any]:
                self.poll_calls += 1
                return {
                    "has_window": True,
                    "busy": False,
                    "text": "",
                    "has_copy_button": False,
                    "confirmation_card": "ActionCardRemyConfirmationCard",
                }

        confirm_ax = ConfirmAX()
        with mock.patch.object(MacOSGeminiDriver, "_check_screen_locked", return_value="unlocked"), \
             mock.patch.object(MacOSGeminiDriver, "_check_accessibility", return_value="granted"), \
             mock.patch.object(
                 drv,
                 "discover_app",
                 return_value={
                     "app_detected": True,
                     "app_name": "Gemini",
                     "app_path": "/Applications/Gemini.app",
                     "bundle_id": "com.google.GeminiMacOS",
                     "app_version": "2.0",
                     "app_running": True,
                 },
             ), \
             mock.patch.object(MacOSGeminiDriver, "_check_orca", return_value=None), \
             mock.patch.object(MacOSGeminiDriver, "_find_running_pid", return_value=4242), \
             mock.patch.object(dw._MacOSAXBridge, "get_instance", return_value=confirm_ax), \
             mock.patch.object(MacOSGeminiDriver, "_pbpaste_bytes", return_value=b"ORIG"), \
             mock.patch.object(MacOSGeminiDriver, "_pbcopy_bytes", return_value=True), \
             mock.patch("desktop_worker.subprocess.run") as mock_sub, \
             mock.patch("desktop_worker.time.sleep", return_value=None):
            mock_sub.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
            with self.assertRaises(RuntimeError) as ctx:
                drv.execute_prompt(build_sentinel_prompt(req.job_id, req.prompt), req.job_id, req, threading.Event())

        self.assertEqual(confirm_ax.poll_calls, 1)
        self.assertIn("ActionCardRemyConfirmationCard", str(ctx.exception))
        self.assertIn("aborted instead of hanging until timeout", str(ctx.exception))

    def test_macos_background_mode_daemon_axpress_zero_clipboard_and_diag_log_tail(self):
        """Default background=True uses daemon AXPress (0 CGEvent), 0 clipboard touches, diagnostic.log tailing, and prev_pid restore."""
        with tempfile.TemporaryDirectory() as tmp_ws, tempfile.TemporaryDirectory() as tmp_logs, tempfile.TemporaryDirectory() as tmp_app:
            target_ws = os.path.realpath(tmp_ws)
            fake_app = Path(tmp_app) / "Gemini.app"
            (fake_app / "Contents").mkdir(parents=True)
            diag_log = Path(tmp_logs) / "diagnostic-2026-11-17.log"
            diag_log.write_text("2026-11-17T00:00:00Z boot\n", encoding="utf-8")

            # 1. _MacOSAXBridge._attach_workspace_folder(..., background=True) spawns daemon AXPress, 0 CGEvent mouse calls
            bridge = dw._MacOSAXBridge.__new__(dw._MacOSAXBridge)
            handles: dict[int, tuple[str, Any]] = {}
            next_id = [7000]
            axpress_threads: list[tuple[int, str, bool]] = []
            mouse_posts: list[Any] = []
            main_ident = threading.get_ident()

            def _alloc(kind: str, val: Any) -> int:
                next_id[0] += 1
                handles[next_id[0]] = (kind, val)
                return next_id[0]

            bridge._attrs = {
                name: _alloc("attr", name)
                for name in (
                    "AXWindows",
                    "AXChildren",
                    "AXRole",
                    "AXSubrole",
                    "AXIdentifier",
                    "AXDescription",
                    "AXTitle",
                    "AXValue",
                    "AXSelected",
                    "AXPress",
                    "AXCancel",
                )
            }
            bridge._k_true = _alloc("bool", True)

            nodes: dict[int, dict[str, Any]] = {
                100: {"AXWindows": [201]},
                201: {"AXRole": "AXWindow", "AXSubrole": "AXStandardWindow", "AXChildren": [401]},
                401: {"AXRole": "AXButton", "AXDescription": "Folders", "AXTitle": "Folders"},
                500: {"AXRole": "AXMenu", "AXChildren": [501, 502]},
                501: {"AXRole": "AXMenuItem", "AXTitle": target_ws},
                502: {"AXRole": "AXMenuItem", "AXIdentifier": "performAction", "AXTitle": "Add new folder…"},
            }

            class _BgCF:
                def CFGetTypeID(self, ref: int) -> int:
                    return {"str": 1, "arr": 2, "bool": 3}.get(handles.get(ref, ("", None))[0], 0)

                def CFStringGetTypeID(self) -> int:
                    return 1

                def CFArrayGetTypeID(self) -> int:
                    return 2

                def CFBooleanGetTypeID(self) -> int:
                    return 3

                def CFStringCreateWithCString(self, _a, raw_bytes: bytes, _e: int) -> int:
                    return _alloc("str", raw_bytes.decode("utf-8"))

                def CFStringGetLength(self, ref: int) -> int:
                    return len(handles[ref][1])

                def CFStringGetMaximumSizeForEncoding(self, length: int, _e: int) -> int:
                    return length * 4 + 1

                def CFStringGetCString(self, ref: int, buf, max_bytes: int, _e: int) -> bool:
                    raw = handles[ref][1].encode("utf-8")[: max_bytes - 1]
                    buf[0 : len(raw) + 1] = raw + b"\x00"
                    return True

                def CFBooleanGetValue(self, ref: int) -> bool:
                    return bool(handles[ref][1])

                def CFArrayGetCount(self, ref: int) -> int:
                    return len(handles[ref][1])

                def CFArrayGetValueAtIndex(self, ref: int, idx: int) -> int:
                    return int(handles[ref][1][idx])

                def CFRetain(self, ref: int) -> int:
                    return ref

                def CFRelease(self, _ref: int) -> None:
                    return None

            class _BgAX:
                def AXUIElementCreateApplication(self, _pid: int) -> int:
                    return 100

                def AXUIElementSetMessagingTimeout(self, _app: int, _t: float) -> int:
                    return 0

                def AXUIElementCopyAttributeValue(self, el: int, attr_ref: int, out_ref) -> int:
                    attr_name = handles[attr_ref][1]
                    node = nodes.get(el, {})
                    if attr_name not in node:
                        return -25212
                    val = node[attr_name]
                    kind = "bool" if isinstance(val, bool) else ("str" if isinstance(val, str) else "arr")
                    out_ref._obj.value = _alloc(kind, val)
                    return 0

                def AXUIElementPerformAction(self, el: int, action_ref: int) -> int:
                    act_name = handles[action_ref][1]
                    cur_t = threading.current_thread()
                    axpress_threads.append((el, act_name, cur_t.daemon and cur_t.ident != main_ident))
                    if el == 401 and act_name == "AXPress":
                        nodes[201]["AXChildren"] = [401, 500]
                    elif el == 501 and act_name == "AXPress":
                        nodes[201]["AXChildren"] = [401, 505]
                        nodes[505] = {"AXRole": "AXGroup", "AXIdentifier": "ConnectedFolderInputChip", "AXTitle": target_ws}
                    return 0

            class _BgCG:
                def CGEventCreateMouseEvent(self, *_a) -> int:
                    mouse_posts.append(_a)
                    return _alloc("mouse", _a)

                def CGEventPost(self, *_a) -> None:
                    mouse_posts.append(_a)

            bridge.cf = _BgCF()
            bridge.ax = _BgAX()
            bridge.cg = _BgCG()

            ok = bridge._attach_workspace_folder(4242, 201, target_ws, restore_clipboard=False, background=True)
            self.assertTrue(ok)
            self.assertEqual(mouse_posts, [])
            self.assertIn((401, "AXPress", True), axpress_threads)
            self.assertTrue(any(el == 501 and act == "AXPress" for el, act, _ in axpress_threads))

            # 2. Full MacOSGeminiDriver silent background flow: default background=True, diag log tail, 0 pbcopy/pbpaste, prev_pid restore
            drv = MacOSGeminiDriver()
            job_id = "dsk-bg-silent-01"
            req = DesktopJobRequest(
                job_id=job_id,
                prompt="Analyze silently",
                driver="macos_ax",
                mode="task",
                workspace_path=target_ws,
                timeout_sec=15,
            )
            self.assertTrue(req.background)
            framed = build_sentinel_prompt(job_id, req.prompt, mode="task", workspace_path=target_ws)
            expected_md = (
                f"{SentinelEnvelope.start_marker(job_id)}\n"
                "## Executive Summary\nSilent background extraction via AXStaticText.AXDescription.\n"
                f"{SentinelEnvelope.done_marker(job_id)}"
            )

            class SilentBGBridge:
                def __init__(self) -> None:
                    self.frontmost_calls: list[int] = []
                    self.phase = "dispatch"
                    self.wait_polls = 0
                    self.attached_bg: bool | None = None
                    self._window_visible = False

                def has_window(self, pid: int) -> bool:
                    return self._window_visible

                def _bring_frontmost(self, pid: int) -> None:
                    self.frontmost_calls.append(pid)
                    if pid == 4242:
                        self._window_visible = True

                def ensure_mode(self, pid: int, mode: str, background: bool = False) -> bool:
                    return background is True and mode == "task"

                def attach_workspace_folder(
                    self,
                    pid: int,
                    ws: str,
                    restore_clipboard: bool = True,
                    background: bool = False,
                ) -> bool:
                    self.attached_bg = background
                    return background is True and ws == target_ws

                def write_prompt_and_submit(self, pid: int, text: str) -> tuple[bool, bool]:
                    self.phase = "waiting"
                    self._window_visible = False
                    return (text == framed, True)

                def poll_chat(self, pid: int) -> dict[str, Any]:
                    if self.phase == "waiting":
                        self.wait_polls += 1
                        if self.wait_polls == 1:
                            with diag_log.open("a", encoding="utf-8") as fh:
                                fh.write("addStreamingConversation\n")
                        elif self.wait_polls >= 2:
                            with diag_log.open("a", encoding="utf-8") as fh:
                                fh.write("isMessageTreeCompleted=true\nremoveStreamingConversation()\n")
                            self.phase = "extract"
                        return {"has_window": False, "busy": False, "text": "", "confirmation_card": None}
                    return {
                        "has_window": self._window_visible,
                        "busy": False,
                        "text": expected_md if self._window_visible else "",
                        "confirmation_card": None,
                    }

            silent_ax = SilentBGBridge()
            with mock.patch.dict(os.environ, {"GEMINI_DIAGNOSTIC_LOG_DIR": tmp_logs}, clear=False), \
                 mock.patch.object(MacOSGeminiDriver, "_check_screen_locked", return_value="unlocked"), \
                 mock.patch.object(MacOSGeminiDriver, "_check_accessibility", return_value="granted"), \
                 mock.patch.object(
                     drv,
                     "discover_app",
                     return_value={
                         "app_detected": True,
                         "app_name": "Gemini",
                         "app_path": str(fake_app),
                         "bundle_id": "com.google.GeminiMacOS",
                         "app_version": "2.0",
                         "app_running": True,
                         "is_pwa": False,
                     },
                 ), \
                 mock.patch.object(MacOSGeminiDriver, "_check_orca", return_value=None), \
                 mock.patch.object(MacOSGeminiDriver, "_find_running_pid", return_value=4242), \
                 mock.patch.object(MacOSGeminiDriver, "_get_frontmost_pid", return_value=9999), \
                 mock.patch.object(dw._MacOSAXBridge, "get_instance", return_value=silent_ax), \
                 mock.patch.object(MacOSGeminiDriver, "_pbpaste_bytes") as mock_pbpaste, \
                 mock.patch.object(MacOSGeminiDriver, "_pbcopy_bytes") as mock_pbcopy, \
                 mock.patch("desktop_worker.subprocess.run") as mock_sub_run, \
                 mock.patch("desktop_worker.time.sleep", return_value=None):
                raw_text, meta = drv.execute_prompt(framed, job_id, req, threading.Event())

            mock_pbpaste.assert_not_called()
            mock_pbcopy.assert_not_called()
            mock_sub_run.assert_not_called()
            self.assertTrue(silent_ax.attached_bg)
            self.assertEqual(raw_text, expected_md)
            self.assertTrue(meta["background"])
            self.assertFalse(meta["clipboard_touched"])
            self.assertTrue(meta["clipboard_restored"])
            self.assertTrue(meta["workspace_attached"])
            # prev_pid (9999) restored after dispatch and extraction
            self.assertIn(9999, silent_ax.frontmost_calls)
            self.assertEqual(silent_ax.frontmost_calls[-1], 9999)

    def test_macos_background_mode_unbookmarked_workspace_raises_clear_error(self):
        """Unbookmarked workspace in background=True cancels menu, avoids NSOpenPanel, and raises clear --allow-foreground error."""
        with tempfile.TemporaryDirectory() as tmp_ws, tempfile.TemporaryDirectory() as other_ws:
            target_ws = os.path.realpath(tmp_ws)
            other_dir = os.path.realpath(other_ws)

            bridge = dw._MacOSAXBridge.__new__(dw._MacOSAXBridge)
            handles: dict[int, tuple[str, Any]] = {}
            next_id = [6000]
            actions_called: list[tuple[int, str]] = []
            key_posts: list[Any] = []

            def _alloc(kind: str, val: Any) -> int:
                next_id[0] += 1
                handles[next_id[0]] = (kind, val)
                return next_id[0]

            bridge._attrs = {
                name: _alloc("attr", name)
                for name in ("AXWindows", "AXChildren", "AXRole", "AXSubrole", "AXIdentifier", "AXDescription", "AXTitle", "AXValue", "AXPress", "AXCancel")
            }
            bridge._k_true = _alloc("bool", True)

            nodes: dict[int, dict[str, Any]] = {
                100: {"AXWindows": [201]},
                201: {"AXRole": "AXWindow", "AXSubrole": "AXStandardWindow", "AXChildren": [401]},
                401: {"AXRole": "AXButton", "AXDescription": "Folders", "AXTitle": "Folders"},
                500: {"AXRole": "AXMenu", "AXChildren": [501, 502]},
                501: {"AXRole": "AXMenuItem", "AXTitle": other_dir},
                502: {"AXRole": "AXMenuItem", "AXIdentifier": "performAction", "AXTitle": "Add new folder…"},
            }

            class _CF:
                def CFGetTypeID(self, ref: int) -> int:
                    return {"str": 1, "arr": 2}.get(handles.get(ref, ("", None))[0], 0)

                def CFStringGetTypeID(self) -> int:
                    return 1

                def CFArrayGetTypeID(self) -> int:
                    return 2

                def CFBooleanGetTypeID(self) -> int:
                    return 3

                def CFStringCreateWithCString(self, _a, raw_bytes: bytes, _e: int) -> int:
                    return _alloc("str", raw_bytes.decode("utf-8"))

                def CFStringGetLength(self, ref: int) -> int:
                    return len(handles[ref][1])

                def CFStringGetMaximumSizeForEncoding(self, length: int, _e: int) -> int:
                    return length * 4 + 1

                def CFStringGetCString(self, ref: int, buf, max_bytes: int, _e: int) -> bool:
                    raw = handles[ref][1].encode("utf-8")[: max_bytes - 1]
                    buf[0 : len(raw) + 1] = raw + b"\x00"
                    return True

                def CFArrayGetCount(self, ref: int) -> int:
                    return len(handles[ref][1])

                def CFArrayGetValueAtIndex(self, ref: int, idx: int) -> int:
                    return int(handles[ref][1][idx])

                def CFRetain(self, ref: int) -> int:
                    return ref

                def CFRelease(self, _ref: int) -> None:
                    return None

            class _AX:
                def AXUIElementCreateApplication(self, _pid: int) -> int:
                    return 100

                def AXUIElementSetMessagingTimeout(self, _app: int, _t: float) -> int:
                    return 0

                def AXUIElementCopyAttributeValue(self, el: int, attr_ref: int, out_ref) -> int:
                    attr_name = handles[attr_ref][1]
                    node = nodes.get(el, {})
                    if attr_name not in node:
                        return -25212
                    val = node[attr_name]
                    out_ref._obj.value = _alloc("str" if isinstance(val, str) else "arr", val)
                    return 0

                def AXUIElementPerformAction(self, el: int, action_ref: int) -> int:
                    act_name = handles[action_ref][1]
                    actions_called.append((el, act_name))
                    if el == 401 and act_name == "AXPress":
                        nodes[201]["AXChildren"] = [401, 500]
                    return 0

            class _CG:
                def CGEventCreateKeyboardEvent(self, *_a) -> int:
                    key_posts.append(_a)
                    return 1

                def CGEventPost(self, *_a) -> None:
                    key_posts.append(_a)

            bridge.cf = _CF()
            bridge.ax = _AX()
            bridge.cg = _CG()

            with mock.patch("desktop_worker.time.sleep", return_value=None):
                with self.assertRaises(RuntimeError) as ctx:
                    bridge._attach_workspace_folder(4242, 201, target_ws, restore_clipboard=False, background=True)

            self.assertIn("--allow-foreground", str(ctx.exception))
            self.assertIn("not bookmarked", str(ctx.exception))
            self.assertIn((500, "AXCancel"), actions_called)
            self.assertNotIn((502, "AXPress"), actions_called)
            self.assertEqual(key_posts, [])

    def test_macos_extract_one_shot_background_open_g_fallback_and_post_done_fail_fast(self):
        """_extract_one_shot_background falls back to open -g -a if AXFrontmost leaves has_window=False, then restores prev_pid."""
        drv = MacOSGeminiDriver()
        job_id = "dsk-open-g-01"
        expected_md = (
            f"{SentinelEnvelope.start_marker(job_id)}\n"
            "## Executive Summary\nReopened via open -g -a.\n"
            f"{SentinelEnvelope.done_marker(job_id)}"
        )

        class _HiddenWindowBridge:
            def __init__(self) -> None:
                self.visible = False
                self.calls: list[str] = []

            def has_window(self, pid: int) -> bool:
                return self.visible

            def _bring_frontmost(self, pid: int) -> None:
                self.calls.append(f"bring:{pid}")

            def _activate_pid(self, pid: int) -> bool:
                self.calls.append(f"activate:{pid}")
                return True

            def poll_chat(self, pid: int) -> dict[str, Any]:
                if not self.visible:
                    return {"has_window": False, "busy": False, "text": "", "confirmation_card": None}
                return {"has_window": True, "busy": False, "text": expected_md, "confirmation_card": None}

        ax = _HiddenWindowBridge()
        sub_cmds: list[list[str]] = []

        def _fake_sub(cmd, **_kwargs):
            sub_cmds.append(list(cmd))
            ax.visible = True
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        with mock.patch.object(MacOSGeminiDriver, "_get_frontmost_pid", return_value=9999), \
             mock.patch("desktop_worker.subprocess.run", side_effect=_fake_sub) as mock_sub, \
             mock.patch("desktop_worker.time.sleep", return_value=None):
            res = drv._extract_one_shot_background(
                ax_bridge=ax,
                pid=4242,
                job_id=job_id,
                open_bin="/usr/bin/open",
                app_path="/Applications/Gemini.app",
            )

        self.assertTrue(mock_sub.called)
        self.assertEqual(sub_cmds[0], ["/usr/bin/open", "-g", "-a", "/Applications/Gemini.app"])
        self.assertTrue(res["has_window"])
        self.assertEqual(res["text"], expected_md)
        self.assertIn("bring:4242", ax.calls)
        self.assertEqual(ax.calls[-1], "activate:9999")

        # Post-done fail-fast guard: if saw_done fired and extraction repeatedly returns empty/hidden, do not hang until timeout
        with tempfile.TemporaryDirectory() as tmp_logs:
            (Path(tmp_logs) / "diagnostic.log").write_text("addStreamingConversation\n", encoding="utf-8")

            class _AlwaysEmptyBridge(_HiddenWindowBridge):
                def ensure_mode(self, pid: int, mode: str, background: bool = False) -> bool:
                    return True

                def write_prompt_and_submit(self, pid: int, text: str) -> tuple[bool, bool]:
                    return True, True

                def poll_chat(self, pid: int) -> dict[str, Any]:
                    return {"has_window": True if self.visible else False, "busy": False, "text": "", "confirmation_card": None}

            empty_ax = _AlwaysEmptyBridge()
            empty_ax.visible = True

            def _wait_returns_done(*, log_state, **_kwargs):
                log_state["saw_done"] = True
                return None

            req = DesktopJobRequest(
                job_id="dsk-post-done-empty",
                prompt="Check fail-fast",
                driver="macos_ax",
                mode="chat",
                timeout_sec=120,
            )
            with mock.patch.dict(os.environ, {"GEMINI_DIAGNOSTIC_LOG_DIR": tmp_logs}, clear=False), \
                 mock.patch.object(MacOSGeminiDriver, "_check_screen_locked", return_value="unlocked"), \
                 mock.patch.object(MacOSGeminiDriver, "_check_accessibility", return_value="granted"), \
                 mock.patch.object(
                     drv,
                     "discover_app",
                     return_value={
                         "app_detected": True,
                         "app_name": "Gemini",
                         "app_path": "/Applications/Gemini.app",
                         "bundle_id": "com.google.GeminiMacOS",
                         "app_version": "2.0",
                         "app_running": True,
                         "is_pwa": False,
                     },
                 ), \
                 mock.patch.object(MacOSGeminiDriver, "_check_orca", return_value=None), \
                 mock.patch.object(MacOSGeminiDriver, "_find_running_pid", return_value=4242), \
                 mock.patch.object(dw._MacOSAXBridge, "get_instance", return_value=empty_ax), \
                 mock.patch.object(drv, "_wait_via_diagnostic_log", side_effect=_wait_returns_done), \
                 mock.patch.object(drv, "_extract_one_shot_background", return_value={"has_window": False, "busy": False, "text": "", "confirmation_card": None}), \
                 mock.patch("desktop_worker.time.sleep", return_value=None):
                with self.assertRaises(RuntimeError) as ctx:
                    drv.execute_prompt("prompt", req.job_id, req, threading.Event())
            self.assertIn("yielded no AX response in background mode", str(ctx.exception))

    def test_macos_zero_switch_open_app_window_silent_and_axhidden(self):
        """open_app_window_silent opens OmnichatWindow via AXMenuBar File->Open App + AXHidden=True with 0 AXFrontmost calls."""
        bridge = dw._MacOSAXBridge.__new__(dw._MacOSAXBridge)
        handles: dict[int, tuple[str, Any]] = {}
        next_id = [9000]
        frontmost_sets: list[Any] = []
        actions_called: list[tuple[int, str]] = []

        def _alloc(kind: str, val: Any) -> int:
            next_id[0] += 1
            handles[next_id[0]] = (kind, val)
            return next_id[0]

        bridge._attrs = {
            name: _alloc("attr", name)
            for name in (
                "AXWindows",
                "AXChildren",
                "AXRole",
                "AXSubrole",
                "AXIdentifier",
                "AXDescription",
                "AXTitle",
                "AXValue",
                "AXEnabled",
                "AXHidden",
                "AXFrontmost",
                "AXMenuBar",
                "AXPress",
            )
        }
        bridge._k_true = _alloc("bool", True)
        bridge._k_false = _alloc("bool", False)

        # Start with MinichatWindow (AXSystemDialog) and AXHidden=True; File -> Open App transitions to OmnichatWindow (AXStandardWindow).
        nodes: dict[int, dict[str, Any]] = {
            100: {"AXWindows": [200], "AXHidden": True, "AXMenuBar": 300},
            200: {"AXRole": "AXWindow", "AXSubrole": "AXSystemDialog", "AXTitle": "Gemini Mini Chat — New chat"},
            201: {"AXRole": "AXWindow", "AXSubrole": "AXStandardWindow", "AXTitle": "Gemini — New chat"},
            300: {"AXRole": "AXMenuBar", "AXChildren": [310]},
            310: {"AXRole": "AXMenuBarItem", "AXTitle": "File", "AXChildren": [311]},
            311: {"AXRole": "AXMenu", "AXChildren": [312]},
            312: {"AXRole": "AXMenuItem", "AXTitle": "Open App", "AXEnabled": True},
        }

        class _CF:
            def CFGetTypeID(self, ref: int) -> int:
                return {"str": 1, "arr": 2, "bool": 3}.get(handles.get(ref, ("", None))[0], 0)

            def CFStringGetTypeID(self) -> int:
                return 1

            def CFArrayGetTypeID(self) -> int:
                return 2

            def CFBooleanGetTypeID(self) -> int:
                return 3

            def CFStringCreateWithCString(self, _a, raw_bytes: bytes, _e: int) -> int:
                return _alloc("str", raw_bytes.decode("utf-8"))

            def CFStringGetLength(self, ref: int) -> int:
                return len(handles[ref][1])

            def CFStringGetMaximumSizeForEncoding(self, length: int, _e: int) -> int:
                return length * 4 + 1

            def CFStringGetCString(self, ref: int, buf, max_bytes: int, _e: int) -> bool:
                raw = handles[ref][1].encode("utf-8")[: max_bytes - 1]
                buf[0 : len(raw) + 1] = raw + b"\x00"
                return True

            def CFBooleanGetValue(self, ref: int) -> bool:
                return bool(handles[ref][1])

            def CFArrayGetCount(self, ref: int) -> int:
                return len(handles[ref][1])

            def CFArrayGetValueAtIndex(self, ref: int, idx: int) -> int:
                return int(handles[ref][1][idx])

            def CFRetain(self, ref: int) -> int:
                return ref

            def CFRelease(self, _ref: int) -> None:
                return None

        class _AX:
            def AXUIElementCreateApplication(self, _pid: int) -> int:
                return 100

            def AXUIElementSetMessagingTimeout(self, _app: int, _t: float) -> int:
                return 0

            def AXUIElementCopyAttributeValue(self, el: int, attr_ref: int, out_ref) -> int:
                attr_name = handles[attr_ref][1]
                node = nodes.get(el, {})
                if attr_name not in node:
                    return -25212
                val = node[attr_name]
                if isinstance(val, bool):
                    out_ref._obj.value = _alloc("bool", val)
                elif isinstance(val, str):
                    out_ref._obj.value = _alloc("str", val)
                elif isinstance(val, int):
                    out_ref._obj.value = val
                elif isinstance(val, list):
                    out_ref._obj.value = _alloc("arr", val)
                return 0

            def AXUIElementSetAttributeValue(self, el: int, attr_ref: int, val_ref: int) -> int:
                attr_name = handles[attr_ref][1]
                if attr_name == "AXFrontmost":
                    frontmost_sets.append(val_ref)
                kind, val = handles.get(val_ref, ("", None))
                if el in nodes and kind == "bool":
                    nodes[el][attr_name] = val
                return 0

            def AXUIElementPerformAction(self, el: int, action_ref: int) -> int:
                act_name = handles[action_ref][1]
                actions_called.append((el, act_name))
                if el == 312 and act_name == "AXPress":
                    nodes[100]["AXWindows"] = [201]
                    nodes[100]["AXHidden"] = False
                return 0

        bridge.cf = _CF()
        bridge.ax = _AX()
        bridge.cg = None

        self.assertFalse(bridge.has_usable_background_window(4242))
        with mock.patch("desktop_worker.time.sleep", return_value=None):
            ok = bridge.open_app_window_silent(4242, keep_hidden=True, wait_s=1.0)
        self.assertTrue(ok)
        self.assertTrue(bridge.has_usable_background_window(4242))
        self.assertTrue(bridge.is_hidden(4242))
        self.assertIn((312, "AXPress"), actions_called)
        self.assertEqual(frontmost_sets, [])

    def test_macos_task_mode_intermediate_endOfData_and_zero_focus_switch_flow(self):
        """Task mode ignores intermediate endOfData, resets saw_done if busy=True, and achieves 0 focus switches with silent open."""
        with tempfile.TemporaryDirectory() as tmp_ws, tempfile.TemporaryDirectory() as tmp_logs, tempfile.TemporaryDirectory() as tmp_app:
            target_ws = os.path.realpath(tmp_ws)
            fake_app = Path(tmp_app) / "Gemini.app"
            (fake_app / "Contents").mkdir(parents=True)
            diag_log = Path(tmp_logs) / "diagnostic-task.log"
            diag_log.write_text("boot\n", encoding="utf-8")

            # 1. _read_diagnostic_log_updates ignores intermediate endOfData / Loop exited in task mode
            with mock.patch.dict(os.environ, {"GEMINI_DIAGNOSTIC_LOG_DIR": tmp_logs}, clear=False):
                state = MacOSGeminiDriver._snapshot_diagnostic_log()
                with diag_log.open("a", encoding="utf-8") as fh:
                    fh.write(
                        "agentModeTask: started\n"
                        "addStreamingConversation\n"
                        "ClientGenerateResponseStream.endOfData\n"
                        "Loop exited normally\n"
                    )
                saw_start, saw_done = MacOSGeminiDriver._read_diagnostic_log_updates(state, mode="task")
                self.assertTrue(saw_start)
                self.assertFalse(saw_done)

                # If removeStreamingConversation() is followed immediately by a new addStreamingConversation(), saw_done stays False
                with diag_log.open("a", encoding="utf-8") as fh:
                    fh.write("removeStreamingConversation()\naddStreamingConversation\n")
                _, saw_done_restarted = MacOSGeminiDriver._read_diagnostic_log_updates(state, mode="task")
                self.assertFalse(saw_done_restarted)
                self.assertTrue(state.get("saw_recent_activity"))

                # Final agentModeTask: ended + removeStreamingConversation() triggers saw_done=True
                with diag_log.open("a", encoding="utf-8") as fh:
                    fh.write("agentModeTask: ended (success=true)\nremoveStreamingConversation()\n")
                _, saw_done_final = MacOSGeminiDriver._read_diagnostic_log_updates(state, mode="task")
                self.assertTrue(saw_done_final)

            # 2. Full zero-focus-switch MacOSGeminiDriver run using open_app_window_silent + AXHidden=True
            diag_log.write_text("boot\n", encoding="utf-8")
            drv = MacOSGeminiDriver()
            job_id = "dsk-zero-switch-01"
            req = DesktopJobRequest(
                job_id=job_id,
                prompt="Zero switch test",
                driver="macos_ax",
                mode="task",
                workspace_path=target_ws,
                timeout_sec=15,
            )
            framed = build_sentinel_prompt(job_id, req.prompt, mode="task", workspace_path=target_ws)
            expected_md = (
                f"{SentinelEnvelope.start_marker(job_id)}\n"
                "## Executive Summary\nCompleted with 0 focus switches.\n"
                f"{SentinelEnvelope.done_marker(job_id)}"
            )

            class _ZeroSwitchBridge:
                def __init__(self) -> None:
                    self._usable_win = False
                    self._hidden = True
                    self.bring_calls: list[int] = []
                    self.activate_calls: list[int] = []
                    self.polls = 0

                def is_hidden(self, _pid: int) -> bool:
                    return self._hidden

                def set_hidden(self, _pid: int, hidden: bool = True) -> bool:
                    self._hidden = bool(hidden)
                    return True

                def has_window(self, _pid: int) -> bool:
                    return self._usable_win

                def has_usable_background_window(self, _pid: int) -> bool:
                    return self._usable_win

                def open_app_window_silent(self, _pid: int, keep_hidden: bool = True, wait_s: float = 2.0, cancel_event=None) -> bool:
                    self._usable_win = True
                    if keep_hidden:
                        self._hidden = True
                    return True

                def _bring_frontmost(self, pid: int) -> None:
                    self.bring_calls.append(pid)

                def _activate_pid(self, pid: int) -> bool:
                    self.activate_calls.append(pid)
                    return True

                def press_new_chat(self, _pid: int) -> bool:
                    return True

                def ensure_mode(self, _pid: int, mode: str, background: bool = False) -> bool:
                    return background is True and mode == "task"

                def attach_workspace_folder(self, _pid: int, ws: str, restore_clipboard: bool = True, background: bool = False) -> bool:
                    return background is True and ws == target_ws

                def write_prompt_and_submit(self, _pid: int, text: str) -> tuple[bool, bool]:
                    return (text == framed), True

                def poll_chat(self, _pid: int) -> dict[str, Any]:
                    self.polls += 1
                    if self.polls == 1:
                        with diag_log.open("a", encoding="utf-8") as fh:
                            fh.write("agentModeTask: started\naddStreamingConversation\nClientGenerateResponseStream.endOfData\n")
                        return {"has_window": True, "busy": True, "text": "", "confirmation_card": None}
                    return {"has_window": True, "busy": False, "text": expected_md, "confirmation_card": None}

            zero_ax = _ZeroSwitchBridge()
            with mock.patch.dict(os.environ, {"GEMINI_DIAGNOSTIC_LOG_DIR": tmp_logs}, clear=False), \
                 mock.patch.object(MacOSGeminiDriver, "_check_screen_locked", return_value="unlocked"), \
                 mock.patch.object(MacOSGeminiDriver, "_check_accessibility", return_value="granted"), \
                 mock.patch.object(
                     drv,
                     "discover_app",
                     return_value={
                         "app_detected": True,
                         "app_name": "Gemini",
                         "app_path": str(fake_app),
                         "bundle_id": "com.google.GeminiMacOS",
                         "app_version": "2.0",
                         "app_running": True,
                         "is_pwa": False,
                     },
                 ), \
                 mock.patch.object(MacOSGeminiDriver, "_check_orca", return_value=None), \
                 mock.patch.object(MacOSGeminiDriver, "_find_running_pid", return_value=4242), \
                 mock.patch.object(MacOSGeminiDriver, "_get_frontmost_pid", side_effect=AssertionError("Must not probe/steal focus")), \
                 mock.patch.object(dw._MacOSAXBridge, "get_instance", return_value=zero_ax), \
                 mock.patch.object(MacOSGeminiDriver, "_pbpaste_bytes") as mock_pbpaste, \
                 mock.patch.object(MacOSGeminiDriver, "_pbcopy_bytes") as mock_pbcopy, \
                 mock.patch("desktop_worker.subprocess.run") as mock_sub_run, \
                 mock.patch("desktop_worker.time.sleep", return_value=None):
                raw_text, meta = drv.execute_prompt(framed, job_id, req, threading.Event())

            self.assertEqual(raw_text, expected_md)
            self.assertTrue(meta["background"])
            self.assertTrue(meta["workspace_attached"])
            self.assertEqual(zero_ax.bring_calls, [])
            self.assertEqual(zero_ax.activate_calls, [])
            self.assertTrue(zero_ax._hidden)
            mock_sub_run.assert_not_called()
            mock_pbpaste.assert_not_called()
            mock_pbcopy.assert_not_called()

            # 3. If saw_done latches from a false wakeup while busy=True, _execute_via_native_ax_background resets saw_done
            class _FalseSawDoneBridge(_ZeroSwitchBridge):
                def __init__(self) -> None:
                    super().__init__()
                    self.extract_calls = 0

                def poll_chat(self, _pid: int) -> dict[str, Any]:
                    self.polls += 1
                    if self.polls <= 2:
                        return {"has_window": False, "busy": False, "text": "", "confirmation_card": None}
                    if self.polls == 3:
                        # False done returned busy=True -> must clear log_state["saw_done"]!
                        return {"has_window": True, "busy": True, "text": "", "confirmation_card": None}
                    return {"has_window": True, "busy": False, "text": expected_md, "confirmation_card": None}

            saw_done_ax = _FalseSawDoneBridge()
            wait_call_states: list[bool] = []

            def _fake_wait(*, log_state, **_kw):
                wait_call_states.append(bool(log_state.get("saw_done", False)))
                if len(wait_call_states) == 1:
                    log_state["saw_done"] = True
                    return None
                return {"has_window": True, "busy": False, "text": expected_md, "confirmation_card": None}

            with mock.patch.dict(os.environ, {"GEMINI_DIAGNOSTIC_LOG_DIR": tmp_logs}, clear=False), \
                 mock.patch.object(MacOSGeminiDriver, "_check_screen_locked", return_value="unlocked"), \
                 mock.patch.object(MacOSGeminiDriver, "_check_accessibility", return_value="granted"), \
                 mock.patch.object(
                     drv,
                     "discover_app",
                     return_value={
                         "app_detected": True,
                         "app_name": "Gemini",
                         "app_path": str(fake_app),
                         "bundle_id": "com.google.GeminiMacOS",
                         "app_version": "2.0",
                         "app_running": True,
                         "is_pwa": False,
                     },
                 ), \
                 mock.patch.object(MacOSGeminiDriver, "_check_orca", return_value=None), \
                 mock.patch.object(MacOSGeminiDriver, "_find_running_pid", return_value=4242), \
                 mock.patch.object(dw._MacOSAXBridge, "get_instance", return_value=saw_done_ax), \
                 mock.patch.object(drv, "_wait_via_diagnostic_log", side_effect=_fake_wait), \
                 mock.patch("desktop_worker.time.sleep", return_value=None):
                raw2, _ = drv.execute_prompt(framed, job_id, req, threading.Event())
            self.assertEqual(raw2, expected_md)
            self.assertEqual(wait_call_states, [False, False])

    def test_macos_poll_chat_detects_tab_stop_continue_backup_card(self):
        """poll_chat detects tab_stop_Continue backup confirmation card so jobs abort immediately."""
        bridge = dw._MacOSAXBridge.__new__(dw._MacOSAXBridge)
        handles: dict[int, tuple[str, Any]] = {}
        next_id = [9500]

        def _alloc(kind: str, val: Any) -> int:
            next_id[0] += 1
            handles[next_id[0]] = (kind, val)
            return next_id[0]

        bridge._attrs = {
            name: _alloc("attr", name)
            for name in ("AXWindows", "AXChildren", "AXRole", "AXSubrole", "AXIdentifier", "AXDescription", "AXTitle", "AXValue")
        }
        bridge._k_true = _alloc("bool", True)
        nodes = {
            100: {"AXWindows": [201]},
            201: {"AXRole": "AXWindow", "AXSubrole": "AXStandardWindow", "AXChildren": [301]},
            301: {"AXRole": "AXButton", "AXIdentifier": "tab_stop_Continue", "AXDescription": "Continue, keyboard shortcut Command Return"},
        }

        class _CF:
            def CFGetTypeID(self, ref: int) -> int:
                return {"str": 1, "arr": 2}.get(handles.get(ref, ("", None))[0], 0)
            def CFStringGetTypeID(self) -> int: return 1
            def CFArrayGetTypeID(self) -> int: return 2
            def CFBooleanGetTypeID(self) -> int: return 3
            def CFStringGetLength(self, ref: int) -> int: return len(handles[ref][1])
            def CFStringGetMaximumSizeForEncoding(self, length: int, _e: int) -> int: return length * 4 + 1
            def CFStringGetCString(self, ref: int, buf, max_bytes: int, _e: int) -> bool:
                raw = handles[ref][1].encode("utf-8")[: max_bytes - 1]
                buf[0 : len(raw) + 1] = raw + b"\x00"
                return True
            def CFArrayGetCount(self, ref: int) -> int: return len(handles[ref][1])
            def CFArrayGetValueAtIndex(self, ref: int, idx: int) -> int: return int(handles[ref][1][idx])
            def CFRetain(self, ref: int) -> int: return ref
            def CFRelease(self, _ref: int) -> None: return None

        class _AX:
            def AXUIElementCreateApplication(self, _pid: int) -> int: return 100
            def AXUIElementSetMessagingTimeout(self, _app: int, _t: float) -> int: return 0
            def AXUIElementCopyAttributeValue(self, el: int, attr_ref: int, out_ref) -> int:
                attr_name = handles[attr_ref][1]
                node = nodes.get(el, {})
                if attr_name not in node: return -25212
                val = node[attr_name]
                out_ref._obj.value = _alloc("str" if isinstance(val, str) else "arr", val)
                return 0

        bridge.cf = _CF()
        bridge.ax = _AX()
        bridge.cg = None
        polled = bridge.poll_chat(4242)
        self.assertTrue(polled["has_window"])
        self.assertEqual(polled["confirmation_card"], "tab_stop_Continue")

    def test_windows_driver_background_env_var_and_meta(self):
        """WindowsGeminiDriver passes AGY_DESKTOP_BACKGROUND='1' (background=True) and '0' (background=False)."""
        with tempfile.TemporaryDirectory() as tmp:
            local_app = Path(tmp) / "LocalAppData"
            exe_path = local_app / "Programs" / "Gemini" / "Gemini.exe"
            exe_path.parent.mkdir(parents=True, exist_ok=True)
            exe_path.write_text("stub", encoding="utf-8")

            drv = WindowsGeminiDriver()
            for bg_flag, expected_env_val in ((True, "1"), (False, "0")):
                job_id = f"dsk-win-bg-{expected_env_val}"
                req = DesktopJobRequest(
                    job_id=job_id,
                    prompt="Win background test",
                    driver="windows_uia",
                    background=bg_flag,
                )
                framed = build_sentinel_prompt(job_id, req.prompt)
                captured_env: dict[str, str] = {}

                class _FakeWinProc:
                    def __init__(self, cmd, stdin=None, stdout=None, stderr=None, text=None, encoding=None, env=None):
                        captured_env.update(env or {})
                        self.returncode = 0

                        class _Stdin:
                            def write(_, _s):
                                pass

                            def close(_):
                                pass

                        class _Stdout:
                            def read(_):
                                return json.dumps(
                                    {
                                        "text": (
                                            f"{SentinelEnvelope.start_marker(job_id)}\n"
                                            "## Executive Summary\nOK\n"
                                            f"{SentinelEnvelope.done_marker(job_id)}"
                                        ),
                                        "clipboard_restored": True,
                                        "clipboard_touched": not bg_flag,
                                        "background": bg_flag,
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

                with mock.patch.dict(os.environ, {"LOCALAPPDATA": str(local_app)}, clear=False), \
                     mock.patch.object(WindowsGeminiDriver, "_find_powershell", return_value="powershell.exe"), \
                     mock.patch("desktop_worker.subprocess.Popen", side_effect=_FakeWinProc):
                    _, meta = drv.execute_prompt(framed, job_id, req, threading.Event())

                self.assertEqual(captured_env.get("AGY_DESKTOP_BACKGROUND"), expected_env_val)
                self.assertEqual(meta["background"], bg_flag)
                self.assertEqual(meta["clipboard_touched"], not bg_flag)

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

    def test_default_task_mode_validation_and_readonly_workspace_prompt(self):
        """DesktopJobRequest defaults to mode='task', validates mode/workspace_path, and SentinelEnvelope enforces read-only workspace rules."""
        req_default = DesktopJobRequest(job_id="J-1", prompt="Analyze repo")
        self.assertEqual(req_default.mode, "task")
        self.assertIsNone(req_default.workspace_path)

        with self.assertRaises(ValueError):
            DesktopJobRequest(job_id="J-bad-mode", prompt="Analyze repo", mode="invalid")

        missing_ws = str(Path(tempfile.gettempdir()) / f"nonexistent_ws_{os.getpid()}_xyz")
        with self.assertRaises(ValueError):
            DesktopJobRequest(job_id="J-bad-ws", prompt="Analyze repo", workspace_path=missing_ws)

        with self.assertRaises(ValueError):
            DesktopJobRequest.from_dict({"job_id": "J-bad-dict", "prompt": "Analyze repo", "mode": "invalid"})

        with tempfile.TemporaryDirectory() as tmp_ws:
            resolved_ws = os.path.realpath(tmp_ws)
            req_task = DesktopJobRequest(
                job_id="J-task-ws",
                prompt="Analyze repo",
                workspace_path=tmp_ws,
            )
            self.assertEqual(req_task.mode, "task")
            self.assertEqual(req_task.workspace_path, resolved_ws)

            prompt_task = SentinelEnvelope.build_prompt(
                "J-task-ws",
                "Inspect modules",
                mode="task",
                workspace_path=resolved_ws,
            )
            self.assertIn("Connected Workspace (STRICTLY READ-ONLY)", prompt_task)
            self.assertIn("strictly read-only mode", prompt_task)
            self.assertIn("never modify, create, or delete files", prompt_task)
            self.assertIn(resolved_ws, prompt_task)

            prompt_chat = SentinelEnvelope.build_prompt(
                "J-chat-ws",
                "Quick question",
                mode="chat",
                workspace_path=resolved_ws,
            )
            self.assertNotIn("Connected Workspace (STRICTLY READ-ONLY)", prompt_chat)


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

    def test_sqlite_legacy_desktop_jobs_migration_adds_mode_and_workspace_columns(self):
        """StateStore._init_db migrates legacy desktop_jobs table to add mode, workspace_path, and workspace_attached."""
        with tempfile.TemporaryDirectory() as tmp:
            legacy_db = os.path.join(tmp, "legacy_desktop.db")
            conn = sqlite3.connect(legacy_db)
            conn.execute(
                """
                CREATE TABLE desktop_jobs (
                    job_id TEXT PRIMARY KEY,
                    task_id TEXT,
                    status TEXT NOT NULL,
                    os_platform TEXT NOT NULL,
                    driver_name TEXT NOT NULL,
                    app_path TEXT,
                    prompt_chars INTEGER NOT NULL DEFAULT 0,
                    prompt_preview TEXT,
                    redaction_count INTEGER NOT NULL DEFAULT 0,
                    redactions_json TEXT,
                    artifact_path TEXT,
                    summary_excerpt TEXT,
                    output_chars INTEGER NOT NULL DEFAULT 0,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    estimated_saved_usd REAL NOT NULL DEFAULT 0.0,
                    clipboard_restored INTEGER NOT NULL DEFAULT 1,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO desktop_jobs (
                    job_id, task_id, status, os_platform, driver_name, prompt_chars, created_at
                ) VALUES ('dsk-legacy-1', 'TASK-26', 'completed', 'darwin', 'mock', 120, '2026-11-17T00:00:00+00:00')
                """
            )
            conn.commit()
            conn.close()

            store = StateStore(db_path=legacy_db, workspace_root=tmp)
            check_conn = sqlite3.connect(legacy_db)
            cols = {row[1] for row in check_conn.execute("PRAGMA table_info(desktop_jobs)").fetchall()}
            check_conn.close()

            self.assertIn("mode", cols)
            self.assertIn("workspace_path", cols)
            self.assertIn("workspace_attached", cols)
            self.assertIn("background", cols)

            jobs = store.list_desktop_jobs(job_id="dsk-legacy-1")
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]["mode"], "task")
            self.assertIsNone(jobs[0]["workspace_path"])
            self.assertFalse(jobs[0]["workspace_attached"])
            self.assertTrue(jobs[0]["background"])

    def test_background_mode_rest_migration_and_dashboard_checkbox(self):
        """POST /api/desktop/dispatch defaults to background=True, honors background=False, and dashboard renders #desktop-dispatch-background."""
        # 1. Default dispatch -> background=True
        st_bg, _, res_bg = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "job_id": "dsk-bg-default-01",
                "driver": "mock",
                "async_mode": False,
                "prompt": "Default silent background dispatch",
            },
        )
        self.assertEqual(st_bg, 200)
        self.assertTrue(res_bg["job"]["background"])

        # 2. Explicit background=False (--allow-foreground equivalent)
        st_fg, _, res_fg = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "job_id": "dsk-fg-optin-01",
                "driver": "mock",
                "async_mode": False,
                "background": False,
                "prompt": "Opt-in foreground dispatch",
            },
        )
        self.assertEqual(st_fg, 200)
        self.assertFalse(res_fg["job"]["background"])

        # 3. Dashboard HTML contains checked #desktop-dispatch-background checkbox
        st_html, _, html = self._request("GET", "/")
        self.assertEqual(st_html, 200)
        self.assertIn('id="desktop-dispatch-background"', html)

    def test_task_mode_default_workspace_guard_chat_mode_and_dashboard_ui(self):
        """POST /api/desktop/dispatch defaults to task+workspace_root, rejects /etc & bogus mode (400), supports chat mode, and renders UI controls."""
        expected_ws = os.path.realpath(self.temp_dir.name)

        # 1. Default dispatch (omitted mode & workspace_path) -> task + server workspace_root + workspace_attached=True
        st_def, _, res_def = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "job_id": "dsk-task-default-01",
                "driver": "mock",
                "async_mode": False,
                "prompt": "Default task mode workspace check",
            },
        )
        self.assertEqual(st_def, 200)
        job_def = res_def["job"]
        self.assertEqual(job_def["status"], "completed")
        self.assertEqual(job_def["mode"], "task")
        self.assertEqual(job_def["workspace_path"], expected_ws)
        self.assertTrue(job_def["workspace_attached"])

        # 2. Sensitive workspace root (/etc) rejected with HTTP 400
        st_etc, _, res_etc = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "driver": "mock",
                "mode": "task",
                "workspace_path": "/etc",
                "prompt": "Sensitive root test",
            },
        )
        self.assertEqual(st_etc, 400)
        self.assertIn("error", res_etc)

        # 3. Invalid mode="bogus" rejected with HTTP 400
        st_bogus, _, res_bogus = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "driver": "mock",
                "mode": "bogus",
                "prompt": "Bogus mode test",
            },
        )
        self.assertEqual(st_bogus, 400)
        self.assertIn("error", res_bogus)

        # 4. mode="chat" executes with workspace_attached=False and no workspace_path
        st_chat, _, res_chat = self._request(
            "POST",
            "/api/desktop/dispatch",
            {
                "job_id": "dsk-chat-mode-01",
                "driver": "mock",
                "mode": "chat",
                "async_mode": False,
                "prompt": "Quick chat mode test",
            },
        )
        self.assertEqual(st_chat, 200)
        job_chat = res_chat["job"]
        self.assertEqual(job_chat["status"], "completed")
        self.assertEqual(job_chat["mode"], "chat")
        self.assertIsNone(job_chat["workspace_path"])
        self.assertFalse(job_chat["workspace_attached"])

        # 5. Dashboard HTML renders #desktop-dispatch-mode and #desktop-dispatch-workspace
        st_html, _, html = self._request("GET", "/")
        self.assertEqual(st_html, 200)
        self.assertIn('id="desktop-dispatch-mode"', html)
        self.assertIn('id="desktop-dispatch-workspace"', html)
        self.assertIn("onDesktopDispatchModeChange", html)


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

    def test_cli_desktop_ask_task_mode_workspace_binding(self):
        """client.py desktop-ask --driver mock --mode task --workspace <tmpdir> --json binds workspace E2E."""
        client_cli = str(ORCH_DIR / "client.py")
        with tempfile.TemporaryDirectory() as cli_ws:
            expected_ws = os.path.realpath(cli_ws)
            proc = subprocess.run(
                [
                    sys.executable,
                    client_cli,
                    "--url",
                    self.base_url,
                    "desktop-ask",
                    "--driver",
                    "mock",
                    "--mode",
                    "task",
                    "--workspace",
                    cli_ws,
                    "--prompt",
                    "CLI task mode workspace check",
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "ok")
            job = payload["job"]
            self.assertEqual(job["status"], "completed")
            self.assertEqual(job["mode"], "task")
            self.assertEqual(job["workspace_path"], expected_ws)
            self.assertTrue(job["workspace_attached"])

    def test_cli_desktop_ask_background_default_and_allow_foreground(self):
        """client.py desktop-ask defaults to background=True (timeout=240) and --allow-foreground sets background=False."""
        import client as client_mod

        with mock.patch.object(
            OrchestratorClient,
            "desktop_dispatch",
            return_value={"status": "ok", "job": {"job_id": "dsk-sig-1", "status": "completed", "background": True}},
        ) as mock_disp, \
             mock.patch.object(sys, "argv", ["client.py", "desktop-ask", "--prompt", "hi", "--json"]), \
             mock.patch("builtins.print"):
            client_mod.main()
        self.assertTrue(mock_disp.call_args.kwargs["background"])
        self.assertEqual(mock_disp.call_args.kwargs["timeout_sec"], 240)

        client_cli = str(ORCH_DIR / "client.py")
        p_bg = subprocess.run(
            [
                sys.executable,
                client_cli,
                "--url",
                self.base_url,
                "desktop-ask",
                "--driver",
                "mock",
                "--prompt",
                "CLI background default check",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        d_bg = json.loads(p_bg.stdout)
        self.assertEqual(d_bg["status"], "ok")
        self.assertTrue(d_bg["job"]["background"])

        p_fg = subprocess.run(
            [
                sys.executable,
                client_cli,
                "--url",
                self.base_url,
                "desktop-ask",
                "--driver",
                "mock",
                "--allow-foreground",
                "--prompt",
                "CLI allow foreground check",
                "--json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        d_fg = json.loads(p_fg.stdout)
        self.assertEqual(d_fg["status"], "ok")
        self.assertFalse(d_fg["job"]["background"])


if __name__ == "__main__":
    unittest.main()
