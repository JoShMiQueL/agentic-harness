#Requires -Version 5.1
<#
.SYNOPSIS
    Installs the devin-agentic orchestration system into %APPDATA%\devin\.

.DESCRIPTION
    Idempotent installer / remote bootstrap / sync checker.

    - Install from a clone:   .\install.ps1
    - Install remote (one-liner):
        irm https://raw.githubusercontent.com/JoShMiQueL/devin-agentic/main/install.ps1 | iex
    - Check sync status (local clone):
        .\install.ps1 -Check
    - Check sync status (remote):
        iex "& { $(irm https://raw.githubusercontent.com/JoShMiQueL/devin-agentic/main/install.ps1) } -Check"

    Installed files get a stamp in %APPDATA%\devin\agentic.json (version +
    SHA256 per file) so -Check can report: sync / update-available /
    locally-modified / missing.

.PARAMETER SetBypass
    Sets DEVIN_PERMISSION_MODE=dangerous as a user env var.

.PARAMETER Check
    Compares installed files against this repo's files and the install stamp.
    Makes no changes.

.PARAMETER Branch
    Remote branch to pull files from (default: main).
#>
param(
    [switch]$SetBypass,
    [switch]$Check,
    [string]$Branch = 'main'
)

$ErrorActionPreference = 'Stop'
$RepoUrl = "https://raw.githubusercontent.com/JoShMiQueL/devin-agentic/$Branch"
$DevinHome = Join-Path $env:APPDATA 'devin'
$DevinExe = Join-Path $env:LOCALAPPDATA 'devin\cli\bin\devin.exe'
$StampPath = Join-Path $DevinHome 'agentic.json'

# Manifest: repo-relative path -> path relative to $DevinHome ($null = merged, not copied verbatim)
$Manifest = [ordered]@{
    'AGENTS.md'                    = 'AGENTS.md'
    'config.managed.json'          = $null
    'agents/scout.md'              = 'agents\scout.md'
    'agents/tester.md'             = 'agents\tester.md'
    'agents/reviewer.md'           = 'agents\reviewer.md'
    'agents/worker.md'             = 'agents\worker.md'
    'skills/orchestrate/SKILL.md'  = 'skills\orchestrate\SKILL.md'
    'hooks/pre-tool-guard.ps1'     = 'hooks\pre-tool-guard.ps1'
    'hooks/session-start-memory.ps1' = 'hooks\session-start-memory.ps1'
}

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Sha256($path) { (Get-FileHash $path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLower() }

# --- Resolve source files: local clone or remote download -------------------
$RepoRoot = $PSScriptRoot
if (-not (Test-Path (Join-Path $RepoRoot 'agents\scout.md'))) {
    $RepoRoot = Join-Path $env:TEMP 'devin-agentic-src'
    $dl = $Manifest.Keys + 'VERSION'
    if ($Check) { Step 'Checking remote version' } else { Step 'Running from URL - downloading files' }
    foreach ($f in $dl) {
        $dst = Join-Path $RepoRoot ($f -replace '/', '\')
        New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
        Invoke-WebRequest "$RepoUrl/$f" -OutFile $dst -UseBasicParsing
        if (-not $Check) { Write-Host "  + $f" }
    }
}
$RepoVersion = (Get-Content (Join-Path $RepoRoot 'VERSION') -Raw -ErrorAction SilentlyContinue).Trim()

# ============================ CHECK MODE ====================================
if ($Check) {
    Step 'Sync status'
    $stamp = $null
    if (Test-Path $StampPath) { $stamp = Get-Content $StampPath -Raw | ConvertFrom-Json }
    Write-Host ("  repo version : {0}" -f $RepoVersion)
    Write-Host ("  installed    : {0}" -f $(if ($stamp) { $stamp.version } else { '(unknown — no stamp)' }))
    Write-Host ("  installed at : {0}`n" -f $(if ($stamp) { $stamp.installed_at } else { '-' }))

    $dirty = $false
    foreach ($f in $Manifest.Keys) {
        $rel = $Manifest[$f]
        if (-not $rel) { continue }   # merged files are not compared verbatim
        $src = Join-Path $RepoRoot ($f -replace '/', '\')
        $dst = Join-Path $DevinHome $rel
        $srcHash = Sha256 $src
        $dstHash = if (Test-Path $dst) { Sha256 $dst } else { $null }
        $stampHash = if ($stamp -and $stamp.files.$f) { $stamp.files.$f } else { $null }

        if (-not $dstHash)        { $status = 'MISSING (not installed)'; $dirty = $true }
        elseif ($dstHash -eq $srcHash) { $status = 'sync' }
        elseif ($stampHash -and $dstHash -ne $stampHash) {
            $status = if ($dstHash -ne $srcHash -and $srcHash -ne $stampHash) { 'locally-modified (+remote update pending)' } else { 'locally-modified' }
            $dirty = $true
        }
        else                      { $status = 'update-available'; $dirty = $true }
        "{0,-38} {1}" -f $f, $status | Write-Host
    }
    Write-Host ''
    if ($dirty) { Write-Host 'Run install.ps1 (or the irm one-liner) to update. Local edits are overwritten by repo files.' -ForegroundColor Yellow }
    else        { Write-Host 'Everything in sync.' -ForegroundColor Green }
    return
}

# ============================ INSTALL MODE ==================================
Step 'Checking Devin CLI'
if (-not (Test-Path $DevinExe)) {
    Write-Warning "Devin CLI not found at $DevinExe — install it first (https://docs.devin.ai/cli). Continuing anyway."
}
New-Item -ItemType Directory -Force $DevinHome | Out-Null

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

if ($SetBypass) {
    Step 'Setting DEVIN_PERMISSION_MODE=dangerous (user env)'
    [Environment]::SetEnvironmentVariable('DEVIN_PERMISSION_MODE', 'dangerous', 'User')
    Write-Host '  + every new session defaults to bypass mode'
}

# --- Write install stamp ------------------------------------------------------
Step 'Writing install stamp'
$files = @{}
foreach ($f in $Manifest.Keys) {
    $rel = $Manifest[$f]
    if ($rel) { $files[$f] = (Sha256 (Join-Path $DevinHome $rel)) }
}
$gitSha = $null
if (Test-Path (Join-Path $RepoRoot '.git')) {
    $gitSha = (git -C $RepoRoot rev-parse HEAD 2>$null)
}
@{
    version      = $RepoVersion
    source_sha   = $gitSha
    installed_at = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    files        = $files
} | ConvertTo-Json -Depth 5 | Set-Content $StampPath -Encoding UTF8
Write-Host "  + $StampPath (v$RepoVersion)"

# --- Verify ---------------------------------------------------------------------
Step 'Verifying'
if (Test-Path $DevinExe) { & $DevinExe doctor 2>&1 | Select-Object -First 6 }
else { Write-Host '  (skipped - devin.exe not found)' }

Write-Host "`nDone. System installed at $DevinHome" -ForegroundColor Green
Write-Host 'Try it: devin -> /orchestrate, or "use the scout subagent to map this codebase"'
