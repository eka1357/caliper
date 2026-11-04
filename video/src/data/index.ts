// The demo's data, imported straight from the site's files (no copies to go stale).
import results from "../../../web/public/results.json";
import c07 from "../../../web/public/runs/field-c07/run.json";
import a14 from "../../../web/public/runs/field-a14/run.json";
import a08 from "../../../web/public/runs/field-a08/run.json";
import a11s from "../../../web/public/runs/study-a11/run.json";
import a12s from "../../../web/public/runs/study-a12/run.json";
import a13s from "../../../web/public/runs/study-a13/run.json";
import a14s from "../../../web/public/runs/study-a14/run.json";
import a15s from "../../../web/public/runs/study-a15/run.json";
import a16s from "../../../web/public/runs/study-a16/run.json";
import { buildFacts, type Sources } from "./facts.ts";

export const SOURCES = {
  results,
  c07,
  a14,
  a08,
  study: { A11: a11s, A12: a12s, A13: a13s, A14: a14s, A15: a15s, A16: a16s },
} as unknown as Sources;

export const FACTS = buildFacts(SOURCES);

export const LIVE_URL = "caliper-sigma.vercel.app";
export const REPO_URL = "github.com/eka1357/caliper";
