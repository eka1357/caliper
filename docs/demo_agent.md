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
> diameter. Then run a street speed study on C:\Projects\Caliper\data\field\S_02.MOV with the
> gate lines below, 10 m apart, speed limit 30 km/h. Report each number with its 90% range, and
> say plainly if a vehicle has no reading and why.
>
> gate_a: from (x1, y1) to (x2, y2); gate_b: from (x3, y3) to (x4, y4)

What should appear:

- `measure` returns status `measured`, the value and unit, and `interval_90` for C07: the same
  numbers as the recorded run on `/workspace` (the call replays the cache). If the agent restates
  the number, check it against the tool output on screen; the number comes from the tool, not the
  agent.
- `study` returns a `StudySummary`: each vehicle's speed with its range or its no-reading reason,
  the median, the 85th percentile with its range, and the share over the limit.

## 3. Gates and the study clip

- **S02 is not filmed yet** (DECISIONS 2026-11-02: S01 had no lane with both marks in view). When it
  arrives, draw the two gate lines through the marks on frame 0 of the normalized video
  (`data/cache/normalized/`, width at most 1280 px), commit them to `eval/study_gates.json` before
  any scoring, and paste the same coordinates into the prompt.
- **Stand-in until then:** `data/field/A_04.MOV` with `vehicle_classes: ["gray car"]` reuses a cached
  SAM response ($0) and shows the tool working end to end. Its markers stand on the far kerb, so
  its speeds are not a validated measurement (DECISIONS 2026-11-02, H5 open). Do not present them
  as one in the video.
- A first study call on a new clip spends money: one SAM request per vehicle class over every
  frame. The cost estimate is checked against `PER_STUDY_CAP_USD` before any call. Run it once
  before filming so the filmed call replays the cache.

## 4. Fallback if Claude Desktop is not available

The Python client in the README ("Use Caliper from another agent") makes the same `measure` call
and prints the structured result; it was run against the cache on 2026-11-02.
