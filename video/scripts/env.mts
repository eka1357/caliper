// Reads one variable from the repo's .env without printing it (AGENTS rule 6).
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

export function envVar(name: string): string {
  if (process.env[name]) return process.env[name] as string;
  const text = readFileSync(resolve(import.meta.dirname, "..", "..", ".env"), "utf8");
  for (const line of text.split(/\r?\n/)) {
    const m = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/.exec(line);
    if (m && m[1] === name) {
      return m[2].replace(/^(['"])(.*)\1$/, "$2").trim();
    }
  }
  throw new Error(`${name} is not set in .env`);
}
