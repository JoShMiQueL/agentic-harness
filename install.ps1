#Requires -Version 5.1
<#
.SYNOPSIS
    Installs / syncs / checks the devin-agentic orchestration system.

.DESCRIPTION
    Idempotent installer with a dynamic manifest — every file under
    agents/, skills/ and hooks/ (plus AGENTS.md) is discovered automatically
    (local clone: filesystem scan; remote: GitHub tree API). Adding,
    renaming or deleting files in the repo just works:

      - added    -> installed and tracked by the stamp
      - modified -> overwritten on install, flagged by -Check
      - renamed  -> old name removed (or kept as .bak if locally edited)
      - deleted  -> orphan detected by -Check, cleaned on install

    - Install from a clone:   .\install.ps1
    - Install remote (one-liner):
        irm https://raw.githubusercontent.com/JoShMiQueL/devin-agentic/main/install.ps1 | iex
    - Check sync status:
        .\install.ps1 -Check
        iex "& { $(irm https://raw.githubusercontent.com/JoShMiQueL/devin-agentic/main/install.ps1) } -Check"

    Install stamp: %APPDATA%\devin\agentic.json (version + SHA256 per file).
#>
param(
    [switch]$SetBypass,
    [switch]$Check,
    [string]$Branch = 'main'
)

$ErrorActionPreference = 'Stop'
$RepoSlug = 'JoShMiQueL/devin-agentic'
$RepoUrl = "https://raw.githubusercontent.com/$RepoSlug/$Branch"
$DevinHome = Join-Path $env:APPDATA 'devin'
$DevinExe = Join-Path $env:LOCALAPPDATA 'devin\cli\bin\devin.exe'
$StampPath = Join-Path $DevinHome 'agentic.json'
$SyncDirs = 'agents', 'skills', 'hooks'          # copied verbatim under $DevinHome
$TopFiles = 'AGENTS.md'                          # repo-root files synced verbatim
$MergedFiles = 'config.managed.json'             # merged, never copied verbatim

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Sha256($p) { (Get-FileHash $p -Algorithm SHA256 -ErrorAction Stop).Hash.ToLower() }

# --- Discover manifest: repo-relative -> $DevinHome-relative ------------------
$RepoRoot = $PSScriptRoot
$localRepo = Test-Path (Join-Path $RepoRoot 'agents\scout.md')
$Manifest = [ordered]@{}

if ($localRepo) {
    foreach ($d in $SyncDirs) {
        $root = Join-Path $RepoRoot $d
        if (Test-Path $root) {
            Get-ChildItem $root -Recurse -File | ForEach-Object {
                $rel = $_.FullName.Substring($RepoRoot.Length + 1) -replace '\\', '/'
                $Manifest[$rel] = ($rel -replace '/', '\')
            }
        }
    }
    foreach ($f in $TopFiles) {
        if (Test-Path (Join-Path $RepoRoot $f)) { $Manifest[$f] = $f }
    }
}
else {
    Step 'Resolving remote file list'
    $tree = (Invoke-RestMethod "https://api.github.com/repos/$RepoSlug/git/trees/$Branch`?recursive=1" -Headers @{ 'User-Agent' = 'devin-agentic' }).tree
    $remote = $tree | Where-Object {
        $_.type -eq 'blob' -and ($_.path -match '^(' + ($SyncDirs -join '|') + ')/' -or $TopFiles -contains $_.path -or $MergedFiles -contains $_.path)
    } | ForEach-Object { $_.path }
    $RepoRoot = Join-Path $env:TEMP 'devin-agentic-src'
    foreach ($f in $remote + 'VERSION') {
        $dst = Join-Path $RepoRoot ($f -replace '/', '\')
        New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
        Invoke-WebRequest "$RepoUrl/$f" -OutFile $dst -UseBasicParsing
        if ($f -ne 'VERSION' -and $f -ne $MergedFiles) { $Manifest[$f] = ($f -replace '/', '\') }
        if (-not $Check) { Write-Host "  + $f" }
    }
}

$RepoVersion = (Get-Content (Join-Path $RepoRoot 'VERSION') -Raw -ErrorAction SilentlyContinue).Trim()
$stamp = $null
if (Test-Path $StampPath) { $stamp = Get-Content $StampPath -Raw | ConvertFrom-Json }
$stampFiles = @{}
if ($stamp -and $stamp.files) {
    $stamp.files.PSObject.Properties | ForEach-Object { $stampFiles[$_.Name] = $_.Value }
}

# ============================ CHECK MODE ======================================
if ($Check) {
    Step 'Sync status'
    Write-Host ("  repo version : {0}" -f $RepoVersion)
    Write-Host ("  installed    : {0}" -f $(if ($stamp) { $stamp.version } else { '(unknown - no stamp)' }))
    Write-Host ("  installed at : {0}`n" -f $(if ($stamp) { $stamp.installed_at } else { '-' }))

    $dirty = $false
    foreach ($f in $Manifest.Keys) {
        $src = Join-Path $RepoRoot ($f -replace '/', '\')
        $dst = Join-Path $DevinHome $Manifest[$f]
        $srcHash = Sha256 $src
        $dstHash = if (Test-Path $dst) { Sha256 $dst } else { $null }
        $stampHash = $stampFiles[$f]

        if (-not $dstHash)             { $status = 'MISSING (new in repo, not installed)'; $dirty = $true }
        elseif ($dstHash -eq $srcHash) { $status = 'sync' }
        elseif ($stampHash -and $dstHash -ne $stampHash) {
            $status = if ($srcHash -ne $stampHash) { 'locally-modified (+remote update pending)' } else { 'locally-modified' }
            $dirty = $true
        }
        else                           { $status = 'update-available'; $dirty = $true }
        "{0,-42} {1}" -f $f, $status | Write-Host
    }
    # Orphans: files we installed that are no longer in the repo
    foreach ($f in $stampFiles.Keys) {
        if (-not $Manifest.Contains($f)) {
            $dst = Join-Path $DevinHome ($f -replace '/', '\')
            if (Test-Path $dst) {
                $s = if ((Sha256 $dst) -eq $stampFiles[$f]) { 'removed-in-repo (install will delete)' } else { 'removed-in-repo + locally-modified (install keeps a .bak)' }
                "{0,-42} {1}" -f $f, $s | Write-Host; $dirty = $true
            }
        }
    }
    Write-Host ''
    if ($dirty) { Write-Host 'Run the install one-liner to converge. Untouched local edits are overwritten; orphans are deleted (a .bak is kept if you edited one).' -ForegroundColor Yellow }
    else        { Write-Host 'Everything in sync.' -ForegroundColor Green }
    return
}

# ============================ INSTALL MODE ====================================
Step 'Checking Devin CLI'
if (-not (Test-Path $DevinExe)) {
    Write-Warning "Devin CLI not found at $DevinExe — install it first. Continuing anyway."
}
New-Item -ItemType Directory -Force $DevinHome | Out-Null

# --- Short-circuit: already in sync -------------------------------------------
$allSync = $stamp -and $stamp.version -eq $RepoVersion
if ($allSync) {
    foreach ($f in $Manifest.Keys) {
        $dst = Join-Path $DevinHome $Manifest[$f]
        if (-not (Test-Path $dst) -or (Sha256 $dst) -ne (Sha256 (Join-Path $RepoRoot ($f -replace '/', '\')))) { $allSync = $false; break }
    }
    if ($allSync -and ($stampFiles.Keys | Where-Object { -not $Manifest.Contains($_) })) { $allSync = $false }
}
if ($allSync -and -not $SetBypass) {
    Write-Host "Already in sync (v$RepoVersion) - nothing to do." -ForegroundColor Green
    return
}

Step "Copying files -> $DevinHome"
foreach ($f in $Manifest.Keys) {
    $src = Join-Path $RepoRoot ($f -replace '/', '\')
    $dst = Join-Path $DevinHome $Manifest[$f]
    if ((Test-Path $dst) -and -not $stampFiles[$f] -and (Sha256 $dst) -ne (Sha256 $src)) {
        Copy-Item $dst "$dst.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Write-Host "  ! $f had unmanaged content -> .bak kept"
    }
    New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
    Copy-Item $src $dst -Force
    Write-Host "  + $f"
}

# --- Orphan cleanup: installed by us, gone from repo ---------------------------
foreach ($f in $stampFiles.Keys) {
    if (-not $Manifest.Contains($f)) {
        $dst = Join-Path $DevinHome ($f -replace '/', '\')
        if (Test-Path $dst) {
            if ((Sha256 $dst) -eq $stampFiles[$f]) {
                Remove-Item $dst -Force
                Write-Host "  - $f (removed in repo)"
            } else {
                Move-Item $dst "$dst.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
                Write-Host "  ! $f removed in repo but locally modified -> .bak kept"
            }
        }
    }
}

Step 'Merging config.json'
$cfgPath = Join-Path $DevinHome 'config.json'
$managed = Get-Content "$RepoRoot\config.managed.json" -Raw | ConvertFrom-Json
if (Test-Path $cfgPath) {
    $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
    Copy-Item $cfgPath "$cfgPath.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Write-Host "  ! existing config.json backed up"
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

# --- Write install stamp -------------------------------------------------------
Step 'Writing install stamp'
$files = @{}
foreach ($f in $Manifest.Keys) { $files[$f] = (Sha256 (Join-Path $DevinHome $Manifest[$f])) }
$gitSha = $null
if (Test-Path (Join-Path $RepoRoot '.git')) { $gitSha = (git -C $RepoRoot rev-parse HEAD 2>$null) }
@{
    version      = $RepoVersion
    source_sha   = $gitSha
    installed_at = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
    files        = $files
} | ConvertTo-Json -Depth 5 | Set-Content $StampPath -Encoding UTF8
Write-Host "  + $StampPath (v$RepoVersion)"

Step 'Verifying'
if (Test-Path $DevinExe) { & $DevinExe doctor 2>&1 | Select-Object -First 6 }
else { Write-Host '  (skipped - devin.exe not found)' }

Write-Host "`nDone. System installed at $DevinHome (v$RepoVersion)" -ForegroundColor Green
Write-Host 'Try it: devin -> /orchestrate, or "use the scout subagent to map this codebase"'
