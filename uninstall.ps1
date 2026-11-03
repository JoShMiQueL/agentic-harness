#Requires -Version 5.1
<#
.SYNOPSIS
    Removes the devin-agentic system from %APPDATA%\devin\.

.DESCRIPTION
    Deletes the files this repo installed (agents, orchestrate skill, hook
    scripts, global AGENTS.md) and clears the managed "hooks" key in
    config.json. Permissions are left as-is — restore a config.json.bak-*
    backup if you want the pre-install values back.
#>
$ErrorActionPreference = 'Stop'
$DevinHome = Join-Path $env:APPDATA 'devin'

foreach ($f in 'scout.md', 'tester.md', 'reviewer.md', 'worker.md') {
    Remove-Item (Join-Path "$DevinHome\agents" $f) -Force -ErrorAction SilentlyContinue
}
Remove-Item "$DevinHome\skills\orchestrate" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$DevinHome\hooks\pre-tool-guard.ps1", "$DevinHome\hooks\session-start-memory.ps1" -Force -ErrorAction SilentlyContinue
Remove-Item "$DevinHome\AGENTS.md" -Force -ErrorAction SilentlyContinue

$cfgPath = Join-Path $DevinHome 'config.json'
if (Test-Path $cfgPath) {
    $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
    Copy-Item $cfgPath "$cfgPath.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    $cfg.PSObject.Properties.Remove('hooks')
    $cfg | ConvertTo-Json -Depth 10 | Set-Content $cfgPath -Encoding UTF8
    Write-Host 'hooks key cleared (config.json.bak-* kept)'
}

Write-Host 'Uninstalled. permissions.* left untouched — restore a .bak file to revert them.'
