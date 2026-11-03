# PreToolUse hook — hard policy, applies in every permission mode (incl. dangerous).
# Input (stdin): hook event JSON { hook_event_name, tool_name, tool_input, ... }
# Output (stdout): {"decision":"block","reason":...} to deny, nothing to allow.

$i = [Console]::In.ReadToEnd() | ConvertFrom-Json

function Block($reason) {
    @{ decision = 'block'; reason = $reason } | ConvertTo-Json -Compress
}

switch -Regex ($i.tool_name) {

    # Destructive shell commands
    '^exec$' {
        if ($i.tool_input.command -match 'rm\s+(-[a-zA-Z]*r|-[a-zA-Z]*f)|Remove-Item\s+.*-Recurse|del\s+/s\s+/q|format\s+[a-zA-Z]:|dd\s+if=|git\s+push\s+(-f|--force)|git\s+reset\s+--hard|git\s+clean\s+-[a-zA-Z]*f') {
            Block 'Destructive command blocked by global policy. Ask the user to run it manually.'
        }
    }

    # Secret material — replaces permissions.deny, which bypass mode may skip
    '^(read|write|edit|notebook_edit|notebook_read)$' {
        if ($i.tool_input.file_path -match '\.env|id_rsa|\.pem$|\.key$|credentials\.toml$') {
            Block 'Secret file access blocked by global policy.'
        }
    }
}
