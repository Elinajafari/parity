import { describe, expect, it } from "vitest";
import vectors from "../number-vectors.json";
import {
  cleanText,
  digitValue,
  filingKey,
  filingRefusal,
  numbersDiffer,
  numbersOf,
  parseFiling,
  parseSegments,
  parseStanding,
  verdictOf,
  type Reading,
} from "./index";

// number-vectors.json is generated from the contract's own functions
// (see packages/contracts/tests/test_vectors.py), so every case below is the
// contract's answer, not a hand-written expectation.

describe("the port agrees with the contract", () => {
  it.each(vectors.numbers_of)("numbers_of($text)", ({ text, numbers }) => {
    expect(numbersOf(text)).toEqual(numbers);
  });
  it.each(vectors.numbers_differ)("numbers_differ($source | $target)", ({ source, target, differ }) => {
    expect(numbersDiffer(source, target)).toBe(differ);
  });
  it.each(vectors.verdict_of)("verdict_of($readings)", ({ readings, verdict }) => {
    expect(verdictOf(readings as Reading[])).toBe(verdict);
  });
  it.each(vectors.clean_text)("clean_text", ({ raw, clean }) => {
    expect(cleanText(raw)).toBe(clean);
  });
  it.each(vectors.filing_key)("filing_key", async ({ source_lang, target_lang, sources, targets, key }) => {
    expect(await filingKey(source_lang, target_lang, sources, targets)).toBe(key);
  });
});

describe("digits", () => {
  it("reads all three scripts as the same ten digits", () => {
    for (let d = 0; d < 10; d++) {
      expect(digitValue(String(d))).toBe(String(d));
      expect(digitValue(String.fromCodePoint(0x06f0 + d))).toBe(String(d));
      expect(digitValue(String.fromCodePoint(0x0660 + d))).toBe(String(d));
    }
    expect(digitValue("a")).toBe("");
  });

  it("does not round a long reference number", () => {
    expect(numbersOf("ref 12345678901234567890")).toEqual(["12345678901234567890"]);
  });
});

describe("the client-side refusals mirror the contract's", () => {
  const ok = ["one two", "three four"];
  it("accepts a well formed filing", () => {
    expect(filingRefusal("A title", "English", "Persian", ok, ok)).toBe("");
  });
  it.each([
    ["x", "English", "Persian", ok, ok, "title"],
    ["A title", "E", "Persian", ok, ok, "language name"],
    ["A title", "English", " english ", ok, ok, "two different languages"],
    ["A title", "English", "Persian", ok, ok.slice(0, 1), "2 segments and the translation 1"],
    ["A title", "English", "Persian", Array(9).fill("ab"), Array(9).fill("cd"), "capped at 8"],
    ["A title", "English", "Persian", ["a", "bb"], ok, "at least 2"],
    ["A title", "English", "Persian", ["y".repeat(401), "bb"], ok, "capped at 400"],
  ])("refuses %s / %s / %s", (t, s, l, src, tgt, msg) => {
    expect(filingRefusal(t, s, l, src as string[], tgt as string[])).toContain(msg);
  });
});

describe("parsers refuse what the contract never returns", () => {
  const filing = {
    id: 2, filer: "0x" + "ab".repeat(20), title: "t", source_lang: "English", target_lang: "Persian",
    at: "2026-09-23T10:00:00Z", key: "k", segments: 3, verdict: "rejected", altered: 1, unclear: 0,
    counted: 0, why: "", reason_is_leader_supplied: true, withdrawn: false,
  };
  it("parses a filing, from an object or a Map", () => {
    expect(parseFiling(filing).verdict).toBe("rejected");
    expect(parseFiling(new Map(Object.entries(filing))).segments).toBe(3);
  });
  it("refuses an unknown verdict", () => {
    expect(() => parseFiling({ ...filing, verdict: "approved" })).toThrow("unexpected verdict");
  });
  it("parses segments and refuses an unknown reading", () => {
    const seg = { index: 0, filing: 2, source: "a", target: "b", reading: "faithful", how: "read" };
    expect(parseSegments({ segments: [seg] })[0].how).toBe("read");
    expect(() => parseSegments({ segments: [{ ...seg, reading: "good" }] })).toThrow("unexpected reading");
    expect(() => parseSegments({})).toThrow("did not return a list");
  });
  it("parses a standing", () => {
    expect(parseStanding("withdrawn")).toBe("withdrawn");
    expect(() => parseStanding("maybe")).toThrow();
  });
});
