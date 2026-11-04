// agentic-guard — hard policy, fires in every permission mode (incl. --auto).
// Blocks destructive shell commands and access to secret files.
// Deny mechanism: throw before execution -> the tool never runs and the
// model sees the reason in the tool error.

const DESTRUCTIVE = new RegExp(
  [
    String.raw`rm\s+(-[a-zA-Z]*r|-[a-zA-Z]*f)`,
    String.raw`Remove-Item\s+.*-Recurse`,
    String.raw`del\s+/s\s+/q`,
    String.raw`format\s+[a-zA-Z]:`,
    String.raw`dd\s+if=`,
    String.raw`git\s+push\s+(-f|--force)`,
    String.raw`git\s+reset\s+--hard`,
    String.raw`git\s+clean\s+-[a-zA-Z]*f`,
  ].join("|"),
  "i",
)

const SECRETS = /\.env|id_rsa|\.pem$|\.key$|credentials\.toml$/i
const FILE_TOOLS = new Set(["read", "write", "edit", "patch", "multiedit"])
const SHELL_TOOLS = new Set(["bash", "shell", "exec", "execute"])

function file_path(args) {
  return args.filePath ?? args.file_path ?? args.path ?? ""
}

export const AgenticGuard = async () => ({
  "tool.execute.before": async (input, output) => {
    const args = output.args ?? {}
    if (SHELL_TOOLS.has(input.tool)) {
      const command = String(args.command ?? args.commands ?? "")
      if (DESTRUCTIVE.test(command)) {
        throw new Error(
          "Blocked by global policy (agentic-guard): destructive command. " +
            "Ask the user to run it manually.",
        )
      }
    } else if (FILE_TOOLS.has(input.tool) && SECRETS.test(file_path(args))) {
      throw new Error(
        "Blocked by global policy (agentic-guard): secret file access.",
      )
    }
  },
})
