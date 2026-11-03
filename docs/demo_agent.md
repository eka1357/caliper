# Demo: another agent calls Caliper over MCP

For the demo video: Claude Desktop uses Caliper's MCP server (`backend/caliper/mcp_server.py`) to
measure the phone in C07 and to run a street speed study. Both calls go through the live-run caps;
the C07 call is answered from the disk cache, so it costs $0 and returns the recorded run's value.

## 1. Claude Desktop config

Windows: `%APPDATA%\Claude\claude_desktop_config.json` (macOS:
`~/Library/Application Support/Claude/claude_desktop_config.json`). Restart Claude Desktop after
saving.

```json
{
  "mcpServers": {
    "caliper": {
      "command": "C:\\Projects\\Caliper\\backend\\.venv\\Scripts\\python.exe",
      "args": ["-m", "caliper.mcp_server"],
      "env": {
        "PYTHONPATH": "C:\\Projects\\Caliper\\backend",
        "LIVE_RUNS_ENABLED": "true"
      }
    }
  }
}
```

`MODEL_API_KEY` and the caps are read from the repo's `.env` (never paste the key into this file).
`LIVE_RUNS_ENABLED` is set here because `.env` keeps it false locally; an environment variable wins
over `.env`. Needs `pip install -e "backend[mcp]"` once.

Check before filming: Claude Desktop's tools menu lists `caliper` with `measure` and `study`.

## 2. The prompt (one message, type it on camera)

> Use the caliper tools. First measure how long the phone is in cm in
> C:\Projects\Caliper\data\field\C_07.MOV — the coin next to it is an INR 10 coin, 0.027 m in
> diameter. Then run a street speed study on
> C:\Projects\Caliper\data\field\PXL_20261103_120028917.mp4 (vehicle class "scooter") with
> gate_a from (200, 0) to (200, 720) and gate_b from (1010, 0) to (1010, 720), 7.92 m apart.
> Report each number with its 90% range, and say plainly if a vehicle has no reading and why.

That clip is A14 from Set A (scooter); the gates are the ones committed in eval/study_gates.json
before scoring. `vehicle_classes: ["scooter"]` matters: it is the SAM concept already in the cache.
With the default four classes the study would make three new SAM requests (they cost money).

What should appear (both calls replay the disk cache, $0):

- `measure` returns status `measured` for C07 with its value and `interval_90`: the recorded run's
  value (the live bootstrap, B=200, can move the range in the second decimal). If the agent
  restates the number, check it against the tool output on screen; the number comes from the
  tool, not the agent.
- `study` returns a `StudySummary`: the moving scooter measured with its speed and range, and the
  other tracked scooters (parked at the shops) with "no reading" and the reason. The speed is the
  same as eval/h5_results.csv for A14.

## 3. Checked on 2026-11-03

- Pre-run with an MCP stdio client using exactly the config above (same `command`, `args` and
  `env`, started from a folder outside the repo) and the API URL pointed at a dead port, so a cache
  miss would have failed: both calls were cache hits, $0 settled, the tool list shows `measure`
  and `study`. This checks the server and the config; Claude Desktop itself was not run here.
- S02 (a multi-vehicle street clip) is not filmed. When it is, draw its gates on frame 0, commit
  them to eval/study_gates.json before scoring, run it once, and use it here instead of A14.
- The live caps apply (`.env`): a study clip over `LIVE_MAX_STUDY_SECONDS` or an estimate over
  `PER_STUDY_CAP_USD` is refused before any call.

## 4. Fallback if Claude Desktop is not available

The Python client in the README ("Use Caliper from another agent") makes the same `measure` call
and prints the structured result; it was run against the cache on 2026-11-02.
