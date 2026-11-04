// agentic-memory — replicates the SessionStart memory hook.
// If <project>/.opencode/memory/state.md exists, it is appended to the
// system prompt on the first model call of each session. Nothing is
// created for projects without a memory file.

import { existsSync, readFileSync } from "fs"
import { join } from "path"

export default {
  id: "agentic-memory",
  setup: async (ctx) => {
    let state = null
    const sessions = new Set()
    try {
      const p = join(ctx.location.directory, ".opencode", "memory", "state.md")
      if (existsSync(p)) state = readFileSync(p, "utf8").trim()
    } catch {
      /* unreadable -> skip silently */
    }
    if (!state) return

    await ctx.session.hook("context", (event) => {
      if (!event.sessionID || sessions.has(event.sessionID)) return
      sessions.add(event.sessionID)
      event.system.push({
        type: "text",
        text: "Persisted project memory:\n" + state,
      })
    })
  },
}
