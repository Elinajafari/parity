// Put the demo on the explorer: every verdict, and every refusal.
//
//   pnpm seed:contract
//
// Reads the address from deployments/studionet.json (written by deploy.mjs),
// files the three translations in demo/demo.json, sends the writes the
// contract exists to refuse, and appends everything to the same record: every
// transaction hash, its status, the refusal sentence where there was one, and
// every filing and segment as stored. Nothing in that file is typed by hand.
//
// The two accounts come from FILER_PRIVATE_KEY and OTHER_PRIVATE_KEY, or on
// studionet are made in memory for this run and never written to disk.
// StudioNet is gasless, so they hold nothing. The run stops at the first step
// that does not do what the demo expects, because the record claims whatever
// it holds.

import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { PKG, RECORD_FILE, accountFrom, clientFor, loadEnv, network, readRetry, recorder, sourceSha256 } from "./lib.mjs";

loadEnv();
const net = network();
const record = JSON.parse(readFileSync(RECORD_FILE, "utf8"));
if (record.source_sha256 !== sourceSha256()) {
  throw new Error("parity.py has changed since it was deployed; run pnpm deploy:contract first");
}
const address = record.contract;
const demo = JSON.parse(readFileSync(path.join(PKG, "demo", "demo.json"), "utf8"));
const joined = (xs) => xs.join("|");

const filer = accountFrom("FILER_PRIVATE_KEY", net);
const other = accountFrom("OTHER_PRIVATE_KEY", net);
const asFiler = clientFor(net, filer);
const asOther = clientFor(net, other);
const ro = clientFor(net, null);
console.log(`\ncontract ${address}\n  filer ${filer.address}\n  other ${other.address}`);

const rec = recorder();
const certify = (translation) => [demo.title, demo.source_lang, demo.target_lang, joined(demo.source), joined(translation)];

console.log("\nthree translations of one clause");
for (const [k, f] of demo.filings.entries()) {
  await rec.write(asFiler, filer, address, "certify", certify(f.translation), { step: `filing ${k}: ${f.name.replace("_", " ")} (expected ${f.expected})` });
}

console.log("\nwhat the contract refuses");
await rec.write(asFiler, filer, address, "certify", certify(demo.filings[0].translation.slice(0, 2)), { step: "a translation missing a segment", expect: "refused" });
await rec.write(asOther, other, address, "certify", certify(demo.filings[0].translation), { step: "the same translation checked again", expect: "refused" });
await rec.write(asOther, other, address, "withdraw", [1], { step: "someone else withdraws filing 1", expect: "refused" });
await rec.write(asFiler, filer, address, "withdraw", [1], { step: "the filer withdraws the wrong number" });

const read = (fn, args = []) => readRetry(() => ro.readContract({ address, functionName: fn, args }));
const n = Number(await read("count"));
const filings = [], segments = [], standing = [];
for (let k = 0; k < n; k++) {
  filings.push(await read("filing", [k]));
  segments.push((await read("segments_of", [k])).segments);
  standing.push(await read("standing", [k]));
}

const out = {
  ...record,
  accounts: { deployer: record.deployer, filer: filer.address, other: other.address },
  steps: [...record.steps.filter((s) => s.step === "deploy"), ...rec.steps],
  filings,
  segments,
  standing,
};
writeFileSync(RECORD_FILE, JSON.stringify(out, null, 2) + "\n");

console.log("");
for (const [k, f] of filings.entries()) {
  console.log(`  filing ${k}  ${String(f.verdict).padEnd(13)} counted ${f.counted}  ${standing[k]}`);
}
console.log(`  written    ${path.relative(PKG, RECORD_FILE)}\n`);
