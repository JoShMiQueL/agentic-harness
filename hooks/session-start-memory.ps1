# SessionStart hook — injects .devin/memory/state.md into agent context if present.
# Output (stdout): JSON with hookSpecificOutput.additionalContext, or nothing.
$f = Join-Path $env:DEVIN_PROJECT_DIR '.devin\memory\state.md'
if (Test-Path $f) {
    $c = Get-Content $f -Raw
    @{
        hookSpecificOutput = @{
            hookEventName     = 'SessionStart'
            additionalContext = "Persisted project memory:`n$c"
        }
    } | ConvertTo-Json -Depth 4 -Compress
}
