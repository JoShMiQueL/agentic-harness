#Requires -Version 5.1
<#
.SYNOPSIS
    Installs the devin-agentic orchestration system into %APPDATA%\devin\.

.DESCRIPTION
    Idempotent installer / remote bootstrap.

    - Run from a cloned repo:  .\install.ps1
    - Run remote (one-liner):  irm https://raw.githubusercontent.com/JoShMiQueL/devin-agentic/main/install.ps1 | iex

    When executed via irm|iex the script downloads the full file set from the
    repo first, then installs. Copies agents/, skills/, hooks/ and AGENTS.md
    into the Devin CLI user directory, then merges the managed keys
    (permissions, hooks) from config.managed.json into config.json —
    preserving everything else (org_id, credentials, model prefs, theme).

    Re-run anytime to apply updates.

.PARAMETER SetBypass
    Also sets DEVIN_PERMISSION_MODE=dangerous as a user env var so every
    session runs in bypass mode by default.

.EXAMPLE
    .\install.ps1
    .\install.ps1 -SetBypass
#>
param(
    [switch]$SetBypass,
    [string]$Branch = 'main'
)

$ErrorActionPreference = 'Stop'
$RepoUrl = "https://raw.githubusercontent.com/JoShMiQueL/devin-agentic/$Branch"
$DevinHome = Join-Path $env:APPDATA 'devin'
$DevinExe = Join-Path $env:LOCALAPPDATA 'devin\cli\bin\devin.exe'

# Files that make up the system (relative paths inside the repo).
$Manifest = @(
    'AGENTS.md',
    'config.managed.json',
    'agents/scout.md',
    'agents/tester.md',
    'agents/reviewer.md',
    'agents/worker.md',
    'skills/orchestrate/SKILL.md',
    'hooks/pre-tool-guard.ps1',
    'hooks/session-start-memory.ps1'
)

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

# --- 0. source files: local clone or remote bootstrap -----------------------
$RepoRoot = $PSScriptRoot
if (-not (Test-Path (Join-Path $RepoRoot 'agents\scout.md'))) {
    Step 'Running from URL — downloading files'
    $RepoRoot = Join-Path $env:TEMP 'devin-agentic-src'
    foreach ($f in $Manifest) {
        $dst = Join-Path $RepoRoot ($f -replace '/', '\')
        New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
        Invoke-WebRequest "$RepoUrl/$f" -OutFile $dst -UseBasicParsing
        Write-Host "  + $f"
    }
}

# --- 1. sanity ---------------------------------------------------------------
Step 'Checking Devin CLI'
if (-not (Test-Path $DevinExe)) {
    Write-Warning "Devin CLI not found at $DevinExe — install it first (https://docs.devin.ai/cli). Continuing anyway."
}
New-Item -ItemType Directory -Force $DevinHome | Out-Null

# --- 2. copy pieces -----------------------------------------------------------
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

# --- 3. merge managed config ---------------------------------------------------
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

$cfg | Add-Member -NotePropertyName permissions -NotePropertyValue $managed.permissions -Force
$cfg | Add-Member -NotePropertyName hooks -NotePropertyValue $managed.hooks -Force
$cfg | ConvertTo-Json -Depth 10 | Set-Content $cfgPath -Encoding UTF8
Write-Host '  + permissions, hooks merged (other keys untouched)'

# --- 4. optional bypass mode ---------------------------------------------------
if ($SetBypass) {
    Step 'Setting DEVIN_PERMISSION_MODE=dangerous (user env)'
    [Environment]::SetEnvironmentVariable('DEVIN_PERMISSION_MODE', 'dangerous', 'User')
    Write-Host '  + every new session defaults to bypass mode'
}

# --- 5. verify ------------------------------------------------------------------
Step 'Verifying'
if (Test-Path $DevinExe) {
    & $DevinExe doctor 2>&1 | Select-Object -First 6
} else {
    Write-Host '  (skipped — devin.exe not found)'
}

Write-Host "`nDone. System installed at $DevinHome" -ForegroundColor Green
Write-Host 'Try it: devin -> /orchestrate, or "use the scout subagent to map this codebase"'
