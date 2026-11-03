#Requires -Version 5.1
<#
.SYNOPSIS
    Installs the devin-agentic orchestration system into %APPDATA%\devin\.

.DESCRIPTION
    Idempotent installer. Copies agents/, skills/, hooks/ and AGENTS.md into
    the Devin CLI user directory, then merges the managed keys (permissions,
    hooks) from config.managed.json into config.json — preserving everything
    else (org_id, credentials, model prefs, theme).

    Re-run anytime after `git pull` to apply updates.

.PARAMETER SetBypass
    Also sets DEVIN_PERMISSION_MODE=dangerous as a user env var so every
    session runs in bypass mode by default.

.EXAMPLE
    .\install.ps1
    .\install.ps1 -SetBypass
#>
param(
    [switch]$SetBypass
)

$ErrorActionPreference = 'Stop'
$RepoRoot = $PSScriptRoot
$DevinHome = Join-Path $env:APPDATA 'devin'
$DevinExe = Join-Path $env:LOCALAPPDATA 'devin\cli\bin\devin.exe'

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

# --- 0. sanity -------------------------------------------------------------
Step 'Checking Devin CLI'
if (-not (Test-Path $DevinExe)) {
    Write-Warning "Devin CLI not found at $DevinExe — install it first (https://docs.devin.ai/cli). Continuing anyway (config will land but nothing will consume it)."
}
New-Item -ItemType Directory -Force $DevinHome | Out-Null

# --- 1. copy pieces ---------------------------------------------------------
Step "Copying files -> $DevinHome"
foreach ($d in 'agents', 'skills', 'hooks') {
    Copy-Item "$RepoRoot\$d" $DevinHome -Recurse -Force
    Write-Host "  + $d\"
}

$agentsTarget = Join-Path $DevinHome 'AGENTS.md'
if (Test-Path $agentsTarget) {
    $bak = "$agentsTarget.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $agentsTarget $bak
    Write-Host "  ! existing AGENTS.md backed up -> $(Split-Path $bak -Leaf)"
}
Copy-Item "$RepoRoot\AGENTS.md" $agentsTarget -Force
Write-Host "  + AGENTS.md"

# --- 2. merge managed config ------------------------------------------------
Step 'Merging config.json'
$cfgPath = Join-Path $DevinHome 'config.json'
$managed = Get-Content "$RepoRoot\config.managed.json" -Raw | ConvertFrom-Json

if (Test-Path $cfgPath) {
    $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
    $cfgBak = "$cfgPath.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item $cfgPath $cfgBak
    Write-Host "  ! existing config.json backed up -> $(Split-Path $cfgBak -Leaf)"
} else {
    $cfg = [PSCustomObject]@{ version = 1 }
}

# Managed keys are replaced wholesale; everything else is preserved.
$cfg | Add-Member -NotePropertyName permissions -NotePropertyValue $managed.permissions -Force
$cfg | Add-Member -NotePropertyName hooks -NotePropertyValue $managed.hooks -Force
$cfg | ConvertTo-Json -Depth 10 | Set-Content $cfgPath -Encoding UTF8
Write-Host '  + permissions, hooks merged (other keys untouched)'

# --- 3. optional bypass mode --------------------------------------------------
if ($SetBypass) {
    Step 'Setting DEVIN_PERMISSION_MODE=dangerous (user env)'
    [Environment]::SetEnvironmentVariable('DEVIN_PERMISSION_MODE', 'dangerous', 'User')
    Write-Host '  + every new session defaults to bypass. Undo: install.ps1 docs or remove the env var.'
}

# --- 4. verify ------------------------------------------------------------------
Step 'Verifying'
if (Test-Path $DevinExe) {
    & $DevinExe doctor 2>&1 | Select-Object -First 6
} else {
    Write-Host '  (skipped — devin.exe not found)'
}

Write-Host "`nDone. System installed at $DevinHome" -ForegroundColor Green
Write-Host 'Try it: devin -> /orchestrate, or "use the scout subagent to map this codebase"'
