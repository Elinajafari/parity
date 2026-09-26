// Check the live deployment against the record, from the chain, read only.
//
//   pnpm e2e:contract
//
// deployments/studionet.json says what the demo did. This asks the chain
// again, with no key: every transaction's receipt must still say what the
// record says (executed, or refused with the same sentence), and every filing
// and segment must read back exactly as recorded. It prints PASS or FAIL per
// check and exits non-zero on any FAIL, so a record that drifted from the
// chain cannot sit in the repo looking verified.

import { readFileSync } from "node:fs";
import { RECORD_FILE, clientFor, loadEnv, network, outcome, readRetry, sourceSha256 } from "./lib.mjs";

loadEnv();
const net = network();
const record = JSON.parse(readFileSync(RECORD_FILE, "utf8"));
const client = clientFor(net, null);
const address = record.contract;

let failed = 0;
function check(name, ok, detail = "") {
  if (!ok) failed++;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${!ok && detail ? `\n      ${detail}` : ""}`);
}
const view = (functionName, args = []) => readRetry(() => client.readContract({ address, functionName, args }));
const plain = (v) => JSON.parse(JSON.stringify(v, (_, x) => (typeof x === "bigint" ? Number(x) : x instanceof Map ? Object.fromEntries(x) : x)));
const sorted = (o) => (Array.isArray(o) ? o.map(sorted) : o && typeof o === "object" ? Object.fromEntries(Object.keys(o).sort().map((k) => [k, sorted(o[k])])) : o);
const same = (a, b) => JSON.stringify(sorted(plain(a))) === JSON.stringify(sorted(plain(b)));

console.log(`\n${record.network} contract ${address}\n`);
check("the recorded source is the file in this repo", record.source_sha256 === sourceSha256());

for (const s of record.steps) {
  const receipt = await readRetry(() => client.getTransaction({ hash: s.tx }));
  const out = outcome(receipt);
  const good = s.ok ? out.ok : !out.ok && out.refusal === s.refusal;
  check(`tx ${s.tx.slice(0, 10)}  ${s.step}`, good, `chain says ok=${out.ok} ${out.status} "${out.refusal}"`);
}

const count = Number(await view("count"));
check(`count is at least the ${record.filings.length} demo filings`, count >= record.filings.length, `count ${count}`);

for (const [id, want] of record.filings.entries()) {
  const got = await view("filing", [id]);
  // withdrawn can only move one way after the record was written.
  check(`filing ${id} reads back as recorded (${want.verdict})`, same({ ...plain(got), withdrawn: want.withdrawn }, want) && (plain(got).withdrawn || !want.withdrawn));
  const segs = await view("segments_of", [id]);
  check(`filing ${id}: ${record.segments[id].length} segments and their readings`, same(plain(segs).segments, record.segments[id]));
  const standing = await view("standing", [id]);
  check(`filing ${id} standing is ${record.standing[id]}`, standing === record.standing[id], `chain says ${standing}`);
}

console.log(`\n${failed === 0 ? "every check passed" : `${failed} check(s) failed`}`);
process.exit(failed === 0 ? 0 : 1);
