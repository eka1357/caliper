import type { Word } from "./media.ts";

export type Page = { text: string; startMs: number; endMs: number };

const SOFT = /[,:;]$/;

/**
 * One-line caption pages from the spoken words. A page ends at a sentence end, or at a comma, colon
 * or semicolon once it is past about half the width. A page that would run past maxChars breaks
 * after its last comma, colon or semicolon (not mid-phrase) when it has one. Words of a key line are
 * left out (the line is on screen as large type) and no page runs across one.
 */
export function pages(
  words: Word[],
  maxChars: number,
  isKey: (w: Word) => boolean,
): Page[] {
  const out: Page[] = [];
  let cur: Word[] = [];
  const text = (ws: Word[]) => ws.map((w) => w.text).join(" ");
  const push = (ws: Word[]) => {
    if (ws.length) {
      out.push({
        text: text(ws),
        startMs: ws[0].startMs,
        endMs: ws[ws.length - 1].endMs,
      });
    }
  };
  const flush = () => {
    push(cur);
    cur = [];
  };
  const tooLong = (w: Word) =>
    cur.length > 0 && text(cur).length + 1 + w.text.length > maxChars;
  for (const w of words) {
    if (isKey(w)) {
      flush();
      continue;
    }
    if (tooLong(w)) {
      let j = -1;
      for (let k = cur.length - 1; k > 0 && j < 0; k--) {
        if (SOFT.test(cur[k].text)) j = k;
      }
      if (j > 0 && text(cur.slice(0, j + 1)).length >= 12) {
        push(cur.slice(0, j + 1));
        cur = cur.slice(j + 1);
      }
      if (tooLong(w)) flush();
    }
    cur.push(w);
    if (/[.?!]$/.test(w.text)) flush();
    else if (SOFT.test(w.text) && text(cur).length > maxChars * 0.55) flush();
  }
  flush();
  return out;
}
