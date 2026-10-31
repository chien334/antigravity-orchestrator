<#
.SYNOPSIS
  Multi-Agent Orchestrator & Antigravity CLI Installer for Windows (PowerShell)
#>
[CmdletBinding()]
param (
    [string]$TargetDir = ""
)

$ErrorActionPreference = "Stop"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Multi-Agent Orchestrator & Antigravity CLI Installer (Win)    " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check & Install Antigravity CLI
Write-Host "[1/5] Checking Antigravity CLI (agy)..." -ForegroundColor Yellow
if (Get-Command agy -ErrorAction SilentlyContinue) {
    $ver = agy --version
    Write-Host "[OK] Antigravity CLI (agy) is already installed: $ver" -ForegroundColor Green
} else {
    Write-Host "[!] agy not found. Downloading via official installer..." -ForegroundColor Yellow
    try {
        irm https://antigravity.google/cli/install.ps1 | iex
        Write-Host "[OK] Antigravity CLI installed successfully." -ForegroundColor Green
    } catch {
        Write-Warning "Failed to auto-install agy. Please visit docs/ANTIGRAVITY_CLI_SETUP.md for manual install instructions."
    }
}

# 2. Check Python Environment
Write-Host ""
Write-Host "[2/5] Checking Python Environment..." -ForegroundColor Yellow
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python 3 is required. Please install Python 3.8+ from python.org or Microsoft Store."
    exit 1
}
$pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "[OK] Python detected: version $pyVer" -ForegroundColor Green

# 3. Install Global Configurations
Write-Host ""
Write-Host "[3/5] Installing Global Antigravity Skills & Workflows..." -ForegroundColor Yellow
$userHome = $env:USERPROFILE
$globalConfig = Join-Path $userHome ".gemini\config"
$globalCommands = Join-Path $userHome ".gemini\commands"
$scriptRoot = $PSScriptRoot

New-Item -ItemType Directory -Force -Path (Join-Path $globalConfig "workflows") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $globalConfig "global_workflows") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $globalConfig "skills") | Out-Null
New-Item -ItemType Directory -Force -Path $globalCommands | Out-Null

# Copy all skills from packages/skills
Get-ChildItem -Directory -Path "$scriptRoot\packages\skills" | ForEach-Object {
    $sTarget = Join-Path $globalConfig "skills\$($_.Name)"
    New-Item -ItemType Directory -Force -Path $sTarget | Out-Null
    Copy-Item -Path "$($_.FullName)\*" -Destination $sTarget -Recurse -Force
}
$skillCount = (Get-ChildItem -Directory -Path "$scriptRoot\packages\skills").Count
Write-Host "    -> Installed $skillCount Agent Skills into: $globalConfig\skills" -ForegroundColor Green

Get-ChildItem -Path "$scriptRoot\packages\workflows\*.md" | ForEach-Object {
    Copy-Item -Path $_.FullName -Destination "$globalConfig\workflows\" -Force
    Copy-Item -Path $_.FullName -Destination "$globalConfig\global_workflows\" -Force
}
Copy-Item -Path "$scriptRoot\packages\commands\orchestrator.toml" -Destination "$globalCommands\orchestrator.toml" -Force
Write-Host "[OK] Global configurations installed." -ForegroundColor Green

# 4. Optional: Project Workspace Installation
if ($TargetDir -ne "") {
    Write-Host ""
    Write-Host "[4/5] Installing into workspace: $TargetDir" -ForegroundColor Yellow
    $dest = Resolve-Path $TargetDir
    New-Item -ItemType Directory -Force -Path "$dest\.agents\skills" | Out-Null
    New-Item -ItemType Directory -Force -Path "$dest\.agents\workflows" | Out-Null
    New-Item -ItemType Directory -Force -Path "$dest\.gemini\commands" | Out-Null
    New-Item -ItemType Directory -Force -Path "$dest\tools\orchestrator" | Out-Null
    New-Item -ItemType Directory -Force -Path "$dest\docs\specs" | Out-Null
    New-Item -ItemType Directory -Force -Path "$dest\docs\plans" | Out-Null
    New-Item -ItemType Directory -Force -Path "$dest\docs\reports" | Out-Null
    New-Item -ItemType Directory -Force -Path "$dest\docs\reviews" | Out-Null
    New-Item -ItemType Directory -Force -Path "$dest\docs\security" | Out-Null

    Get-ChildItem -Directory -Path "$scriptRoot\packages\skills" | ForEach-Object {
        $wsTarget = Join-Path $dest ".agents\skills\$($_.Name)"
        New-Item -ItemType Directory -Force -Path $wsTarget | Out-Null
        Copy-Item -Path "$($_.FullName)\*" -Destination $wsTarget -Recurse -Force
    }
    Copy-Item -Path "$scriptRoot\packages\workflows\*.md" -Destination "$dest\.agents\workflows\" -Force
    Copy-Item -Path "$scriptRoot\packages\commands\orchestrator.toml" -Destination "$dest\.gemini\commands\" -Force
    Copy-Item -Path "$scriptRoot\packages\orchestrator\*.py" -Destination "$dest\tools\orchestrator\" -Force
    Write-Host "[OK] Workspace initialized at $dest with $skillCount skills" -ForegroundColor Green
}

# 5. Run Verification Suite
Write-Host ""
Write-Host "[5/5] Running Self-Test Verification Suite..." -ForegroundColor Yellow
$env:PYTHONPATH = "$scriptRoot\packages;$scriptRoot\packages\orchestrator;$env:PYTHONPATH"
python "$scriptRoot\tests\test_orchestrator.py"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  INSTALLATION COMPLETED SUCCESSFULLY!                          " -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host "Start Dashboard: python packages/orchestrator/server.py --port 8484"
Write-Host "In Antigravity chat: type /orchestrator"
