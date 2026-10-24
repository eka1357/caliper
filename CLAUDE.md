@AGENTS.md

# Claude Code notes

These add to AGENTS.md. If anything here conflicts with AGENTS.md, AGENTS.md wins.

- Start every phase in plan mode. Show the plan, wait for approval, then build.
- Use the slash commands in `.claude/commands/`: `/phase 0` starts a phase from PROMPTS.md, `/gate` produces the gate report.
- Before saying a task is done, run `make test` and `make lint` and paste the summary lines.
- Never read `.env`. It is denied in `.claude/settings.json`. Use `.env.example` to learn variable names.
- UI work: start Claude Code inside `web/` so the shadcn MCP server finds `web/components.json` (set up in docs/SETUP.md step 4).
- The 21st.dev Magic MCP (`.mcp.json`) is for first drafts of a component only. Every generated component must then be restyled to the tokens in docs/DESIGN.md and pass the checks in its QA list.
- Keep diffs small. One concern per commit.
- When a number changes, say which command produced it and where it is stored. Never quote a number from memory.
