#!/usr/bin/env python3
"""
Cross-Platform Gemini Desktop App Worker Bridge.

Provides zero-dependency (Python 3.10+ stdlib only) discovery, pre-flight
diagnostics, secret scrubbing, split-literal sentinel framing, clipboard
save/restore, cross-process locking, and OS drivers (macOS, Windows, Linux, Mock)
for offloading bounded read-only deep-analysis prompts to the local Gemini
Desktop App at $0.00 AGY API spend.
"""

from __future__ import annotations

import argparse
from abc import ABC, abstractmethod
from contextlib import contextmanager
import ctypes
import ctypes.util
from dataclasses import asdict, dataclass, field
import datetime
import glob
import json
import os
from pathlib import Path, PureWindowsPath
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Iterator
import uuid

if os.name == "nt":
    import msvcrt  # type: ignore[import-not-found]
else:
    import fcntl


# ---------------------------------------------------------------------------
# Module Constants & Validation Contracts
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT_SEC: int = 180
DEFAULT_POLL_INTERVAL_MS: int = 750
DEFAULT_STABILITY_DEBOUNCE_MS: int = 500
DEFAULT_MAX_PROMPT_CHARS: int = 150_000
SOFT_PROMPT_WARNING_CHARS: int = 60_000

SUPPORTED_DRIVERS: tuple[str, ...] = (
    "auto",
    "macos_ax",
    "orca",
    "windows_uia",
    "linux_pwa",
    "mock",
)

VALID_JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")
MACOS_BUNDLE_IDS: tuple[str, ...] = (
    "com.google.GeminiMacOS",
    "com.google.gemini",
    "com.google.GeminiMacOS.launcher",
)
MACOS_PWA_BUNDLE_PREFIXES: tuple[str, ...] = (
    "com.google.Chrome.app.",
    "com.microsoft.edgemac.app.",
    "org.chromium.Chromium.app.",
)
WINDOWS_ALLOWED_EXES: frozenset[str] = frozenset(
    {
        "gemini.exe",
        "msedge.exe",
        "chrome.exe",
    }
)
LINUX_ALLOWED_BINARIES: frozenset[str] = frozenset(
    {
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
        "microsoft-edge-stable",
    }
)
_LINUX_DISALLOWED_RESOLVED_NAMES: frozenset[str] = frozenset(
    {
        "sh",
        "bash",
        "zsh",
        "dash",
        "fish",
        "csh",
        "tcsh",
        "ksh",
        "python",
        "python3",
        "perl",
        "ruby",
        "nc",
        "curl",
        "wget",
    }
)
ALLOWED_ARTIFACT_EXTENSIONS: frozenset[str] = frozenset({".md", ".json", ".txt"})

USD_TO_VND_RATE: float = 25400.0
BASELINE_CARBON_RATES: dict[str, float] = {"in": 2.00, "out": 10.00}

_DONE_PREFIX = "<<<AGY_DESKTOP_DONE:"
_DONE_SUFFIX = ">>>"


class DesktopJobCancelledError(RuntimeError):
    """Raised when a desktop worker job is cancelled mid-execution."""


class SecretRedactionError(ValueError):
    """Structured error raised when strict secret mode detects credentials."""

    def __init__(self, message: str, redactions: dict[str, int] | None = None) -> None:
        super().__init__(message)
        self.redactions: dict[str, int] = dict(redactions or {})
        self.total_redactions: int = sum(self.redactions.values())


# ---------------------------------------------------------------------------
# Static Automation Scripts (NEVER interpolate untrusted prompt/path strings!)
# ---------------------------------------------------------------------------

_MACOS_AX_TRUST_JXA = (
    'ObjC.import("ApplicationServices");\n'
    "$.AXIsProcessTrustedWithOptions(null);\n"
)

_MACOS_SCREEN_LOCK_JXA = (
    'ObjC.import("CoreGraphics");\n'
    "var d = $.CGSessionCopyCurrentDictionary();\n"
    'if (!d) { "unlocked"; }\n'
    "else {\n"
    "  var obj = ObjC.deepUnwrap(ObjC.castRefToObject(d));\n"
    '  (obj && obj.CGSSessionScreenIsLocked) ? "locked" : "unlocked";\n'
    "}\n"
)

_MACOS_ACTIVATE_AND_CHECK_JXA = """
function run(argv) {
  var procName = argv[0] || "Gemini";
  var se = Application("System Events");
  var procs = se.processes.whose({ name: procName });
  if (procs.length === 0) {
    return JSON.stringify({ running: false, windowCount: 0, focused: false });
  }
  var p = procs[0];
  try { p.frontmost = true; } catch (e) {}
  var wins = [];
  try { wins = p.windows(); } catch (e) {}
  var focused = false;
  if (wins.length > 0) {
    try {
      var w = wins[0];
      var elems = w.entireContents();
      for (var i = 0; i < elems.length; i++) {
        var el = elems[i];
        var role = "";
        try { role = el.role(); } catch (e) {}
        if (role === "AXTextArea" || role === "AXTextField") {
          try {
            el.focused = true;
            focused = true;
            break;
          } catch (e) {}
        }
      }
    } catch (e) {}
  }
  return JSON.stringify({ running: true, windowCount: wins.length, focused: focused });
}
"""

_MACOS_NEW_CHAT_APPLESCRIPT = """
on run argv
  set procName to item 1 of argv
  tell application "System Events"
    tell process procName
      set frontmost to true
      delay 0.15
      keystroke "n" using command down
    end tell
  end tell
end run
"""

_MACOS_PASTE_APPLESCRIPT = """
on run argv
  set procName to item 1 of argv
  tell application "System Events"
    tell process procName
      set frontmost to true
      delay 0.1
      keystroke "v" using command down
    end tell
  end tell
end run
"""

_MACOS_SUBMIT_JXA = """
function run(argv) {
  var procName = argv[0] || "Gemini";
  var se = Application("System Events");
  var procs = se.processes.whose({ name: procName });
  if (procs.length === 0) {
    return "missing_process";
  }
  var p = procs[0];
  try { p.frontmost = true; } catch (e) {}
  try {
    var wins = p.windows();
    if (wins.length > 0) {
      var elems = wins[0].entireContents();
      for (var i = 0; i < elems.length; i++) {
        var el = elems[i];
        var role = "";
        try { role = el.role(); } catch (e) {}
        if (role === "AXButton") {
          var title = "";
          var desc = "";
          try { title = String(el.title() || ""); } catch (e) {}
          try { desc = String(el.description() || ""); } catch (e) {}
          var label = (title + " " + desc).toLowerCase();
          if (label.indexOf("submit") !== -1 || label === "send" || label.indexOf("send message") !== -1) {
            var enabled = true;
            try { enabled = Boolean(el.enabled()); } catch (e) {}
            if (enabled) {
              el.click();
              return "clicked_submit";
            }
          }
        }
      }
    }
  } catch (e) {}
  se.keyCode(36);
  return "sent_return";
}
"""

_MACOS_POLL_AX_JXA = """
function run(argv) {
  var procName = argv[0] || "Gemini";
  var se = Application("System Events");
  var procs = se.processes.whose({ name: procName });
  if (procs.length === 0) {
    return JSON.stringify({ running: false, busy: false, text: "" });
  }
  var p = procs[0];
  var wins = [];
  try { wins = p.windows(); } catch (e) {}
  if (wins.length === 0) {
    return JSON.stringify({ running: true, busy: false, text: "" });
  }
  var busy = false;
  var chunks = [];
  try {
    var elems = wins[0].entireContents();
    for (var i = 0; i < elems.length; i++) {
      var el = elems[i];
      var role = "";
      try { role = el.role(); } catch (e) {}
      var title = "";
      var desc = "";
      var val = "";
      try { title = String(el.title() || ""); } catch (e) {}
      try { desc = String(el.description() || ""); } catch (e) {}
      if (role === "AXButton") {
        var bLabel = (title + " " + desc).toLowerCase();
        if (bLabel.indexOf("stop response") !== -1 || bLabel === "stop" || bLabel.indexOf("stop generating") !== -1) {
          busy = true;
        }
      }
      if (role === "AXStaticText" || role === "AXTextArea" || role === "AXTextField" || role === "AXWebArea") {
        try {
          var rawVal = el.value();
          if (rawVal !== null && rawVal !== undefined) {
            val = String(rawVal);
          }
        } catch (e) {}
        var combined = val || title || desc;
        if (combined) {
          if (combined.indexOf("Generating your response") !== -1) {
            busy = true;
          }
          chunks.push(combined);
        }
      }
    }
  } catch (e) {}
  return JSON.stringify({ running: true, busy: busy, text: chunks.join("\\n") });
}
"""

_MACOS_COPY_RESPONSE_JXA = """
function run(argv) {
  var procName = argv[0] || "Gemini";
  var se = Application("System Events");
  var procs = se.processes.whose({ name: procName });
  if (procs.length === 0) {
    return "missing_process";
  }
  var p = procs[0];
  try { p.frontmost = true; } catch (e) {}
  var lastCopy = null;
  try {
    var wins = p.windows();
    if (wins.length > 0) {
      var elems = wins[0].entireContents();
      for (var i = 0; i < elems.length; i++) {
        var el = elems[i];
        var role = "";
        try { role = el.role(); } catch (e) {}
        if (role === "AXButton") {
          var title = "";
          var desc = "";
          try { title = String(el.title() || ""); } catch (e) {}
          try { desc = String(el.description() || ""); } catch (e) {}
          var label = (title + " " + desc).trim().toLowerCase();
          if (label === "copy" || label === "copy response") {
            lastCopy = el;
          }
        }
      }
    }
  } catch (e) {}
  if (lastCopy !== null) {
    try {
      lastCopy.click();
      return "clicked_copy";
    } catch (e) {}
  }
  se.keystroke("c", { using: ["command down", "shift down"] });
  return "sent_cmd_shift_c";
}
"""

_WINDOWS_UIA_PS_SCRIPT = r"""
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class AgyWin32 {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@

$promptPath = $env:AGY_DESKTOP_PROMPT_FILE
if (-not $promptPath -or -not (Test-Path -LiteralPath $promptPath)) {
    throw "Prompt file missing via AGY_DESKTOP_PROMPT_FILE"
}
$promptText = [System.IO.File]::ReadAllText($promptPath, [System.Text.Encoding]::UTF8)
$jobId = $env:AGY_DESKTOP_JOB_ID
$appPath = $env:AGY_DESKTOP_APP_PATH
$timeoutSec = [int]([string]$env:AGY_DESKTOP_TIMEOUT_SEC)
if ($timeoutSec -le 0) { $timeoutSec = 180 }
$pollMs = [int]([string]$env:AGY_DESKTOP_POLL_MS)
if ($pollMs -lt 100) { $pollMs = 750 }
$newChat = ($env:AGY_DESKTOP_NEW_CHAT -eq "1")
$restoreClip = ($env:AGY_DESKTOP_RESTORE_CLIPBOARD -ne "0")

function Get-GeminiWindow {
    $procs = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowHandle -ne 0 -and ($_.ProcessName -eq "Gemini" -or $_.MainWindowTitle -like "*Gemini*")
    }
    return $procs | Select-Object -First 1
}

$proc = Get-GeminiWindow
if (-not $proc -and $appPath -and (Test-Path -LiteralPath $appPath)) {
    Start-Process -FilePath $appPath | Out-Null
    $launchDeadline = (Get-Date).AddSeconds(8)
    while ((Get-Date) -lt $launchDeadline) {
        Start-Sleep -Milliseconds 250
        $proc = Get-GeminiWindow
        if ($proc) { break }
    }
}
if (-not $proc) {
    throw "Could not find running Gemini Desktop window"
}

[AgyWin32]::ShowWindow($proc.MainWindowHandle, 9) | Out-Null
[AgyWin32]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 200

$rootEl = [System.Windows.Automation.AutomationElement]::FromHandle($proc.MainWindowHandle)
if ($newChat) {
    $newChatCond = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty, "New chat"
    )
    $newChatBtn = $rootEl.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $newChatCond)
    if ($newChatBtn) {
        try {
            $inv = $newChatBtn.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
            $inv.Invoke()
        } catch {
            [System.Windows.Forms.SendKeys]::SendWait("^n")
        }
    } else {
        [System.Windows.Forms.SendKeys]::SendWait("^n")
    }
    Start-Sleep -Milliseconds 350
}

$editCond = New-Object System.Windows.Automation.OrCondition(
    (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)),
    (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Document))
)
$editEl = $rootEl.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $editCond)
if ($editEl) {
    try { $editEl.SetFocus() } catch {}
}

$hadText = [System.Windows.Forms.Clipboard]::ContainsText()
$savedClip = $null
if ($hadText) {
    $savedClip = [System.Windows.Forms.Clipboard]::GetText()
}
$clipRestored = $true
try {
    [System.Windows.Forms.Clipboard]::SetText($promptText)
    Start-Sleep -Milliseconds 80
    [System.Windows.Forms.SendKeys]::SendWait("^v")
    Start-Sleep -Milliseconds 250
} finally {
    if ($restoreClip) {
        try {
            if ($hadText -and $null -ne $savedClip) {
                [System.Windows.Forms.Clipboard]::SetText($savedClip)
            } else {
                [System.Windows.Forms.Clipboard]::Clear()
            }
        } catch {
            $clipRestored = $false
        }
    }
}

$submitCond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty, "Submit"
)
$submitBtn = $rootEl.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $submitCond)
if ($submitBtn) {
    try {
        $inv2 = $submitBtn.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
        $inv2.Invoke()
    } catch {
        [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    }
} else {
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
}

$startMarker = "<<<AGY_DESKTOP_START:" + $jobId + ">>>"
$doneMarker = "<<<AGY_DESKTOP_DONE:" + $jobId + ">>>"
$boundary = "--- TASK CONTEXT ---"
$deadline = (Get-Date).AddSeconds($timeoutSec)
$lastLen = -1
$stableSince = $null
$capturedText = ""
$sawBusy = $false
$idlePolls = 0

function Read-UiaTreeText($root) {
    $stopBusy = $false
    $stopCond = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty, "Stop response"
    )
    if ($root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $stopCond)) {
        $stopBusy = $true
    }
    $textCond = New-Object System.Windows.Automation.OrCondition(
        (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Text)),
        (New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Document))
    )
    $nodes = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $textCond)
    $sb = New-Object System.Text.StringBuilder
    foreach ($n in $nodes) {
        $t = ""
        try {
            $tp = $null
            if ($n.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern, [ref]$tp)) {
                $t = $tp.DocumentRange.GetText(-1)
            }
        } catch {}
        if (-not $t) {
            try { $t = [string]$n.Current.Name } catch {}
        }
        if ($t) {
            if ($t -like "*Generating your response*") { $stopBusy = $true }
            [void]$sb.AppendLine($t)
        }
    }
    return @{ busy = $stopBusy; text = $sb.ToString() }
}

while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds $pollMs
    $snap = Read-UiaTreeText $rootEl
    if ($snap.busy) {
        $sawBusy = $true
        $idlePolls = 0
        $lastLen = -1
        $stableSince = $null
        continue
    }
    $idlePolls++
    $txt = $snap.text
    $bIdx = $txt.LastIndexOf($boundary)
    $scoped = if ($bIdx -ge 0) { $txt.Substring($bIdx + $boundary.Length) } else { $txt }
    $sIdx = $scoped.IndexOf($startMarker)
    $dIdx = if ($sIdx -ge 0) { $scoped.IndexOf($doneMarker, $sIdx + $startMarker.Length) } else { -1 }
    if ($sIdx -lt 0 -or $dIdx -le $sIdx) {
        if ($sawBusy -or $idlePolls -ge 3) {
            $probeSaved = $null
            $probeHad = [System.Windows.Forms.Clipboard]::ContainsText()
            if ($probeHad) { $probeSaved = [System.Windows.Forms.Clipboard]::GetText() }
            try {
                [AgyWin32]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
                [System.Windows.Forms.SendKeys]::SendWait("^+c")
                Start-Sleep -Milliseconds 180
                if ([System.Windows.Forms.Clipboard]::ContainsText()) {
                    $txt = [System.Windows.Forms.Clipboard]::GetText()
                    $sIdx = $txt.IndexOf($startMarker)
                    $dIdx = if ($sIdx -ge 0) { $txt.IndexOf($doneMarker, $sIdx + $startMarker.Length) } else { -1 }
                }
            } finally {
                if ($restoreClip) {
                    try {
                        if ($probeHad -and $null -ne $probeSaved) {
                            [System.Windows.Forms.Clipboard]::SetText($probeSaved)
                        } else {
                            [System.Windows.Forms.Clipboard]::Clear()
                        }
                    } catch {
                        $clipRestored = $false
                    }
                }
            }
        }
    }
    if ($sIdx -ge 0 -and $dIdx -gt $sIdx) {
        if ($txt.Length -eq $lastLen) {
            if ($null -ne $stableSince -and ((Get-Date) - $stableSince).TotalMilliseconds -ge 500) {
                $capturedText = $txt
                break
            }
        } else {
            $lastLen = $txt.Length
            $stableSince = Get-Date
        }
    } else {
        $lastLen = -1
        $stableSince = $null
    }
}

if (-not $capturedText) {
    $fallbackSaved = $null
    $fallbackHad = [System.Windows.Forms.Clipboard]::ContainsText()
    if ($fallbackHad) { $fallbackSaved = [System.Windows.Forms.Clipboard]::GetText() }
    try {
        [AgyWin32]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null
        [System.Windows.Forms.SendKeys]::SendWait("^+c")
        Start-Sleep -Milliseconds 250
        if ([System.Windows.Forms.Clipboard]::ContainsText()) {
            $capturedText = [System.Windows.Forms.Clipboard]::GetText()
        }
    } finally {
        if ($restoreClip) {
            try {
                if ($fallbackHad -and $null -ne $fallbackSaved) {
                    [System.Windows.Forms.Clipboard]::SetText($fallbackSaved)
                } else {
                    [System.Windows.Forms.Clipboard]::Clear()
                }
            } catch {
                $clipRestored = $false
            }
        }
    }
}

if (-not $capturedText) {
    throw "Timed out waiting for Gemini Windows Desktop response"
}

$resultObj = @{
    text = $capturedText
    clipboard_restored = $clipRestored
}
$resultJson = $resultObj | ConvertTo-Json -Compress
$outputPath = $env:AGY_DESKTOP_OUTPUT_FILE
if ($outputPath) {
    $tmpOut = "$outputPath.tmp"
    [System.IO.File]::WriteAllText($tmpOut, $resultJson, [System.Text.Encoding]::UTF8)
    Move-Item -LiteralPath $tmpOut -Destination $outputPath -Force
    Write-Output '{"ok":true}'
} else {
    Write-Output $resultJson
}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_job_id() -> str:
    """Generate a compact URL-safe desktop job identifier."""
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"dsk-{stamp}-{uuid.uuid4().hex[:6]}"


def _normalize_os(target_os: str = "auto") -> str:
    raw = (target_os or "auto").strip().lower()
    if raw == "auto":
        if sys.platform == "darwin":
            return "darwin"
        if sys.platform == "win32":
            return "win32"
        if sys.platform.startswith("linux"):
            return "linux"
        return sys.platform
    if raw in ("darwin", "macos", "mac"):
        return "darwin"
    if raw in ("win32", "windows", "win"):
        return "win32"
    if raw.startswith("linux"):
        return "linux"
    raise ValueError(f"Unsupported target_os: {target_os!r}")


def _is_allowed_macos_bundle_id(bundle_id: str | None) -> bool:
    if not isinstance(bundle_id, str):
        return False
    bid = bundle_id.strip()
    if not bid:
        return False
    if bid in MACOS_BUNDLE_IDS:
        return True
    return any(bid.startswith(prefix) and len(bid) > len(prefix) for prefix in MACOS_PWA_BUNDLE_PREFIXES)


def validate_app_path(app_path: str, platform_name: str | None = None) -> str:
    """Validate custom Gemini Desktop app_path against strict per-OS binary/bundle allowlists."""
    if not isinstance(app_path, str) or not app_path.strip():
        raise ValueError("Invalid app_path: must be a non-empty string")
    raw = app_path.strip()
    if "\x00" in raw:
        raise ValueError("Invalid app_path: null byte is not allowed")
    if raw.startswith("-"):
        raise ValueError("Invalid app_path: leading '-' is not allowed")

    eff_os = _normalize_os(platform_name or "auto")

    if eff_os == "darwin":
        expanded = Path(raw).expanduser()
        resolved = Path(os.path.realpath(str(expanded)))
        if not resolved.exists() or not resolved.is_dir() or resolved.suffix.lower() != ".app":
            raise ValueError(
                f"Invalid macOS app_path {app_path!r}: must be an existing .app bundle directory"
            )
        plist_path = resolved / "Contents" / "Info.plist"
        if not plist_path.is_file():
            raise ValueError(
                f"Invalid macOS app_path {app_path!r}: missing Contents/Info.plist"
            )
        try:
            with plist_path.open("rb") as fh:
                plist_data = plistlib.load(fh)
        except (OSError, plistlib.InvalidFileException, ValueError) as exc:
            raise ValueError(f"Invalid macOS app_path {app_path!r}: unreadable Info.plist ({exc})") from exc
        bundle_id = plist_data.get("CFBundleIdentifier") if isinstance(plist_data, dict) else None
        if not _is_allowed_macos_bundle_id(bundle_id):
            raise ValueError(
                f"Unapproved macOS CFBundleIdentifier {bundle_id!r} for app_path {app_path!r}"
            )
        return str(resolved)

    if eff_os == "win32":
        if raw.startswith("\\\\") or raw.startswith("//"):
            raise ValueError(f"Invalid Windows app_path {app_path!r}: UNC network paths are rejected")
        win_name = PureWindowsPath(raw).name.lower()
        if win_name not in WINDOWS_ALLOWED_EXES:
            raise ValueError(
                f"Unapproved Windows executable {win_name!r}; allowed: {', '.join(sorted(WINDOWS_ALLOWED_EXES))}"
            )
        expanded = Path(raw).expanduser()
        resolved = Path(os.path.realpath(str(expanded)))
        if not resolved.exists() or not resolved.is_file() or resolved.suffix.lower() != ".exe":
            raise ValueError(
                f"Invalid Windows app_path {app_path!r}: must reference an existing .exe file"
            )
        return str(resolved)

    if eff_os == "linux":
        expanded = Path(raw).expanduser()
        basename = expanded.name
        if basename not in LINUX_ALLOWED_BINARIES:
            raise ValueError(
                f"Unapproved Linux browser binary {basename!r}; allowed: {', '.join(sorted(LINUX_ALLOWED_BINARIES))}"
            )
        if expanded.exists():
            if expanded.is_dir():
                raise ValueError(f"Invalid Linux app_path {app_path!r}: path cannot be a directory")
            resolved = Path(os.path.realpath(str(expanded)))
            if resolved.is_dir() or resolved.name.lower() in _LINUX_DISALLOWED_RESOLVED_NAMES:
                raise ValueError(f"Invalid Linux app_path {app_path!r}: unsafe resolved target")
            return str(resolved)
        return raw

    raise ValueError(f"Unsupported platform for app_path validation: {eff_os!r}")


def _compute_saved_quota(input_chars: int, output_chars: int) -> tuple[float, int]:
    """Approximate API spend saved against Gemini 4 Carbon baseline rates."""
    est_in = (max(0, int(input_chars or 0)) + 3) // 4
    est_out = (max(0, int(output_chars or 0)) + 3) // 4
    usd = round(
        (est_in / 1_000_000.0) * BASELINE_CARBON_RATES["in"]
        + (est_out / 1_000_000.0) * BASELINE_CARBON_RATES["out"],
        4,
    )
    vnd = round(usd * USD_TO_VND_RATE)
    return usd, vnd


def _build_summary_excerpt(clean_markdown: str, max_chars: int = 600) -> str:
    text = " ".join(line.strip() for line in clean_markdown.splitlines() if line.strip())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


# ---------------------------------------------------------------------------
# Data Contracts
# ---------------------------------------------------------------------------

@dataclass
class DesktopDriverStatus:
    os_platform: str
    driver_name: str
    ready: bool
    app_detected: bool
    app_name: str | None = None
    app_path: str | None = None
    bundle_id: str | None = None
    app_version: str | None = None
    app_running: bool = False
    available_backends: list[str] = field(default_factory=list)
    permissions: dict[str, str] = field(default_factory=dict)
    queue_depth: int = 0
    lock_busy: bool = False
    warnings: list[str] = field(default_factory=list)
    remediation_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DesktopJobRequest:
    job_id: str
    prompt: str
    task_id: str | None = None
    driver: str = "auto"
    target_os: str = "auto"
    app_path: str | None = None
    timeout_sec: int = DEFAULT_TIMEOUT_SEC
    poll_interval_ms: int = DEFAULT_POLL_INTERVAL_MS
    output_path: str | None = None
    redact_secrets: bool = True
    strict_secrets: bool = False
    restore_clipboard: bool = True
    restore_focus: bool = False
    new_chat: bool = True
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DesktopJobRequest":
        raw_job_id = data.get("job_id")
        job_id = str(raw_job_id).strip() if raw_job_id else generate_job_id()
        if not VALID_JOB_ID_RE.match(job_id):
            raise ValueError(f"Invalid job_id format: {job_id!r}")

        raw_meta = data.get("metadata") or {}
        if not isinstance(raw_meta, dict):
            raise ValueError("metadata must be a JSON object")
        metadata = {str(k): str(v) for k, v in raw_meta.items()}

        return cls(
            job_id=job_id,
            prompt=str(data.get("prompt") or ""),
            task_id=str(data["task_id"]) if data.get("task_id") is not None else None,
            driver=str(data.get("driver") or "auto").strip().lower(),
            target_os=str(data.get("target_os") or "auto").strip().lower(),
            app_path=str(data["app_path"]) if data.get("app_path") is not None else None,
            timeout_sec=max(1, int(data.get("timeout_sec", DEFAULT_TIMEOUT_SEC))),
            poll_interval_ms=max(50, int(data.get("poll_interval_ms", DEFAULT_POLL_INTERVAL_MS))),
            output_path=str(data["output_path"]) if data.get("output_path") is not None else None,
            redact_secrets=bool(data.get("redact_secrets", True)),
            strict_secrets=bool(data.get("strict_secrets", False)),
            restore_clipboard=bool(data.get("restore_clipboard", True)),
            restore_focus=bool(data.get("restore_focus", False)),
            new_chat=bool(data.get("new_chat", True)),
            metadata=metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DesktopJobResult:
    job_id: str
    status: str
    driver_used: str
    os_platform: str
    artifact_path: str | None = None
    summary_excerpt: str = ""
    raw_char_count: int = 0
    duration_ms: int = 0
    redactions: dict[str, int] = field(default_factory=dict)
    estimated_saved_usd: float = 0.0
    estimated_saved_vnd: int = 0
    clipboard_restored: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Pre-Flight SecretRedactor
# ---------------------------------------------------------------------------

class SecretRedactor:
    """Scans and scrubs common API keys, JWTs, PEM blocks, and DSN passwords."""

    PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
        ("google_api_key", re.compile(r"AIza[0-9A-Za-z\-_]{35}"), "[REDACTED:GOOGLE_API_KEY]"),
        ("openai_anthropic_key", re.compile(r"sk-(?:proj-|ant-)?[A-Za-z0-9\-_]{20,}"), "[REDACTED:LLM_API_KEY]"),
        ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"), "[REDACTED:GITHUB_TOKEN]"),
        ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED:AWS_ACCESS_KEY]"),
        ("jwt_token", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "[REDACTED:JWT]"),
        ("private_key_pem", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"), "[REDACTED:PRIVATE_KEY]"),
        ("dsn_credentials", re.compile(r"(postgresql|postgres|mysql|mongodb|redis)(?:\+[a-z]+)?://[^:\s/@]+:[^@\s]+@"), r"\1://[REDACTED_USER:PASS]@"),
        (
            "bearer_or_secret_kv",
            re.compile(
                r"(?i)(?:authorization:\s*bearer\s+\S+|bearer\s+[A-Za-z0-9_\-.=+/]{16,}|[\"']?(?:api_key|apiKey|secret|client_secret|password|passwd|access_token|refresh_token|auth_token|token)[\"']?\s*[=:]\s*[\"']?[A-Za-z0-9_.\-+/=]{12,}[\"']?)"
            ),
            "[REDACTED:CREDENTIAL]",
        ),
    ]

    @classmethod
    def scrub(
        cls,
        text: str,
        redact: bool = True,
        strict: bool = False,
        raise_on_strict: bool = False,
    ) -> dict[str, Any]:
        """Return {'text': str, 'redactions': dict[str, int], 'total_redactions': int, 'blocked': bool}."""
        if not text or (not redact and not strict):
            return {
                "text": text,
                "redactions": {},
                "total_redactions": 0,
                "blocked": False,
            }

        counts: dict[str, int] = {}
        working = text
        for category, pattern, replacement in cls.PATTERNS:
            if redact:
                working, count = pattern.subn(replacement, working)
            else:
                count = len(pattern.findall(working))
            if count > 0:
                counts[category] = count

        total = sum(counts.values())
        blocked = bool(strict and total > 0)
        if blocked and raise_on_strict:
            categories = ", ".join(sorted(counts.keys()))
            raise SecretRedactionError(
                f"Blocked prompt containing {total} detected secret(s): {categories}",
                redactions=counts,
            )

        return {
            "text": working if redact else text,
            "redactions": counts,
            "total_redactions": total,
            "blocked": blocked,
        }


def redact_secrets(
    text: str,
    strict: bool = False,
    redact: bool = True,
    raise_on_strict: bool = False,
) -> tuple[str, dict[str, int], bool]:
    """Return (sanitized_text, per_category_counts, blocked_by_strict)."""
    result = SecretRedactor.scrub(
        text,
        redact=redact,
        strict=strict,
        raise_on_strict=raise_on_strict,
    )
    return result["text"], result["redactions"], result["blocked"]


# ---------------------------------------------------------------------------
# Sentinel Envelope & Response Normalizer
# ---------------------------------------------------------------------------

class SentinelEnvelope:
    """Split-literal sentinel prompt framing and UI chrome stripper."""

    PROMPT_BOUNDARY = "--- TASK CONTEXT ---"
    UI_CHROME_LINES: set[str] = {
        "Gemini said",
        "Show thinking",
        "Hide thinking",
        "Copy",
        "Export to Docs",
        "Send feedback",
        "Stop response",
        "Generating your response…",
        "Generating your response...",
    }

    @staticmethod
    def start_marker(job_id: str) -> str:
        return f"<<<AGY_DESKTOP_START:{job_id}>>>"

    @staticmethod
    def done_marker(job_id: str) -> str:
        return f"{_DONE_PREFIX}{job_id}{_DONE_SUFFIX}"

    @classmethod
    def build_prompt(
        cls,
        job_id: str,
        prompt: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Frame prompt with split-literal closing instructions to prevent prompt-echo false positives."""
        start_tok = cls.start_marker(job_id)
        done_part_a = _DONE_PREFIX
        done_part_b = f"{job_id}{_DONE_SUFFIX}"

        meta_lines: list[str] = []
        if metadata:
            for key in sorted(metadata):
                val = str(metadata[key]).replace("\n", " ").strip()
                meta_lines.append(f"- {key}: {val}")
        meta_block = ("\nMetadata:\n" + "\n".join(meta_lines) + "\n") if meta_lines else ""

        lines = [
            f"[AGY_DESKTOP_WORKER_TASK job_id={job_id}]",
            "You are acting as a bounded deep-analysis worker for an automated software engineering orchestrator.",
            "Follow these strict formatting rules:",
            f"1. Begin your final answer with the exact marker line: {start_tok}",
            "2. Provide concise, evidence-grounded Markdown sections:",
            "   - ## Executive Summary",
            "   - ## Key Findings",
            "   - ## Risks & Edge Cases",
            "   - ## Actionable Recommendations",
            f'3. End your final answer with the exact marker line constructed by joining "{done_part_a}" and "{done_part_b}" with no spaces.',
            "4. Do NOT emit the end marker until your entire response is complete.",
        ]
        header = "\n".join(lines)
        if meta_block:
            header += meta_block
        return f"{header}\n\n{cls.PROMPT_BOUNDARY}\n{prompt}"

    @classmethod
    def has_complete_sentinel(
        cls,
        text: str,
        job_id: str,
        assistant_only: bool = False,
    ) -> bool:
        """Check whether assistant output contains both start and done markers in order."""
        if not text:
            return False

        start_tok = cls.start_marker(job_id)
        done_tok = cls.done_marker(job_id)

        scope = text
        if not assistant_only:
            boundary_idx = text.rfind(cls.PROMPT_BOUNDARY)
            if boundary_idx != -1:
                scope = text[boundary_idx + len(cls.PROMPT_BOUNDARY) :]
            else:
                # If prompt header exists without boundary, start searching after Rule 1's start marker.
                task_hdr = f"[AGY_DESKTOP_WORKER_TASK job_id={job_id}]"
                hdr_idx = text.rfind(task_hdr)
                if hdr_idx != -1:
                    first_start = text.find(start_tok, hdr_idx)
                    if first_start != -1:
                        scope = text[first_start + len(start_tok) :]

        start_idx = scope.find(start_tok)
        if start_idx == -1:
            return False
        done_idx = scope.find(done_tok, start_idx + len(start_tok))
        return done_idx != -1 and start_idx < done_idx

    @classmethod
    def _strip_ui_chrome(cls, text: str) -> str:
        cleaned_lines: list[str] = []
        blank_run = 0
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if stripped in cls.UI_CHROME_LINES:
                continue
            if not stripped:
                blank_run += 1
                if blank_run <= 2 and cleaned_lines:
                    cleaned_lines.append("")
                continue
            blank_run = 0
            cleaned_lines.append(raw_line.rstrip())
        return "\n".join(cleaned_lines).strip()

    @classmethod
    def extract_response(cls, raw_text: str, job_id: str) -> tuple[str, bool]:
        """Extract clean Markdown response between final start/done markers and report match status."""
        if not raw_text:
            return "", False

        start_tok = cls.start_marker(job_id)
        done_tok = cls.done_marker(job_id)

        scoped = raw_text
        boundary_idx = raw_text.rfind(cls.PROMPT_BOUNDARY)
        if boundary_idx != -1:
            scoped = raw_text[boundary_idx + len(cls.PROMPT_BOUNDARY) :]

        done_idx = scoped.rfind(done_tok)
        if done_idx != -1:
            start_idx = scoped.rfind(start_tok, 0, done_idx)
            if start_idx != -1 and start_idx < done_idx:
                body = scoped[start_idx + len(start_tok) : done_idx]
                return cls._strip_ui_chrome(body), True

        start_idx = scoped.rfind(start_tok)
        if start_idx != -1:
            partial = scoped[start_idx + len(start_tok) :]
            return cls._strip_ui_chrome(partial), False

        return cls._strip_ui_chrome(scoped), False


def build_sentinel_prompt(
    job_id: str,
    prompt: str,
    metadata: dict[str, str] | None = None,
) -> str:
    """Module-level alias for SentinelEnvelope.build_prompt."""
    return SentinelEnvelope.build_prompt(job_id, prompt, metadata=metadata)


def extract_sentinel_response(raw_text: str, job_id: str) -> tuple[str, bool]:
    """Module-level alias for SentinelEnvelope.extract_response."""
    return SentinelEnvelope.extract_response(raw_text, job_id)


# ---------------------------------------------------------------------------
# Base Driver & OS Driver Implementations
# ---------------------------------------------------------------------------

class BaseDesktopDriver(ABC):
    name: str = "base"
    supported_os: tuple[str, ...] = ()

    @abstractmethod
    def discover_app(self, app_path: str | None = None) -> dict[str, Any]:
        """Probe local installation paths and running process metadata."""

    @abstractmethod
    def doctor(self, app_path: str | None = None) -> DesktopDriverStatus:
        """Run non-intrusive readiness checks and return actionable diagnostics."""

    @abstractmethod
    def execute_prompt(
        self,
        framed_prompt: str,
        job_id: str,
        request: DesktopJobRequest,
        cancel_event: threading.Event,
    ) -> tuple[str, dict[str, Any]]:
        """Send framed_prompt to GUI app, wait for sentinel completion, return (raw_text, meta)."""


class MacOSGeminiDriver(BaseDesktopDriver):
    """macOS driver using native Info.plist discovery, JXA System Events, and pbcopy/pbpaste."""

    name: str = "macos_ax"
    supported_os: tuple[str, ...] = ("darwin",)

    def __init__(self, prefer_orca: bool = False) -> None:
        self.prefer_orca = prefer_orca
        if prefer_orca:
            self.name = "orca"

    @staticmethod
    def _parse_info_plist(plist_path: Path) -> dict[str, Any]:
        """Parse macOS Info.plist using stdlib plistlib."""
        try:
            with plist_path.open("rb") as fh:
                data = plistlib.load(fh)
        except (OSError, plistlib.InvalidFileException, ValueError):
            return {}

        url_schemes: list[str] = []
        for url_type in data.get("CFBundleURLTypes") or []:
            if isinstance(url_type, dict):
                for scheme in url_type.get("CFBundleURLSchemes") or []:
                    if isinstance(scheme, str) and scheme:
                        url_schemes.append(scheme)

        return {
            "CFBundleIdentifier": data.get("CFBundleIdentifier"),
            "CFBundleName": data.get("CFBundleName"),
            "CFBundleDisplayName": data.get("CFBundleDisplayName"),
            "CFBundleShortVersionString": data.get("CFBundleShortVersionString"),
            "CFBundleVersion": data.get("CFBundleVersion"),
            "CFBundleURLTypes": data.get("CFBundleURLTypes") or [],
            "LSMinimumSystemVersion": data.get("LSMinimumSystemVersion"),
            "url_schemes": url_schemes,
        }

    @staticmethod
    def _check_orca() -> str | None:
        env_cmd = os.environ.get("ORCA_CLI_COMMAND", "").strip()
        if env_cmd:
            return shutil.which(env_cmd) or (env_cmd if Path(env_cmd).exists() else None)
        return shutil.which("orca")

    @staticmethod
    def _check_accessibility() -> str:
        osascript = shutil.which("osascript") or ("/usr/bin/osascript" if Path("/usr/bin/osascript").exists() else None)
        if osascript:
            try:
                proc = subprocess.run(
                    [osascript, "-l", "JavaScript", "-"],
                    input=_MACOS_AX_TRUST_JXA,
                    text=True,
                    capture_output=True,
                    timeout=3.0,
                )
                out = proc.stdout.strip().lower()
                if proc.returncode == 0:
                    if out in ("true", "1"):
                        return "granted"
                    if out in ("false", "0"):
                        return "missing"
            except (OSError, subprocess.SubprocessError):
                pass

        if sys.platform == "darwin":
            try:
                lib_path = ctypes.util.find_library("ApplicationServices")
                if lib_path:
                    lib = ctypes.cdll.LoadLibrary(lib_path)
                    lib.AXIsProcessTrusted.restype = ctypes.c_bool
                    return "granted" if lib.AXIsProcessTrusted() else "missing"
            except (OSError, AttributeError):
                pass

        return "unknown"

    @staticmethod
    def _check_screen_locked() -> str:
        osascript = shutil.which("osascript") or ("/usr/bin/osascript" if Path("/usr/bin/osascript").exists() else None)
        if not osascript:
            return "unknown"
        try:
            proc = subprocess.run(
                [osascript, "-l", "JavaScript", "-"],
                input=_MACOS_SCREEN_LOCK_JXA,
                text=True,
                capture_output=True,
                timeout=3.0,
            )
            out = proc.stdout.strip().lower()
            if proc.returncode == 0 and out in ("locked", "unlocked"):
                return out
        except (OSError, subprocess.SubprocessError):
            pass
        return "unknown"

    @staticmethod
    def _check_shortcuts() -> list[str]:
        shortcuts_bin = shutil.which("shortcuts") or ("/usr/bin/shortcuts" if Path("/usr/bin/shortcuts").exists() else None)
        if not shortcuts_bin:
            return []
        try:
            proc = subprocess.run(
                [shortcuts_bin, "list"],
                text=True,
                capture_output=True,
                timeout=2.5,
            )
            if proc.returncode == 0:
                return [
                    line.strip()
                    for line in proc.stdout.splitlines()
                    if "gemini" in line.lower()
                ]
        except (OSError, subprocess.SubprocessError):
            pass
        return []

    @staticmethod
    def _is_app_running(app_name: str, app_path: str | None) -> bool:
        pgrep = shutil.which("pgrep")
        if not pgrep:
            return False
        try:
            res = subprocess.run(
                [pgrep, "-x", app_name],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if res.returncode == 0:
                return True
            if app_path:
                res2 = subprocess.run(
                    [pgrep, "-f", app_path],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
                return res2.returncode == 0
        except (OSError, subprocess.SubprocessError):
            pass
        return False

    def discover_app(self, app_path: str | None = None) -> dict[str, Any]:
        explicit = app_path or os.environ.get("GEMINI_APP_PATH")
        candidates: list[tuple[Path, bool]] = []

        if explicit:
            validated = validate_app_path(explicit, "darwin")
            candidates.append((Path(validated), False))
        else:
            mdfind = shutil.which("mdfind")
            if mdfind:
                try:
                    res = subprocess.run(
                        [
                            mdfind,
                            "kMDItemCFBundleIdentifier == 'com.google.GeminiMacOS' || kMDItemCFBundleIdentifier == 'com.google.gemini'",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=2.0,
                    )
                    if res.returncode == 0:
                        for line in res.stdout.splitlines():
                            line = line.strip()
                            if line:
                                candidates.append((Path(line), False))
                except (OSError, subprocess.SubprocessError):
                    pass

            for canonical in (
                Path("/Applications/Gemini.app"),
                Path.home() / "Applications" / "Gemini.app",
                Path("/Applications/Google Gemini.app"),
                Path.home() / "Applications" / "Google Gemini.app",
            ):
                candidates.append((canonical, False))

            pwa_globs = (
                str(Path.home() / "Applications" / "Chrome Apps.localized" / "*Gemini*.app"),
                str(Path.home() / "Applications" / "Edge Apps.localized" / "*Gemini*.app"),
                "/Applications/Chrome Apps.localized/*Gemini*.app",
                "/Applications/Edge Apps.localized/*Gemini*.app",
            )
            for pattern in pwa_globs:
                for match in sorted(glob.glob(pattern)):
                    candidates.append((Path(match), True))

        seen: set[str] = set()
        for cand, is_pwa in candidates:
            key = str(cand)
            if key in seen:
                continue
            seen.add(key)
            if not cand.exists():
                continue

            plist_path = cand / "Contents" / "Info.plist"
            info = self._parse_info_plist(plist_path) if plist_path.exists() else {}
            bundle_id = info.get("CFBundleIdentifier")
            app_name = info.get("CFBundleDisplayName") or info.get("CFBundleName") or cand.stem
            app_version = info.get("CFBundleShortVersionString") or info.get("CFBundleVersion")
            running = self._is_app_running(str(app_name), str(cand))

            return {
                "app_detected": True,
                "app_name": app_name,
                "app_path": str(cand),
                "bundle_id": bundle_id,
                "app_version": app_version,
                "url_schemes": info.get("url_schemes", []),
                "min_os_version": info.get("LSMinimumSystemVersion"),
                "app_running": running,
                "is_pwa": is_pwa or ("Apps.localized" in str(cand)),
            }

        return {
            "app_detected": False,
            "app_name": None,
            "app_path": str(Path(explicit).expanduser()) if explicit else None,
            "bundle_id": None,
            "app_version": None,
            "url_schemes": [],
            "min_os_version": None,
            "app_running": False,
            "is_pwa": False,
        }

    def doctor(self, app_path: str | None = None) -> DesktopDriverStatus:
        info = self.discover_app(app_path=app_path)
        accessibility = self._check_accessibility()
        screen_lock = self._check_screen_locked()
        pbcopy_bin = shutil.which("pbcopy") or ("/usr/bin/pbcopy" if Path("/usr/bin/pbcopy").exists() else None)
        pbpaste_bin = shutil.which("pbpaste") or ("/usr/bin/pbpaste" if Path("/usr/bin/pbpaste").exists() else None)
        osascript_bin = shutil.which("osascript") or ("/usr/bin/osascript" if Path("/usr/bin/osascript").exists() else None)
        clipboard_ok = bool(pbcopy_bin and pbpaste_bin)
        orca_bin = self._check_orca()
        gemini_shortcuts = self._check_shortcuts()

        available_backends: list[str] = []
        if orca_bin and (self.prefer_orca or os.environ.get("GEMINI_PREFER_ORCA") == "1"):
            available_backends.append("orca")
        if clipboard_ok and osascript_bin:
            available_backends.append("macos_ax")
        if orca_bin and "orca" not in available_backends:
            available_backends.append("orca")
        available_backends.append("mock")

        permissions: dict[str, str] = {
            "accessibility": accessibility,
            "clipboard": "ok" if clipboard_ok else "missing",
            "screen_lock": screen_lock,
            "orca": "available" if orca_bin else "not_installed",
            "shortcuts": "configured" if gemini_shortcuts else "none",
        }

        warnings: list[str] = []
        remediation: list[str] = []

        if not info["app_detected"]:
            remediation.append(
                "Install Google Gemini Desktop App for macOS into /Applications/Gemini.app (or pass --app-path / GEMINI_APP_PATH)."
            )
        if accessibility != "granted":
            remediation.append(
                "Grant Accessibility access to your terminal / Antigravity host in System Settings -> Privacy & Security -> Accessibility, then retry desktop-doctor."
            )
        if not clipboard_ok:
            remediation.append("Ensure /usr/bin/pbcopy and /usr/bin/pbpaste are available.")
        if not osascript_bin:
            remediation.append("Ensure /usr/bin/osascript is available on macOS.")
        if self.name == "orca" and not orca_bin:
            remediation.append("Driver 'orca' selected but 'orca' CLI is not installed; use --driver macos_ax or install orca.")

        if screen_lock == "locked":
            warnings.append("Mac screen is currently locked; unlock screen before dispatching GUI jobs.")
        if info.get("is_pwa"):
            warnings.append("Using Chrome/Edge PWA fallback instead of native /Applications/Gemini.app.")

        driver_ok = (orca_bin is not None) if self.name == "orca" else bool(osascript_bin)
        ready = bool(info["app_detected"] and clipboard_ok and accessibility == "granted" and driver_ok)

        return DesktopDriverStatus(
            os_platform="darwin",
            driver_name=self.name,
            ready=ready,
            app_detected=bool(info["app_detected"]),
            app_name=info["app_name"],
            app_path=info["app_path"],
            bundle_id=info["bundle_id"],
            app_version=info["app_version"],
            app_running=bool(info["app_running"]),
            available_backends=available_backends,
            permissions=permissions,
            warnings=warnings,
            remediation_steps=remediation,
        )

    @staticmethod
    def _pbpaste_bytes() -> bytes | None:
        pbpaste = shutil.which("pbpaste") or ("/usr/bin/pbpaste" if Path("/usr/bin/pbpaste").exists() else None)
        if not pbpaste:
            return None
        try:
            proc = subprocess.run([pbpaste], capture_output=True, timeout=2.0)
            if proc.returncode == 0:
                return proc.stdout
        except (OSError, subprocess.SubprocessError):
            pass
        return None

    @staticmethod
    def _pbcopy_bytes(data: bytes) -> bool:
        pbcopy = shutil.which("pbcopy") or ("/usr/bin/pbcopy" if Path("/usr/bin/pbcopy").exists() else None)
        if not pbcopy:
            return False
        try:
            proc = subprocess.run([pbcopy], input=data, capture_output=True, timeout=3.0)
            return proc.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    @staticmethod
    def _run_osascript(
        script: str,
        lang: str = "JavaScript",
        args: list[str] | None = None,
        timeout: float = 10.0,
    ) -> str:
        osascript = shutil.which("osascript") or "/usr/bin/osascript"
        cmd = [osascript, "-l", lang, "-"] if lang == "JavaScript" else [osascript, "-"]
        if args:
            cmd.extend(args)
        proc = subprocess.run(
            cmd,
            input=script,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            err = proc.stderr.strip() or f"osascript exited with code {proc.returncode}"
            raise RuntimeError(err)
        return proc.stdout.strip()

    def _execute_via_orca(
        self,
        orca_bin: str,
        framed_prompt: str,
        job_id: str,
        request: DesktopJobRequest,
        cancel_event: threading.Event,
        app_info: dict[str, Any],
        saved_clip: bytes | None,
    ) -> tuple[str, dict[str, Any]]:
        win_res = subprocess.run(
            [orca_bin, "computer", "windows", "--json"],
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        if win_res.returncode != 0:
            raise RuntimeError(win_res.stderr.strip() or "orca computer windows failed")

        windows = json.loads(win_res.stdout or "[]")
        target_win = None
        for win in windows if isinstance(windows, list) else []:
            title = str(win.get("title") or win.get("app") or "")
            if "gemini" in title.lower():
                target_win = win.get("id") or win.get("window_id")
                break
        if target_win is None:
            open_bin = shutil.which("open") or "/usr/bin/open"
            subprocess.run([open_bin, "-a", str(app_info["app_path"])], capture_output=True, timeout=5.0, check=True)
            time.sleep(0.5)
            win_res = subprocess.run([orca_bin, "computer", "windows", "--json"], capture_output=True, text=True, timeout=5.0)
            windows = json.loads(win_res.stdout or "[]")
            for win in windows if isinstance(windows, list) else []:
                if "gemini" in str(win.get("title") or win.get("app") or "").lower():
                    target_win = win.get("id") or win.get("window_id")
                    break
        if target_win is None:
            raise RuntimeError("Could not locate Gemini window via orca computer")

        clip_restored = True
        try:
            if not self._pbcopy_bytes(framed_prompt.encode("utf-8")):
                raise RuntimeError("Failed to write prompt to macOS clipboard")
            subprocess.run(
                [orca_bin, "computer", "hotkey", "cmd+v", "--window", str(target_win)],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=True,
            )
            time.sleep(0.25)
        finally:
            if request.restore_clipboard and saved_clip is not None:
                clip_restored = self._pbcopy_bytes(saved_clip)

        subprocess.run(
            [orca_bin, "computer", "hotkey", "return", "--window", str(target_win)],
            capture_output=True,
            text=True,
            timeout=5.0,
            check=True,
        )

        deadline = time.monotonic() + max(1, request.timeout_sec)
        poll_sec = max(0.1, request.poll_interval_ms / 1000.0)
        last_len: int | None = None
        stable_since: float | None = None
        captured = ""

        while True:
            if cancel_event.is_set():
                raise DesktopJobCancelledError("Desktop job cancelled")
            if time.monotonic() > deadline:
                raise TimeoutError(f"Timed out after {request.timeout_sec}s waiting for Gemini response via orca")

            snap_res = subprocess.run(
                [orca_bin, "computer", "snapshot", "--window", str(target_win), "--json"],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            snap_text = snap_res.stdout or ""
            busy = "stop response" in snap_text.lower() or "generating your response" in snap_text.lower()
            if not busy and SentinelEnvelope.has_complete_sentinel(snap_text, job_id):
                cur_len = len(snap_text)
                if last_len is not None and cur_len == last_len:
                    if stable_since is not None and (time.monotonic() - stable_since) * 1000.0 >= DEFAULT_STABILITY_DEBOUNCE_MS:
                        captured = snap_text
                        break
                else:
                    last_len = cur_len
                    stable_since = time.monotonic()
            else:
                last_len = None
                stable_since = None

            if cancel_event.wait(poll_sec):
                raise DesktopJobCancelledError("Desktop job cancelled")

        return captured, {
            "clipboard_restored": clip_restored,
            "app_path": app_info["app_path"],
            "bundle_id": app_info["bundle_id"],
            "backend": "orca",
        }

    def execute_prompt(
        self,
        framed_prompt: str,
        job_id: str,
        request: DesktopJobRequest,
        cancel_event: threading.Event,
    ) -> tuple[str, dict[str, Any]]:
        if cancel_event.is_set():
            raise DesktopJobCancelledError("Desktop job cancelled")

        if request.app_path:
            validate_app_path(request.app_path, "darwin")

        if self._check_screen_locked() == "locked":
            raise RuntimeError("Mac screen is locked; cannot drive Gemini Desktop GUI")

        if self._check_accessibility() != "granted":
            raise RuntimeError(
                "macOS Accessibility permission is missing; grant access in System Settings -> Privacy & Security -> Accessibility"
            )

        app_info = self.discover_app(app_path=request.app_path)
        if not app_info["app_detected"] or not app_info["app_path"]:
            raise RuntimeError("Gemini Desktop App not found on macOS")

        saved_clip = self._pbpaste_bytes() if request.restore_clipboard else None
        orca_bin = self._check_orca()
        if (self.prefer_orca or request.driver == "orca") and orca_bin:
            return self._execute_via_orca(
                orca_bin=orca_bin,
                framed_prompt=framed_prompt,
                job_id=job_id,
                request=request,
                cancel_event=cancel_event,
                app_info=app_info,
                saved_clip=saved_clip,
            )

        proc_name = str(app_info.get("app_name") or "Gemini")
        bundle_id = app_info.get("bundle_id")
        open_bin = shutil.which("open") or "/usr/bin/open"

        if request.new_chat and bundle_id in MACOS_BUNDLE_IDS:
            subprocess.run(
                [open_bin, "googlegemini://newchat?ext_src=app_shortcut"],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=True,
            )
        else:
            subprocess.run(
                [open_bin, "-a", str(app_info["app_path"])],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=True,
            )
            if request.new_chat:
                self._run_osascript(_MACOS_NEW_CHAT_APPLESCRIPT, lang="AppleScript", args=[proc_name], timeout=5.0)

        # Wait up to 3s for Gemini window readiness.
        ready_deadline = time.monotonic() + 3.0
        while time.monotonic() < ready_deadline:
            if cancel_event.is_set():
                raise DesktopJobCancelledError("Desktop job cancelled")
            state_raw = self._run_osascript(_MACOS_ACTIVATE_AND_CHECK_JXA, lang="JavaScript", args=[proc_name], timeout=4.0)
            try:
                state = json.loads(state_raw)
            except json.JSONDecodeError:
                state = {}
            if state.get("running") and int(state.get("windowCount", 0)) > 0:
                break
            if cancel_event.wait(0.15):
                raise DesktopJobCancelledError("Desktop job cancelled")

        # Write prompt to clipboard, paste, sleep 250ms, and restore user clipboard immediately.
        clipboard_restored = True
        try:
            if not self._pbcopy_bytes(framed_prompt.encode("utf-8")):
                raise RuntimeError("Failed to write framed prompt to clipboard via pbcopy")
            self._run_osascript(_MACOS_PASTE_APPLESCRIPT, lang="AppleScript", args=[proc_name], timeout=5.0)
            time.sleep(0.25)
        finally:
            if request.restore_clipboard and saved_clip is not None:
                clipboard_restored = self._pbcopy_bytes(saved_clip)

        # Submit prompt.
        self._run_osascript(_MACOS_SUBMIT_JXA, lang="JavaScript", args=[proc_name], timeout=5.0)

        # Poll for non-busy + sentinel + 500ms stability debounce.
        deadline = time.monotonic() + max(1, int(request.timeout_sec))
        poll_sec = max(0.1, int(request.poll_interval_ms) / 1000.0)
        last_len: int | None = None
        stable_since: float | None = None
        captured_text = ""
        saw_busy = False
        idle_polls = 0

        while True:
            if cancel_event.is_set():
                raise DesktopJobCancelledError("Desktop job cancelled")
            if time.monotonic() > deadline:
                raise TimeoutError(f"Timed out after {request.timeout_sec}s waiting for Gemini Desktop response")

            poll_raw = self._run_osascript(_MACOS_POLL_AX_JXA, lang="JavaScript", args=[proc_name], timeout=5.0)
            try:
                poll_data = json.loads(poll_raw)
            except json.JSONDecodeError:
                poll_data = {}

            busy = bool(poll_data.get("busy", False))
            candidate_text = str(poll_data.get("text") or "")

            if busy:
                saw_busy = True
                idle_polls = 0
                last_len = None
                stable_since = None
                if cancel_event.wait(poll_sec):
                    raise DesktopJobCancelledError("Desktop job cancelled")
                continue

            idle_polls += 1
            if not SentinelEnvelope.has_complete_sentinel(candidate_text, job_id) and (saw_busy or idle_polls >= 3):
                probe_clip = self._pbpaste_bytes() if request.restore_clipboard else None
                try:
                    self._run_osascript(_MACOS_COPY_RESPONSE_JXA, lang="JavaScript", args=[proc_name], timeout=5.0)
                    time.sleep(0.18)
                    copied_bytes = self._pbpaste_bytes()
                    if copied_bytes:
                        candidate_text = copied_bytes.decode("utf-8", errors="replace")
                finally:
                    if request.restore_clipboard and probe_clip is not None:
                        clipboard_restored = self._pbcopy_bytes(probe_clip) and clipboard_restored

            if SentinelEnvelope.has_complete_sentinel(candidate_text, job_id):
                cur_len = len(candidate_text)
                if last_len is not None and cur_len == last_len:
                    if stable_since is not None and (time.monotonic() - stable_since) * 1000.0 >= DEFAULT_STABILITY_DEBOUNCE_MS:
                        captured_text = candidate_text
                        break
                else:
                    last_len = cur_len
                    stable_since = time.monotonic()
            else:
                last_len = None
                stable_since = None

            if cancel_event.wait(poll_sec):
                raise DesktopJobCancelledError("Desktop job cancelled")

        # Fallback extraction via Copy button / Cmd+Shift+C if AX text lacked sentinel.
        if not SentinelEnvelope.has_complete_sentinel(captured_text, job_id):
            fallback_clip = self._pbpaste_bytes() if request.restore_clipboard else None
            try:
                self._run_osascript(_MACOS_COPY_RESPONSE_JXA, lang="JavaScript", args=[proc_name], timeout=5.0)
                time.sleep(0.2)
                copied_bytes = self._pbpaste_bytes()
                if copied_bytes:
                    captured_text = copied_bytes.decode("utf-8", errors="replace")
            finally:
                if request.restore_clipboard and fallback_clip is not None:
                    clipboard_restored = self._pbcopy_bytes(fallback_clip) and clipboard_restored

        return captured_text, {
            "clipboard_restored": clipboard_restored,
            "app_path": app_info["app_path"],
            "bundle_id": bundle_id,
            "backend": "macos_ax",
        }


class WindowsGeminiDriver(BaseDesktopDriver):
    """Windows driver using PowerShell -Sta + .NET UIAutomationClient + Clipboard."""

    name: str = "windows_uia"
    supported_os: tuple[str, ...] = ("win32",)

    @staticmethod
    def _find_powershell() -> str | None:
        return shutil.which("powershell.exe") or shutil.which("pwsh")

    def discover_app(self, app_path: str | None = None) -> dict[str, Any]:
        explicit = app_path or os.environ.get("GEMINI_APP_PATH")
        if explicit:
            validated = validate_app_path(explicit, "win32")
            p = Path(validated)
            return {
                "app_detected": True,
                "app_name": p.stem or "Gemini",
                "app_path": str(p),
                "bundle_id": "com.google.GeminiWindows",
                "app_version": None,
                "app_running": False,
                "is_pwa": False,
            }

        local_app = os.environ.get("LOCALAPPDATA", "")
        appdata = os.environ.get("APPDATA", "")
        prog_data = os.environ.get("ProgramData", "")

        exe_candidates: list[Path] = []
        if local_app:
            exe_candidates.extend([
                Path(local_app) / "Programs" / "Gemini" / "Gemini.exe",
                Path(local_app) / "Google" / "Gemini" / "Gemini.exe",
            ])

        for cand in exe_candidates:
            if cand.exists():
                return {
                    "app_detected": True,
                    "app_name": "Gemini",
                    "app_path": str(cand),
                    "bundle_id": "com.google.GeminiWindows",
                    "app_version": None,
                    "app_running": False,
                    "is_pwa": False,
                }

        # Check Start Menu shortcuts (*.lnk).
        start_dirs = [
            Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" if appdata else None,
            Path(prog_data) / "Microsoft" / "Windows" / "Start Menu" / "Programs" if prog_data else None,
        ]
        for sdir in start_dirs:
            if sdir and sdir.exists():
                for match in sorted(sdir.glob("*Gemini*.lnk")):
                    return {
                        "app_detected": True,
                        "app_name": match.stem,
                        "app_path": str(match),
                        "bundle_id": "com.google.GeminiWindows.shortcut",
                        "app_version": None,
                        "app_running": False,
                        "is_pwa": False,
                    }

        # Check Edge / Chrome PWA Web Applications folders.
        if local_app:
            pwa_dirs = [
                Path(local_app) / "Microsoft" / "Edge" / "User Data" / "Default" / "Web Applications",
                Path(local_app) / "Google" / "Chrome" / "User Data" / "Default" / "Web Applications",
            ]
            for pdir in pwa_dirs:
                if pdir.exists():
                    for match in sorted(pdir.glob("*Gemini*")):
                        return {
                            "app_detected": True,
                            "app_name": "Gemini (PWA)",
                            "app_path": str(match),
                            "bundle_id": "com.google.GeminiPWA",
                            "app_version": None,
                            "app_running": False,
                            "is_pwa": True,
                        }

        # Live Windows StartApps query for MSIX/AppX packages.
        ps_bin = self._find_powershell()
        if sys.platform == "win32" and ps_bin:
            try:
                proc = subprocess.run(
                    [
                        ps_bin,
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        "Get-StartApps | Where-Object { $_.Name -like '*Gemini*' } | Select-Object -First 1 | ConvertTo-Json -Compress",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=3.0,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    data = json.loads(proc.stdout.strip())
                    if isinstance(data, dict) and data.get("AppID"):
                        return {
                            "app_detected": True,
                            "app_name": data.get("Name") or "Gemini",
                            "app_path": f"shell:AppsFolder\\{data['AppID']}",
                            "bundle_id": str(data["AppID"]),
                            "app_version": None,
                            "app_running": False,
                            "is_pwa": False,
                        }
            except (OSError, subprocess.SubprocessError, ValueError):
                pass

        return {
            "app_detected": False,
            "app_name": None,
            "app_path": None,
            "bundle_id": None,
            "app_version": None,
            "app_running": False,
            "is_pwa": False,
        }

    def doctor(self, app_path: str | None = None) -> DesktopDriverStatus:
        info = self.discover_app(app_path=app_path)
        ps_bin = self._find_powershell()
        warnings: list[str] = []
        remediation: list[str] = []

        if not info["app_detected"]:
            remediation.append(
                "Install the official Google Gemini Windows Desktop App (or Edge/Chrome Gemini PWA) or pass --app-path."
            )
        if not ps_bin:
            remediation.append("Ensure Windows PowerShell (powershell.exe) is available in PATH for UIAutomationClient.")

        if info.get("is_pwa"):
            warnings.append("Using browser PWA fallback instead of native Gemini.exe.")

        ready = bool(info["app_detected"] and ps_bin)
        return DesktopDriverStatus(
            os_platform="win32",
            driver_name=self.name,
            ready=ready,
            app_detected=bool(info["app_detected"]),
            app_name=info["app_name"],
            app_path=info["app_path"],
            bundle_id=info["bundle_id"],
            app_version=info["app_version"],
            app_running=bool(info["app_running"]),
            available_backends=(["windows_uia", "mock"] if ps_bin else ["mock"]),
            permissions={
                "ui_automation": "ok" if ps_bin else "missing",
                "clipboard": "ok" if ps_bin else "missing",
            },
            warnings=warnings,
            remediation_steps=remediation,
        )

    @staticmethod
    def _reap_process(proc: Any) -> None:
        terminate_fn = getattr(proc, "terminate", None)
        if callable(terminate_fn):
            try:
                terminate_fn()
            except OSError:
                pass
        wait_fn = getattr(proc, "wait", None)
        if callable(wait_fn):
            try:
                wait_fn(timeout=2.0)
                return
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                return
        kill_fn = getattr(proc, "kill", None)
        if callable(kill_fn):
            try:
                kill_fn()
            except OSError:
                pass
            if callable(wait_fn):
                try:
                    wait_fn(timeout=2.0)
                except Exception:
                    pass

    def execute_prompt(
        self,
        framed_prompt: str,
        job_id: str,
        request: DesktopJobRequest,
        cancel_event: threading.Event,
    ) -> tuple[str, dict[str, Any]]:
        if cancel_event.is_set():
            raise DesktopJobCancelledError("Desktop job cancelled")

        if request.app_path:
            validate_app_path(request.app_path, "win32")

        ps_bin = self._find_powershell()
        if not ps_bin:
            raise RuntimeError("powershell.exe is required for Windows UIAutomation driver")

        app_info = self.discover_app(app_path=request.app_path)
        if not app_info["app_detected"]:
            raise RuntimeError("Gemini Desktop App not found on Windows")

        tmp_path: str | None = None
        out_tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix="agy_prompt_",
                suffix=".txt",
                delete=False,
            ) as fh:
                fh.write(framed_prompt)
                tmp_path = fh.name
            if os.name != "nt":
                os.chmod(tmp_path, 0o600)

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix="agy_output_",
                suffix=".json",
                delete=False,
            ) as out_fh:
                out_tmp_path = out_fh.name
            if os.name != "nt":
                os.chmod(out_tmp_path, 0o600)

            env = os.environ.copy()
            env["AGY_DESKTOP_PROMPT_FILE"] = tmp_path
            env["AGY_DESKTOP_OUTPUT_FILE"] = out_tmp_path
            env["AGY_DESKTOP_JOB_ID"] = job_id
            env["AGY_DESKTOP_APP_PATH"] = str(app_info.get("app_path") or "")
            env["AGY_DESKTOP_TIMEOUT_SEC"] = str(max(1, int(request.timeout_sec)))
            env["AGY_DESKTOP_POLL_MS"] = str(max(100, int(request.poll_interval_ms)))
            env["AGY_DESKTOP_NEW_CHAT"] = "1" if request.new_chat else "0"
            env["AGY_DESKTOP_RESTORE_CLIPBOARD"] = "1" if request.restore_clipboard else "0"

            proc = subprocess.Popen(
                [
                    ps_bin,
                    "-NoProfile",
                    "-NonInteractive",
                    "-Sta",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    "-",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env=env,
            )

            # Drain stdout/stderr concurrently before waiting so >64KB pipe output cannot deadlock.
            stdout_chunks: list[str] = []
            stderr_chunks: list[str] = []

            def _drain_stream(stream: Any, sink: list[str]) -> None:
                if stream is None:
                    return
                try:
                    sink.append(stream.read() or "")
                except Exception:
                    pass

            out_thread = (
                threading.Thread(target=_drain_stream, args=(proc.stdout, stdout_chunks), daemon=True)
                if proc.stdout is not None
                else None
            )
            err_thread = (
                threading.Thread(target=_drain_stream, args=(proc.stderr, stderr_chunks), daemon=True)
                if proc.stderr is not None
                else None
            )
            if out_thread is not None:
                out_thread.start()
            if err_thread is not None:
                err_thread.start()

            if proc.stdin is not None:
                try:
                    proc.stdin.write(_WINDOWS_UIA_PS_SCRIPT)
                    proc.stdin.close()
                except (BrokenPipeError, OSError):
                    pass

            deadline = time.monotonic() + max(5, int(request.timeout_sec) + 15)
            while proc.poll() is None:
                if cancel_event.is_set():
                    self._reap_process(proc)
                    if out_thread is not None:
                        out_thread.join(timeout=1.0)
                    if err_thread is not None:
                        err_thread.join(timeout=1.0)
                    raise DesktopJobCancelledError("Desktop job cancelled")
                if time.monotonic() > deadline:
                    self._reap_process(proc)
                    if out_thread is not None:
                        out_thread.join(timeout=1.0)
                    if err_thread is not None:
                        err_thread.join(timeout=1.0)
                    raise TimeoutError(f"Windows driver timed out after {request.timeout_sec}s")
                cancel_event.wait(0.05)

            wait_fn = getattr(proc, "wait", None)
            if callable(wait_fn):
                try:
                    wait_fn(timeout=2.0)
                except Exception:
                    pass
            if out_thread is not None:
                out_thread.join(timeout=2.0)
            if err_thread is not None:
                err_thread.join(timeout=2.0)

            stdout = "".join(stdout_chunks)
            stderr = "".join(stderr_chunks)
            if proc.returncode != 0:
                raise RuntimeError(stderr.strip() or f"powershell exited with code {proc.returncode}")

            payload: dict[str, Any] = {}
            if out_tmp_path and os.path.exists(out_tmp_path):
                out_file_raw = Path(out_tmp_path).read_text(encoding="utf-8", errors="replace").strip()
                if out_file_raw:
                    payload = json.loads(out_file_raw)
            if not payload:
                payload = json.loads(stdout.strip() or "{}")

            return str(payload.get("text") or ""), {
                "clipboard_restored": bool(payload.get("clipboard_restored", True)),
                "app_path": app_info.get("app_path"),
                "backend": "windows_uia",
            }
        finally:
            for cleanup_path in (tmp_path, out_tmp_path, f"{out_tmp_path}.tmp" if out_tmp_path else None):
                if cleanup_path:
                    try:
                        os.unlink(cleanup_path)
                    except OSError:
                        pass


class LinuxGeminiDriver(BaseDesktopDriver):
    """Linux Chromium/Edge PWA driver with Wayland/X11 headless diagnostics."""

    name: str = "linux_pwa"
    supported_os: tuple[str, ...] = ("linux",)

    @staticmethod
    def _detect_display() -> tuple[str | None, str | None]:
        return os.environ.get("DISPLAY") or None, os.environ.get("WAYLAND_DISPLAY") or None

    @staticmethod
    def _find_clipboard_tools() -> tuple[str | None, str | None, str | None]:
        if shutil.which("wl-copy") and shutil.which("wl-paste"):
            return "wl", shutil.which("wl-copy"), shutil.which("wl-paste")
        if shutil.which("xclip"):
            bin_path = shutil.which("xclip")
            return "xclip", bin_path, bin_path
        if shutil.which("xsel"):
            bin_path = shutil.which("xsel")
            return "xsel", bin_path, bin_path
        return None, None, None

    @staticmethod
    def _find_input_tool() -> tuple[str | None, str | None]:
        for name in ("xdotool", "wtype", "ydotool"):
            found = shutil.which(name)
            if found:
                return name, found
        return None, None

    def discover_app(self, app_path: str | None = None) -> dict[str, Any]:
        explicit = app_path or os.environ.get("GEMINI_APP_PATH")
        if explicit:
            validated = validate_app_path(explicit, "linux")
            p = Path(validated).expanduser()
            which_hit = shutil.which(validated)
            exists = p.is_file() or bool(which_hit)
            eff_path = str(p) if p.is_file() else (which_hit or validated)
            return {
                "app_detected": exists,
                "app_name": p.name if exists else None,
                "app_path": eff_path,
                "bundle_id": "com.google.GeminiLinuxPWA" if exists else None,
                "app_version": None,
                "app_running": False,
                "is_pwa": True,
            }

        desktop_dir = Path.home() / ".local" / "share" / "applications"
        if desktop_dir.exists():
            for df in sorted(desktop_dir.glob("*gemini*.desktop")):
                return {
                    "app_detected": True,
                    "app_name": df.stem,
                    "app_path": str(df),
                    "bundle_id": "com.google.GeminiLinuxPWA",
                    "app_version": None,
                    "app_running": False,
                    "is_pwa": True,
                }

        for browser in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge", "brave-browser"):
            found = shutil.which(browser)
            if found:
                return {
                    "app_detected": True,
                    "app_name": f"Gemini PWA ({browser})",
                    "app_path": found,
                    "bundle_id": f"pwa.{browser}",
                    "app_version": None,
                    "app_running": False,
                    "is_pwa": True,
                }

        return {
            "app_detected": False,
            "app_name": None,
            "app_path": None,
            "bundle_id": None,
            "app_version": None,
            "app_running": False,
            "is_pwa": True,
        }

    def doctor(self, app_path: str | None = None) -> DesktopDriverStatus:
        info = self.discover_app(app_path=app_path)
        x_disp, wayland_disp = self._detect_display()
        has_display = bool(x_disp or wayland_disp)
        clip_kind, _, _ = self._find_clipboard_tools()
        inp_kind, _ = self._find_input_tool()

        warnings: list[str] = []
        remediation: list[str] = []

        if not has_display:
            remediation.append(
                "No X11/Wayland display detected; use --driver mock for headless CI or automated tests."
            )
        if not info["app_detected"]:
            remediation.append(
                "Install google-chrome, chromium, or microsoft-edge to launch Gemini as a standalone PWA (--app=https://gemini.google.com)."
            )
        if not clip_kind:
            remediation.append("Install wl-clipboard (Wayland) or xclip/xsel (X11) for clipboard automation.")
        if not inp_kind:
            remediation.append("Install xdotool (X11) or wtype/ydotool (Wayland) for paste/submit automation.")

        ready = bool(has_display and info["app_detected"] and clip_kind and inp_kind)
        return DesktopDriverStatus(
            os_platform="linux",
            driver_name=self.name,
            ready=ready,
            app_detected=bool(info["app_detected"]),
            app_name=info["app_name"],
            app_path=info["app_path"],
            bundle_id=info["bundle_id"],
            app_version=info["app_version"],
            app_running=bool(info["app_running"]),
            available_backends=(["linux_pwa", "mock"] if ready else ["mock"]),
            permissions={
                "display": "ok" if has_display else "missing",
                "clipboard": clip_kind or "missing",
                "input": inp_kind or "missing",
            },
            warnings=warnings,
            remediation_steps=remediation,
        )

    @staticmethod
    def _read_clipboard(kind: str, paste_bin: str) -> bytes | None:
        cmd = (
            [paste_bin]
            if kind == "wl"
            else ([paste_bin, "-o", "-selection", "clipboard"] if kind == "xclip" else [paste_bin, "-ob"])
        )
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=2.0)
            if res.returncode == 0:
                return res.stdout
        except (OSError, subprocess.SubprocessError):
            pass
        return None

    @staticmethod
    def _write_clipboard(kind: str, copy_bin: str, data: bytes) -> bool:
        cmd = (
            [copy_bin]
            if kind == "wl"
            else ([copy_bin, "-i", "-selection", "clipboard"] if kind == "xclip" else [copy_bin, "-ib"])
        )
        try:
            res = subprocess.run(cmd, input=data, capture_output=True, timeout=3.0)
            return res.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    @staticmethod
    def _clear_clipboard(kind: str, copy_bin: str) -> bool:
        cmd = (
            [copy_bin, "--clear"]
            if kind == "wl"
            else ([copy_bin, "-i", "-selection", "clipboard"] if kind == "xclip" else [copy_bin, "-cb"])
        )
        try:
            res = subprocess.run(
                cmd,
                input=(None if kind in ("wl", "xsel") else b""),
                capture_output=True,
                timeout=3.0,
            )
            return res.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    @staticmethod
    def _send_hotkey(inp_kind: str, inp_bin: str, key_spec: str) -> None:
        if inp_kind == "xdotool":
            subprocess.run([inp_bin, "key", key_spec], capture_output=True, timeout=3.0, check=True)
        elif inp_kind == "wtype":
            if key_spec == "Return":
                subprocess.run([inp_bin, "-k", "Return"], capture_output=True, timeout=3.0, check=True)
            elif key_spec == "ctrl+v":
                subprocess.run([inp_bin, "-M", "ctrl", "-k", "v", "-m", "ctrl"], capture_output=True, timeout=3.0, check=True)
            elif key_spec == "ctrl+shift+c":
                subprocess.run([inp_bin, "-M", "ctrl", "-M", "shift", "-k", "c", "-m", "shift", "-m", "ctrl"], capture_output=True, timeout=3.0, check=True)
        else:
            raise RuntimeError(f"Unsupported Linux input tool: {inp_kind}")

    def execute_prompt(
        self,
        framed_prompt: str,
        job_id: str,
        request: DesktopJobRequest,
        cancel_event: threading.Event,
    ) -> tuple[str, dict[str, Any]]:
        if cancel_event.is_set():
            raise DesktopJobCancelledError("Desktop job cancelled")

        if request.app_path:
            validate_app_path(request.app_path, "linux")

        x_disp, wayland_disp = self._detect_display()
        if not (x_disp or wayland_disp):
            raise RuntimeError("No X11/Wayland display detected; use --driver mock for headless CI")

        info = self.discover_app(app_path=request.app_path)
        if not info["app_detected"] or not info["app_path"]:
            raise RuntimeError("No Chromium/Chrome/Edge PWA browser found on Linux")

        clip_kind, copy_bin, paste_bin = self._find_clipboard_tools()
        inp_kind, inp_bin = self._find_input_tool()
        if not clip_kind or not copy_bin or not paste_bin or not inp_kind or not inp_bin:
            raise RuntimeError("Missing Linux clipboard (wl-clipboard/xclip/xsel) or input (xdotool/wtype) utility")

        if request.new_chat and Path(str(info["app_path"])).suffix != ".desktop":
            subprocess.Popen(
                [str(info["app_path"]), "--app=https://gemini.google.com", "--new-window"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if cancel_event.wait(1.5):
                raise DesktopJobCancelledError("Desktop job cancelled")

        saved_clip = self._read_clipboard(clip_kind, paste_bin) if request.restore_clipboard else None
        clipboard_restored = True
        try:
            if not self._write_clipboard(clip_kind, copy_bin, framed_prompt.encode("utf-8")):
                raise RuntimeError("Failed to write prompt to Linux clipboard")
            self._send_hotkey(inp_kind, inp_bin, "ctrl+v")
            time.sleep(0.25)
        finally:
            if request.restore_clipboard:
                if saved_clip is not None:
                    clipboard_restored = self._write_clipboard(clip_kind, copy_bin, saved_clip)
                else:
                    clipboard_restored = self._clear_clipboard(clip_kind, copy_bin)

        self._send_hotkey(inp_kind, inp_bin, "Return")

        deadline = time.monotonic() + max(1, int(request.timeout_sec))
        poll_sec = max(0.2, int(request.poll_interval_ms) / 1000.0)
        last_len: int | None = None
        stable_since: float | None = None
        captured_text = ""

        while True:
            if cancel_event.is_set():
                raise DesktopJobCancelledError("Desktop job cancelled")
            if time.monotonic() > deadline:
                raise TimeoutError(f"Timed out after {request.timeout_sec}s waiting for Gemini PWA response")

            copy_saved = self._read_clipboard(clip_kind, paste_bin) if request.restore_clipboard else None
            try:
                self._send_hotkey(inp_kind, inp_bin, "ctrl+shift+c")
                time.sleep(0.2)
                raw_bytes = self._read_clipboard(clip_kind, paste_bin)
                candidate = raw_bytes.decode("utf-8", errors="replace") if raw_bytes else ""
            finally:
                if request.restore_clipboard:
                    if copy_saved is not None:
                        clipboard_restored = self._write_clipboard(clip_kind, copy_bin, copy_saved) and clipboard_restored
                    else:
                        clipboard_restored = self._clear_clipboard(clip_kind, copy_bin) and clipboard_restored

            if SentinelEnvelope.has_complete_sentinel(candidate, job_id):
                cur_len = len(candidate)
                if last_len is not None and cur_len == last_len:
                    if stable_since is not None and (time.monotonic() - stable_since) * 1000.0 >= DEFAULT_STABILITY_DEBOUNCE_MS:
                        captured_text = candidate
                        break
                else:
                    last_len = cur_len
                    stable_since = time.monotonic()
            else:
                last_len = None
                stable_since = None

            if cancel_event.wait(poll_sec):
                raise DesktopJobCancelledError("Desktop job cancelled")

        return captured_text, {
            "clipboard_restored": clipboard_restored,
            "app_path": info["app_path"],
            "backend": "linux_pwa",
        }


class MockGeminiDriver(BaseDesktopDriver):
    """Deterministic zero-GUI simulator for CI, dry-runs, and unit tests."""

    name: str = "mock"
    supported_os: tuple[str, ...] = ("darwin", "win32", "linux")

    def __init__(self, os_platform: str | None = None) -> None:
        self._os_platform = os_platform or _normalize_os("auto")

    def discover_app(self, app_path: str | None = None) -> dict[str, Any]:
        return {
            "app_detected": True,
            "app_name": "Gemini (Mock Simulator)",
            "app_path": app_path or "/mock/Applications/Gemini.app",
            "bundle_id": "com.google.GeminiMacOS.mock",
            "app_version": "1.0.0-mock",
            "url_schemes": ["googlegemini"],
            "min_os_version": "15.0",
            "app_running": True,
            "is_pwa": False,
        }

    def doctor(self, app_path: str | None = None) -> DesktopDriverStatus:
        info = self.discover_app(app_path=app_path)
        return DesktopDriverStatus(
            os_platform=self._os_platform,
            driver_name=self.name,
            ready=True,
            app_detected=True,
            app_name=info["app_name"],
            app_path=info["app_path"],
            bundle_id=info["bundle_id"],
            app_version=info["app_version"],
            app_running=True,
            available_backends=["mock"],
            permissions={"accessibility": "mock", "clipboard": "mock"},
            warnings=[],
            remediation_steps=[],
        )

    def execute_prompt(
        self,
        framed_prompt: str,
        job_id: str,
        request: DesktopJobRequest,
        cancel_event: threading.Event,
    ) -> tuple[str, dict[str, Any]]:
        delay_ms = max(0, int(os.environ.get("MOCK_DELAY_MS", "50")))
        deadline = time.monotonic() + (delay_ms / 1000.0)
        while time.monotonic() < deadline:
            if cancel_event.is_set():
                raise DesktopJobCancelledError("Mock desktop job cancelled")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            if cancel_event.wait(min(0.01, remaining)):
                raise DesktopJobCancelledError("Mock desktop job cancelled")

        if cancel_event.is_set():
            raise DesktopJobCancelledError("Mock desktop job cancelled")

        if "[MOCK_TIMEOUT]" in framed_prompt:
            raise TimeoutError("Mock Gemini Desktop timeout simulated")
        if "[MOCK_ERROR]" in framed_prompt:
            raise RuntimeError("Mock Gemini Desktop error simulated")

        ctx_idx = framed_prompt.rfind(SentinelEnvelope.PROMPT_BOUNDARY)
        user_ctx = (
            framed_prompt[ctx_idx + len(SentinelEnvelope.PROMPT_BOUNDARY) :].strip()
            if ctx_idx != -1
            else framed_prompt.strip()
        )
        preview = " ".join(user_ctx.splitlines())[:160]

        start_tok = SentinelEnvelope.start_marker(job_id)
        done_tok = SentinelEnvelope.done_marker(job_id)

        if "[MOCK_PARTIAL]" in framed_prompt:
            raw = (
                f"{start_tok}\n"
                "## Executive Summary\n"
                f"Partial simulated response for `{job_id}` without end marker.\n"
            )
            return raw, {"clipboard_restored": True, "mock": True}

        body = (
            "## Executive Summary\n"
            f"Simulated deterministic synthesis for job `{job_id}`.\n\n"
            "## Key Findings\n"
            f"- Analyzed context excerpt: `{preview}`\n"
            "- Zero AGY API tokens consumed ($0.00 marginal API cost).\n\n"
            "## Risks & Edge Cases\n"
            "- Simulated via `MockGeminiDriver`; verify against live desktop GUI before production rollout.\n\n"
            "## Actionable Recommendations\n"
            "- Review generated Markdown artifact and route mutations to `gemini-4-hydrogen`."
        )

        if "[MOCK_CHROME]" in framed_prompt:
            raw = (
                "Show thinking\n"
                "Gemini said\n"
                f"{start_tok}\n"
                "Show thinking\n"
                "Gemini said\n"
                f"{body}\n"
                "Copy\n"
                "Export to Docs\n"
                f"{done_tok}\n"
                "Send feedback\n"
            )
        else:
            raw = f"{start_tok}\n{body}\n{done_tok}\n"

        return raw, {"clipboard_restored": True, "mock": True}


# ---------------------------------------------------------------------------
# Driver Registry & Environment Detection
# ---------------------------------------------------------------------------

def get_desktop_driver(driver: str = "auto", target_os: str = "auto") -> BaseDesktopDriver:
    """Resolve driver implementation from explicit driver name, env override, and OS."""
    raw_driver = (driver or "auto").strip().lower()
    if raw_driver == "auto":
        env_driver = os.environ.get("GEMINI_DESKTOP_DRIVER", "").strip().lower()
        if env_driver:
            raw_driver = env_driver

    if raw_driver not in SUPPORTED_DRIVERS:
        raise ValueError(f"Unsupported desktop driver: {driver!r}")

    eff_os = _normalize_os(target_os)

    if raw_driver == "mock":
        return MockGeminiDriver(os_platform=eff_os)
    if raw_driver == "macos_ax":
        return MacOSGeminiDriver(prefer_orca=False)
    if raw_driver == "orca":
        return MacOSGeminiDriver(prefer_orca=True)
    if raw_driver == "windows_uia":
        return WindowsGeminiDriver()
    if raw_driver == "linux_pwa":
        return LinuxGeminiDriver()

    # Auto selection by target OS.
    if eff_os == "darwin":
        return MacOSGeminiDriver(prefer_orca=(os.environ.get("GEMINI_PREFER_ORCA") == "1"))
    if eff_os == "win32":
        return WindowsGeminiDriver()
    if eff_os == "linux":
        return LinuxGeminiDriver()
    return MockGeminiDriver(os_platform=eff_os)


def detect_desktop_environment(
    driver: str = "auto",
    target_os: str = "auto",
    app_path: str | None = None,
) -> DesktopDriverStatus:
    """Run non-intrusive pre-flight discovery & readiness diagnostics."""
    drv = get_desktop_driver(driver=driver, target_os=target_os)
    return drv.doctor(app_path=app_path)


# ---------------------------------------------------------------------------
# Artifact Writer (Path Traversal Guard + Context Minimization)
# ---------------------------------------------------------------------------

def write_desktop_artifact(
    job_id: str,
    clean_markdown: str,
    request: DesktopJobRequest,
    driver_used: str,
    os_platform: str,
    duration_ms: int,
    redactions: dict[str, int],
    estimated_saved_usd: float,
    output_dir: str | Path | None = None,
    reports_root: str | Path | None = None,
    workspace_root: str | Path | None = None,
) -> str:
    """Persist structured Markdown output inside docs/reports/ (defaulting to docs/reports/desktop_worker/{job_id}.md) safely."""
    if not VALID_JOB_ID_RE.match(job_id):
        raise ValueError(f"Invalid job_id for artifact write: {job_id!r}")

    cwd = Path(os.path.realpath(str(Path.cwd())))
    ws_root = Path(os.path.realpath(str(workspace_root))) if workspace_root is not None else cwd
    default_reports_root = Path(os.path.realpath(str(ws_root / "docs" / "reports")))
    default_worker_dir = Path(os.path.realpath(str(default_reports_root / "desktop_worker")))

    if reports_root is not None:
        allowed_root = Path(os.path.realpath(str(reports_root)))
    elif output_dir is not None:
        allowed_root = Path(os.path.realpath(str(output_dir)))
    else:
        allowed_root = default_reports_root

    default_dir = (
        Path(os.path.realpath(str(output_dir)))
        if output_dir is not None
        else default_worker_dir
    )

    if request.output_path:
        raw_str = str(request.output_path).strip()
        if "\x00" in raw_str:
            raise ValueError("Invalid output_path: null byte is not allowed")
        raw_out = Path(raw_str).expanduser()
        if raw_out.is_absolute():
            target_path = Path(os.path.realpath(str(raw_out)))
        else:
            if (
                workspace_root is not None
                and len(raw_out.parts) >= 2
                and raw_out.parts[0] == "docs"
                and raw_out.parts[1] == "reports"
            ):
                base = ws_root
            elif (
                reports_root is None
                and output_dir is None
                and len(raw_out.parts) >= 2
                and raw_out.parts[0] == "docs"
                and raw_out.parts[1] == "reports"
            ):
                base = cwd
            elif (
                allowed_root.name == "reports"
                and allowed_root.parent.name == "docs"
                and len(raw_out.parts) >= 2
                and raw_out.parts[0] == "docs"
                and raw_out.parts[1] == "reports"
            ):
                base = allowed_root.parent.parent
            else:
                base = allowed_root
            target_path = Path(os.path.realpath(str(base / raw_out)))

        if not target_path.is_relative_to(allowed_root) or target_path == allowed_root:
            raise ValueError(
                f"Path traversal rejected: output_path {request.output_path!r} escapes allowed root {str(allowed_root)!r}"
            )
        if target_path.suffix.lower() not in ALLOWED_ARTIFACT_EXTENSIONS:
            raise ValueError(
                f"Invalid output_path extension {target_path.suffix!r}: must be one of {', '.join(sorted(ALLOWED_ARTIFACT_EXTENSIONS))}"
            )
        if target_path.exists() and target_path.is_dir():
            raise ValueError(f"Invalid output_path {request.output_path!r}: target cannot be a directory")
    else:
        target_path = Path(os.path.realpath(str(default_dir / f"{job_id}.md")))
        if not target_path.is_relative_to(allowed_root):
            raise ValueError("Invalid artifact path resolution")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    utc_now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    header = "\n".join([
        "---",
        f"job_id: {job_id}",
        f"task_id: {request.task_id or 'none'}",
        f"driver: {driver_used}",
        f"os_platform: {os_platform}",
        f"duration_ms: {int(duration_ms)}",
        f"redactions: {json.dumps(redactions, sort_keys=True)}",
        f"estimated_saved_usd: {estimated_saved_usd:.4f}",
        f"generated_at: {utc_now}",
        "---",
        "",
    ])
    content = f"{header}{clean_markdown.rstrip()}\n"
    target_path.write_text(content, encoding="utf-8")

    if target_path.is_relative_to(cwd):
        return target_path.relative_to(cwd).as_posix()
    return str(target_path)


# ---------------------------------------------------------------------------
# Thread-Safe & Cross-Process Locked Worker Manager
# ---------------------------------------------------------------------------

class DesktopWorkerManager:
    """Coordinates sequential single-window GUI execution, secret scrubbing, and artifact generation."""

    @staticmethod
    def _default_lock_path() -> Path:
        if os.name != "nt":
            xdg_rt = os.environ.get("XDG_RUNTIME_DIR", "").strip()
            if xdg_rt:
                p = Path(xdg_rt)
                if p.is_dir() and os.access(p, os.W_OK):
                    return (p / "agy_desktop_worker.lock").resolve()
            home_gemini = Path.home() / ".gemini"
            if (home_gemini.is_dir() and os.access(home_gemini, os.W_OK)) or (
                not home_gemini.exists() and os.access(Path.home(), os.W_OK)
            ):
                return (home_gemini / "agy_desktop_worker.lock").resolve()
        return (Path(tempfile.gettempdir()) / "agy_desktop_worker.lock").resolve()

    def __init__(
        self,
        artifacts_dir: str | Path | None = None,
        lock_path: str | Path | None = None,
        reports_root: str | Path | None = None,
        workspace_root: str | Path | None = None,
    ) -> None:
        self._thread_lock = threading.Lock()
        cwd = Path.cwd().resolve()
        self._workspace_root = (
            Path(os.path.realpath(str(workspace_root)))
            if workspace_root is not None
            else cwd
        )
        if reports_root is not None:
            self._reports_root = Path(os.path.realpath(str(reports_root)))
        elif artifacts_dir is not None:
            self._reports_root = Path(os.path.realpath(str(artifacts_dir)))
        else:
            self._reports_root = Path(os.path.realpath(str(self._workspace_root / "docs" / "reports")))

        if artifacts_dir is not None:
            self._artifacts_dir = Path(os.path.realpath(str(artifacts_dir)))
        else:
            self._artifacts_dir = Path(os.path.realpath(str(self._reports_root / "desktop_worker")))

        self._lock_path = (
            Path(lock_path).resolve()
            if lock_path is not None
            else self._default_lock_path()
        )

    @contextmanager
    def _acquire_locks(self, cancel_event: threading.Event) -> Iterator[None]:
        while not self._thread_lock.acquire(timeout=0.05):
            if cancel_event.is_set():
                raise DesktopJobCancelledError("Job cancelled while waiting for worker lock")

        lock_fh = None
        locked_file = False
        try:
            self._lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_fh = self._lock_path.open("a+", encoding="utf-8")
            while True:
                if cancel_event.is_set():
                    raise DesktopJobCancelledError("Job cancelled while waiting for file lock")
                try:
                    if os.name == "nt":
                        lock_fh.seek(0)
                        msvcrt.locking(lock_fh.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked_file = True
                    break
                except OSError:
                    if cancel_event.wait(0.05):
                        raise DesktopJobCancelledError("Job cancelled while waiting for file lock")
            yield
        finally:
            if lock_fh is not None:
                if locked_file:
                    try:
                        if os.name == "nt":
                            lock_fh.seek(0)
                            msvcrt.locking(lock_fh.fileno(), msvcrt.LK_UNLCK, 1)
                        else:
                            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
                    except OSError:
                        pass
                try:
                    lock_fh.close()
                except OSError:
                    pass
            self._thread_lock.release()

    def is_lock_busy(self) -> bool:
        if not self._thread_lock.acquire(blocking=False):
            return True
        try:
            if not self._lock_path.exists():
                return False
            with self._lock_path.open("a+", encoding="utf-8") as fh:
                if os.name == "nt":
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            return False
        except OSError:
            return True
        finally:
            self._thread_lock.release()

    def get_status(
        self,
        driver: str = "auto",
        target_os: str = "auto",
        app_path: str | None = None,
        queue_depth: int = 0,
    ) -> DesktopDriverStatus:
        status = detect_desktop_environment(driver=driver, target_os=target_os, app_path=app_path)
        status.queue_depth = max(0, int(queue_depth))
        status.lock_busy = self.is_lock_busy()
        return status

    def execute_job(
        self,
        request: DesktopJobRequest,
        cancel_event: threading.Event | None = None,
    ) -> DesktopJobResult:
        cancel = cancel_event or threading.Event()
        start_ts = time.monotonic()

        try:
            drv = get_desktop_driver(driver=request.driver, target_os=request.target_os)
            eff_os = _normalize_os(request.target_os)
        except ValueError as exc:
            return DesktopJobResult(
                job_id=request.job_id,
                status="failed",
                driver_used=str(request.driver or "auto"),
                os_platform=_normalize_os("auto"),
                clipboard_restored=True,
                error=str(exc),
            )

        if not VALID_JOB_ID_RE.match(request.job_id):
            return DesktopJobResult(
                job_id=request.job_id,
                status="failed",
                driver_used=drv.name,
                os_platform=eff_os,
                clipboard_restored=True,
                error=f"Invalid job_id format: {request.job_id!r}",
            )

        if not request.prompt or not request.prompt.strip():
            return DesktopJobResult(
                job_id=request.job_id,
                status="failed",
                driver_used=drv.name,
                os_platform=eff_os,
                clipboard_restored=True,
                error="Prompt must not be empty",
            )

        if len(request.prompt) > DEFAULT_MAX_PROMPT_CHARS:
            return DesktopJobResult(
                job_id=request.job_id,
                status="failed",
                driver_used=drv.name,
                os_platform=eff_os,
                clipboard_restored=True,
                error=f"Prompt exceeds maximum length ({len(request.prompt)} > {DEFAULT_MAX_PROMPT_CHARS} chars)",
            )

        if cancel.is_set():
            return DesktopJobResult(
                job_id=request.job_id,
                status="cancelled",
                driver_used=drv.name,
                os_platform=eff_os,
                clipboard_restored=True,
                error="Desktop job cancelled before execution",
            )

        try:
            clean_prompt, redactions, _ = redact_secrets(
                request.prompt,
                strict=request.strict_secrets,
                redact=request.redact_secrets,
                raise_on_strict=True,
            )
        except SecretRedactionError as exc:
            duration_ms = int((time.monotonic() - start_ts) * 1000)
            return DesktopJobResult(
                job_id=request.job_id,
                status="rejected_secrets",
                driver_used=drv.name,
                os_platform=eff_os,
                duration_ms=duration_ms,
                redactions=exc.redactions,
                clipboard_restored=True,
                error=str(exc),
            )

        framed_prompt = SentinelEnvelope.build_prompt(
            request.job_id,
            clean_prompt,
            metadata=request.metadata,
        )

        clipboard_restored = True
        try:
            with self._acquire_locks(cancel):
                if cancel.is_set():
                    raise DesktopJobCancelledError("Desktop job cancelled")
                raw_text, meta = drv.execute_prompt(framed_prompt, request.job_id, request, cancel)
                clipboard_restored = bool(meta.get("clipboard_restored", True))
        except DesktopJobCancelledError as exc:
            duration_ms = int((time.monotonic() - start_ts) * 1000)
            return DesktopJobResult(
                job_id=request.job_id,
                status="cancelled",
                driver_used=drv.name,
                os_platform=eff_os,
                duration_ms=duration_ms,
                redactions=redactions,
                clipboard_restored=clipboard_restored,
                error=str(exc),
            )
        except TimeoutError as exc:
            duration_ms = int((time.monotonic() - start_ts) * 1000)
            return DesktopJobResult(
                job_id=request.job_id,
                status="timed_out",
                driver_used=drv.name,
                os_platform=eff_os,
                duration_ms=duration_ms,
                redactions=redactions,
                clipboard_restored=clipboard_restored,
                error=str(exc),
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - start_ts) * 1000)
            return DesktopJobResult(
                job_id=request.job_id,
                status="failed",
                driver_used=drv.name,
                os_platform=eff_os,
                duration_ms=duration_ms,
                redactions=redactions,
                clipboard_restored=clipboard_restored,
                error=str(exc),
            )

        duration_ms = int((time.monotonic() - start_ts) * 1000)
        clean_md, sentinel_ok = SentinelEnvelope.extract_response(raw_text, request.job_id)
        saved_usd, saved_vnd = _compute_saved_quota(len(clean_prompt), len(clean_md))
        summary = _build_summary_excerpt(clean_md)

        artifact_path: str | None = None
        if clean_md:
            try:
                artifact_path = write_desktop_artifact(
                    job_id=request.job_id,
                    clean_markdown=clean_md,
                    request=request,
                    driver_used=drv.name,
                    os_platform=eff_os,
                    duration_ms=duration_ms,
                    redactions=redactions,
                    estimated_saved_usd=saved_usd,
                    output_dir=self._artifacts_dir,
                    reports_root=self._reports_root,
                    workspace_root=self._workspace_root,
                )
            except ValueError as exc:
                return DesktopJobResult(
                    job_id=request.job_id,
                    status="failed",
                    driver_used=drv.name,
                    os_platform=eff_os,
                    summary_excerpt=summary,
                    raw_char_count=len(raw_text),
                    duration_ms=duration_ms,
                    redactions=redactions,
                    clipboard_restored=clipboard_restored,
                    error=str(exc),
                )

        if not sentinel_ok:
            return DesktopJobResult(
                job_id=request.job_id,
                status="failed",
                driver_used=drv.name,
                os_platform=eff_os,
                artifact_path=artifact_path,
                summary_excerpt=summary,
                raw_char_count=len(raw_text),
                duration_ms=duration_ms,
                redactions=redactions,
                estimated_saved_usd=0.0,
                estimated_saved_vnd=0,
                clipboard_restored=clipboard_restored,
                error="Completion sentinel missing; response may be truncated",
            )

        return DesktopJobResult(
            job_id=request.job_id,
            status="completed",
            driver_used=drv.name,
            os_platform=eff_os,
            artifact_path=artifact_path,
            summary_excerpt=summary,
            raw_char_count=len(raw_text),
            duration_ms=duration_ms,
            redactions=redactions,
            estimated_saved_usd=saved_usd,
            estimated_saved_vnd=saved_vnd,
            clipboard_restored=clipboard_restored,
            error=None,
        )


# ---------------------------------------------------------------------------
# Standalone CLI (`doctor` & `ask`)
# ---------------------------------------------------------------------------

def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cross-Platform Gemini Desktop App Worker CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_doc = sub.add_parser("doctor", help="Inspect OS, Gemini Desktop App, and permissions")
    p_doc.add_argument("--driver", default="auto", choices=SUPPORTED_DRIVERS)
    p_doc.add_argument("--target-os", default="auto")
    p_doc.add_argument("--app-path", default=None)
    p_doc.add_argument("--json", action="store_true", help="Output JSON diagnostics")

    p_ask = sub.add_parser("ask", help="Execute a bounded prompt via Gemini Desktop Worker")
    p_ask.add_argument("--prompt", default=None, help="Inline prompt text")
    p_ask.add_argument("--prompt-file", default=None, help="Path to UTF-8 prompt file")
    p_ask.add_argument("--driver", default="auto", choices=SUPPORTED_DRIVERS)
    p_ask.add_argument("--target-os", default="auto")
    p_ask.add_argument("--app-path", default=None)
    p_ask.add_argument("--task-id", default=None)
    p_ask.add_argument("--job-id", default=None)
    p_ask.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SEC)
    p_ask.add_argument("--output", default=None, help="Output Markdown path inside docs/reports/")
    p_ask.add_argument("--no-redact", action="store_true", help="Disable secret redaction")
    p_ask.add_argument("--strict-secrets", action="store_true", help="Reject prompt if secrets detected")
    p_ask.add_argument("--no-restore-clipboard", action="store_true", help="Do not restore prior clipboard")
    p_ask.add_argument("--no-new-chat", action="store_true", help="Reuse active chat window")
    p_ask.add_argument("--json", action="store_true", help="Output JSON job result")

    return parser


def _print_doctor_text(status: DesktopDriverStatus) -> None:
    print(f"OS Platform      : {status.os_platform}")
    print(f"Driver           : {status.driver_name}")
    print(f"Ready            : {status.ready}")
    print(f"App Detected     : {status.app_detected}")
    if status.app_name:
        print(f"App Name         : {status.app_name}")
    if status.app_path:
        print(f"App Path         : {status.app_path}")
    if status.bundle_id:
        print(f"Bundle ID        : {status.bundle_id}")
    if status.app_version:
        print(f"App Version      : {status.app_version}")
    print(f"App Running      : {status.app_running}")
    print(f"Backends         : {', '.join(status.available_backends)}")
    print(f"Permissions      : {json.dumps(status.permissions)}")
    print(f"Lock Busy        : {status.lock_busy}")
    if status.warnings:
        print("Warnings:")
        for w in status.warnings:
            print(f"  - {w}")
    if status.remediation_steps:
        print("Remediation:")
        for step in status.remediation_steps:
            print(f"  - {step}")


def main(argv: list[str] | None = None) -> int:
    parser = _build_cli_parser()
    args = parser.parse_args(argv)
    manager = DesktopWorkerManager()

    if args.command == "doctor":
        status = manager.get_status(
            driver=args.driver,
            target_os=args.target_os,
            app_path=args.app_path,
        )
        if args.json:
            print(json.dumps(status.to_dict(), indent=2))
        else:
            _print_doctor_text(status)
        return 0

    if args.command == "ask":
        prompt_text = args.prompt
        if args.prompt_file:
            prompt_text = Path(args.prompt_file).read_text(encoding="utf-8")
        if not prompt_text:
            err = {"error": "Provide --prompt or --prompt-file"}
            print(json.dumps(err) if args.json else err["error"], file=sys.stderr)
            return 2

        req = DesktopJobRequest(
            job_id=args.job_id or generate_job_id(),
            prompt=prompt_text,
            task_id=args.task_id,
            driver=args.driver,
            target_os=args.target_os,
            app_path=args.app_path,
            timeout_sec=args.timeout,
            output_path=args.output,
            redact_secrets=not args.no_redact,
            strict_secrets=args.strict_secrets,
            restore_clipboard=not args.no_restore_clipboard,
            new_chat=not args.no_new_chat,
        )
        res = manager.execute_job(req)
        if args.json:
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(f"Job ID       : {res.job_id}")
            print(f"Status       : {res.status}")
            print(f"Driver       : {res.driver_used} ({res.os_platform})")
            print(f"Duration     : {res.duration_ms} ms")
            print(f"Saved Quota  : ${res.estimated_saved_usd:.4f} (~{res.estimated_saved_vnd} VND)")
            if res.artifact_path:
                print(f"Artifact     : {res.artifact_path}")
            if res.summary_excerpt:
                print(f"Excerpt      : {res.summary_excerpt}")
            if res.error:
                print(f"Error        : {res.error}")
        return 0 if res.status == "completed" else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
