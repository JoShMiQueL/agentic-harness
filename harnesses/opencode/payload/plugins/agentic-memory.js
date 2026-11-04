// agentic-memory — replicates the SessionStart memory hook.
// If <project>/.opencode/memory/state.md exists, it is appended to the
// system prompt on the first model call of each session. Nothing is
// created for projects without a memory file.

import { existsSync, readFileSync } from "fs"
import { join } from "path"

export const AgenticMemory = async ({ directory }) => {
  let state = null
  const sessions = new Set()
  try {
    const p = join(directory, ".opencode", "memory", "state.md")
    if (existsSync(p)) state = readFileSync(p, "utf8").trim()
  } catch {
    /* unreadable -> skip silently */
  }
  if (!state) return {}

  return {
    "experimental.chat.system.transform": async (input, output) => {
      if (!input.sessionID || sessions.has(input.sessionID)) return
      sessions.add(input.sessionID)
      output.system.push("Persisted project memory:\n" + state)
    },
  }
}
