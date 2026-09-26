import { describe, expect, it } from "vitest";
import record from "../../contracts/deployments/studionet.json";
import shape from "../contract-shape.json";
import { parseFiling, parseSegments, parseStanding, verdictOf, type Reading } from "./index";

// The live deployment's own answers, as packages/contracts/scripts/seed.mjs
// read them back from studionet. If the contract ever returned a shape these
// parsers refuse, a client built on this package would break on real data;
// this is where that shows up first.

describe("the parsers accept everything the live deployment returned", () => {
  it("every filing", () => {
    for (const f of record.filings) {
      const parsed = parseFiling(f);
      expect(parsed.id).toBe(f.id);
      expect(Object.keys(parsed).sort()).toEqual(shape.views.filing.fields);
    }
  });

  it("every segment, and each filing's verdict is the arithmetic on its readings", () => {
    record.segments.forEach((rows, k) => {
      const segs = parseSegments({ segments: rows });
      expect(segs).toHaveLength(record.filings[k].segments);
      expect(verdictOf(segs.map((s) => s.reading as Reading))).toBe(record.filings[k].verdict);
    });
  });

  it("every standing", () => {
    for (const s of record.standing) expect(() => parseStanding(s)).not.toThrow();
  });
});
