/**
 * Types and pure rules shared by the Parity contract (packages/contracts/parity.py)
 * and any client that reads it: a script, a bot, another app.
 *
 * Two kinds of thing live here:
 *
 *   1. The SHAPE of what the contract's views return, with parsers that
 *      refuse anything else. genlayer-js 1.1.8 returns plain objects with
 *      number fields (measured on studionet); older builds returned Map, so
 *      the parsers accept both.
 *
 *   2. A PORT of the contract's number check, so a client can show which
 *      pairs will be counted before anything is sent. A preview that
 *      disagrees with the contract is worse than none, so the port is tested
 *      against number-vectors.json, which is generated FROM the contract's
 *      own functions and read by its Python tests too.
 */

// ---------------------------------------------------------------- tokens

export const READINGS = ["faithful", "altered", "unclear"] as const;
export type Reading = (typeof READINGS)[number];

export const VERDICTS = ["certified", "rejected", "inconclusive"] as const;
export type Verdict = (typeof VERDICTS)[number];
export type Standing = Verdict | "withdrawn";

export type How = "counted" | "read";

export const MAX_SEGMENTS = 8;
export const MIN_SEGMENT = 2;
export const MAX_SEGMENT = 400;
export const MIN_TITLE = 2;
export const MAX_TITLE = 120;
export const MIN_LANG = 2;
export const MAX_LANG = 40;

// ---------------------------------------------------------------- shapes

export interface Filing {
  id: number;
  filer: string;
  title: string;
  source_lang: string;
  target_lang: string;
  at: string;
  key: string;
  segments: number;
  verdict: Verdict;
  altered: number;
  unclear: number;
  counted: number;
  why: string;
  reason_is_leader_supplied: boolean;
  withdrawn: boolean;
}

export interface Segment {
  index: number;
  filing: number;
  source: string;
  target: string;
  reading: Reading;
  how: How;
}

type Raw = Record<string, unknown>;

function record(v: unknown): Raw | null {
  if (v instanceof Map) return Object.fromEntries(v.entries()) as Raw;
  if (v && typeof v === "object" && !Array.isArray(v)) return v as Raw;
  return null;
}

function num(v: unknown): number {
  const n = typeof v === "bigint" ? Number(v) : Number(v);
  if (!Number.isFinite(n)) throw new Error(`expected a number, got ${String(v)}`);
  return n;
}

function str(v: unknown): string {
  if (typeof v !== "string") throw new Error(`expected a string, got ${typeof v}`);
  return v;
}

function oneOf<T extends string>(v: unknown, allowed: readonly T[], what: string): T {
  const s = str(v);
  if (!(allowed as readonly string[]).includes(s)) throw new Error(`unexpected ${what}: ${s}`);
  return s as T;
}

export function parseFiling(v: unknown): Filing {
  const r = record(v);
  if (!r) throw new Error("filing is not an object");
  return {
    id: num(r.id),
    filer: str(r.filer),
    title: str(r.title),
    source_lang: str(r.source_lang),
    target_lang: str(r.target_lang),
    at: str(r.at),
    key: str(r.key),
    segments: num(r.segments),
    verdict: oneOf(r.verdict, VERDICTS, "verdict"),
    altered: num(r.altered),
    unclear: num(r.unclear),
    counted: num(r.counted),
    why: str(r.why),
    reason_is_leader_supplied: Boolean(r.reason_is_leader_supplied),
    withdrawn: Boolean(r.withdrawn),
  };
}

export function parseSegments(v: unknown): Segment[] {
  const r = record(v);
  const rows = r ? r.segments : null;
  if (!Array.isArray(rows)) throw new Error("segments_of did not return a list");
  return rows.map((row) => {
    const s = record(row);
    if (!s) throw new Error("segment is not an object");
    return {
      index: num(s.index),
      filing: num(s.filing),
      source: str(s.source),
      target: str(s.target),
      reading: oneOf(s.reading, READINGS, "reading"),
      how: oneOf(s.how, ["counted", "read"] as const, "how"),
    };
  });
}

export function parseStanding(v: unknown): Standing {
  return oneOf(v, [...VERDICTS, "withdrawn"] as const, "standing");
}

// ---------------------------------------------------------------- the count

const ARABIC_ZERO = 0x0660;
const PERSIAN_ZERO = 0x06f0;

/** The ASCII digit a character stands for, or "" (Latin, Arabic-Indic, Persian). */
export function digitValue(ch: string): string {
  const o = ch.codePointAt(0) ?? 0;
  if (o >= 48 && o <= 57) return ch;
  if (o >= ARABIC_ZERO && o <= ARABIC_ZERO + 9) return String(o - ARABIC_ZERO);
  if (o >= PERSIAN_ZERO && o <= PERSIAN_ZERO + 9) return String(o - PERSIAN_ZERO);
  return "";
}

/** Every run of digits, as a number without leading zeros, sorted as strings
 * exactly as Python's sorted() sorts them. */
export function numbersOf(text: string): string[] {
  const runs: string[] = [];
  let cur = "";
  for (const ch of text) {
    const d = digitValue(ch);
    if (d !== "") cur += d;
    else if (cur !== "") {
      runs.push(cur);
      cur = "";
    }
  }
  if (cur !== "") runs.push(cur);
  // BigInt, not Number: a long reference number must not round.
  return runs.map((r) => BigInt(r).toString()).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

/** True only when BOTH sides write numerals and they differ. */
export function numbersDiffer(source: string, target: string): boolean {
  const a = numbersOf(source);
  const b = numbersOf(target);
  if (a.length === 0 || b.length === 0) return false;
  return a.length !== b.length || a.some((x, i) => x !== b[i]);
}

export function verdictOf(readings: Reading[]): Verdict {
  if (readings.includes("altered")) return "rejected";
  if (readings.includes("unclear")) return "inconclusive";
  return "certified";
}

/** The contract's clean_text: control characters become spaces, whitespace
 * collapses. Python's str.split() also splits on a handful of Unicode spaces;
 * \s in JS covers the same set for the text a person types. */
export function cleanText(raw: string): string {
  let out = "";
  for (const ch of raw) {
    const o = ch.codePointAt(0) ?? 0;
    out += o < 32 || o === 127 ? " " : ch;
  }
  return out.split(/\s+/).filter(Boolean).join(" ");
}

/** The replay guard's key, so a client can find a filing it just made. */
export async function filingKey(
  sourceLang: string,
  targetLang: string,
  sources: string[],
  targets: string[],
): Promise<string> {
  const text =
    cleanText(sourceLang).toLowerCase() + "\n" + cleanText(targetLang).toLowerCase() + "\n" +
    sources.join("|") + "\n" + targets.join("|");
  const bytes = new TextEncoder().encode(text);
  const hash = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Why the contract would refuse this filing before any model is asked, or "". */
export function filingRefusal(title: string, sourceLang: string, targetLang: string,
                              sources: string[], targets: string[]): string {
  const t = cleanText(title);
  if (t.length < MIN_TITLE || t.length > MAX_TITLE) return `a title is ${MIN_TITLE} to ${MAX_TITLE} characters`;
  for (const lang of [cleanText(sourceLang), cleanText(targetLang)]) {
    if (lang.length < MIN_LANG || lang.length > MAX_LANG) return `a language name is ${MIN_LANG} to ${MAX_LANG} characters`;
  }
  if (cleanText(sourceLang).toLowerCase() === cleanText(targetLang).toLowerCase())
    return "a translation is between two different languages";
  if (sources.length !== targets.length) return `the source has ${sources.length} segments and the translation ${targets.length}`;
  if (sources.length > MAX_SEGMENTS) return `a filing is capped at ${MAX_SEGMENTS} segments`;
  for (const seg of [...sources, ...targets].map(cleanText)) {
    if (seg.length < MIN_SEGMENT) return `a segment needs at least ${MIN_SEGMENT} characters`;
    if (seg.length > MAX_SEGMENT) return `a segment is capped at ${MAX_SEGMENT} characters`;
  }
  return "";
}
