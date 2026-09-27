// A second round on the deployed contract, from two NEW wallets.
//
//   pnpm seed:activity
//
// The contract in deployments/studionet.json is not redeployed. Two wallets
// made in memory for this run, used by nothing else, file one translation
// each, try what the contract refuses, and withdraw one:
//
//   filer A   a faithful translation            expected certified (read by validators)
//   filer B   both numbers changed               expected rejected (counted by code, no model)
//   filer B   withdraws A's filing               refused: only the filer may withdraw
//   filer A   files the same translation again   refused: the question has been answered
//   filer B   withdraws its own filing           executed
//
// Everything goes to deployments/studionet-activity.json, apart from the demo's
// own record, so the demo and the tests that replay it are untouched. Then
// `pnpm evidence:activity` writes EVIDENCE-ACTIVITY.md from the chain.

import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { createAccount, generatePrivateKey } from "genlayer-js";
import { PKG, RECORD_FILE, clientFor, loadEnv, network, readRetry, recorder } from "./lib.mjs";

loadEnv();
const net = network();
if (net.name !== "studionet") throw new Error("the activity round makes throwaway wallets; run it on studionet");
const address = JSON.parse(readFileSync(RECORD_FILE, "utf8")).contract;
const data = JSON.parse(readFileSync(path.join(PKG, "demo", "activity.json"), "utf8"));
const OUT = path.join(PKG, "deployments", "studionet-activity.json");

const a = createAccount(generatePrivateKey());
const b = createAccount(generatePrivateKey());
const asA = clientFor(net, a);
const asB = clientFor(net, b);
const ro = clientFor(net, null);
const read = (fn, args = []) => readRetry(() => ro.readContract({ address, functionName: fn, args }));

const first = Number(await read("count"));
const [fa, fb] = [first, first + 1];
console.log(`\ncontract ${address} (already deployed, ${first} filings on it)\n  filer A ${a.address}\n  filer B ${b.address}`);

const args = (f) => [f.title, data.source_lang, data.target_lang, f.source.join("|"), f.translation.join("|")];
const rec = recorder();
await rec.write(asA, a, address, "certify", args(data.faithful), { step: `filing ${fa}: a faithful translation (expected certified)` });
await rec.write(asB, b, address, "certify", args(data.counted), { step: `filing ${fb}: both numbers changed (expected rejected, no model)` });
await rec.write(asB, b, address, "withdraw", [fa], { step: `filer B withdraws filing ${fa}`, expect: "refused" });
await rec.write(asA, a, address, "certify", args(data.faithful), { step: "the same translation filed again", expect: "refused" });
await rec.write(asB, b, address, "withdraw", [fb], { step: `filer B withdraws its own filing ${fb}` });

const plain = (v) => JSON.parse(JSON.stringify(v, (_, x) => (typeof x === "bigint" ? Number(x) : x instanceof Map ? Object.fromEntries(x) : x)));
const filings = {};
for (const id of [fa, fb]) {
  filings[id] = {
    filing: plain(await read("filing", [id])),
    segments: plain(await read("segments_of", [id])).segments,
    standing: await read("standing", [id]),
  };
}
writeFileSync(OUT, JSON.stringify({
  network: net.name,
  contract: address,
  accounts: { filer_a: a.address, filer_b: b.address },
  steps: rec.steps,
  filings,
}, null, 2) + "\n");

for (const [id, f] of Object.entries(filings)) {
  console.log(`  filing ${id}  ${f.filing.verdict.padEnd(12)} ${f.segments.map((s) => `${s.reading}(${s.how})`).join(" ")}  standing ${f.standing}`);
}
console.log(`  written    ${path.relative(PKG, OUT)}\n`);
