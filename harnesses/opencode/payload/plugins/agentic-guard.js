// agentic-guard — hard policy, fires in every permission mode (incl. --auto).
// Blocks destructive shell commands and access to secret files.
// Deny mechanism: set event.effect = "deny" in the permission.evaluate hook —
// a deny is enforced even under --auto and the model sees the reason.

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
const FILE_ACTIONS = new Set(["read", "edit", "write", "patch"])

export default {
  id: "agentic-guard",
  setup: async (ctx) => {
    await ctx.permission.hook("evaluate", (event) => {
      if (event.action === "shell") {
        const command = event.resources.join(" ")
        if (DESTRUCTIVE.test(command)) {
          event.effect = "deny"
          event.message =
            "Blocked by global policy (agentic-guard): destructive command. " +
            "Ask the user to run it manually."
        }
      } else if (FILE_ACTIONS.has(event.action)) {
        if (event.resources.some((r) => SECRETS.test(r))) {
          event.effect = "deny"
          event.message =
            "Blocked by global policy (agentic-guard): secret file access."
        }
      }
    })
  },
}
