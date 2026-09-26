"""Measure, do not estimate. Write the numbers into README.md.

    python scripts/measure.py            # measure and print, write nothing
    python scripts/measure.py --write    # measure and write between the markers

Three sections of the README are generated, between `<!-- measured:NAME:start -->`
and `<!-- measured:NAME:end -->`:

    tests        the suite's own count, from a run made now
    mutations    the mutation table, from a run made now
    deployment   the live run, rendered from deployments/studionet.json, or a
                 plain "not deployed yet" until the deploy and seed scripts have run

It refuses to write anything if the suite is red, if a mutation escapes, or if
the recorded deployment is not of the contract file in this repository.
"""

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).absolute().parent.parent
README = ROOT / "README.md"
RECORD = ROOT / "deployments" / "studionet.json"
SOURCE = ROOT / "parity.py"
EXPLORER = "https://explorer-studio.genlayer.com"

NOT_DEPLOYED = ("Not deployed yet. Run `pnpm deploy:contract` and `pnpm seed:contract` (they deploy this exact file to StudioNet and "
                "drive every path, refusals included), then `python scripts/measure.py --write` to render "
                "the record here.")


def tx(h):
    return f"[`{h[:10]}...`]({EXPLORER}/tx/{h})"


def cell(text):
    return str(text).replace("|", "/")


def run_tests():
    proc = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"],
                          cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-1]
    if proc.returncode != 0:
        raise SystemExit("the suite is red; nothing written:\n" + tail)
    passed = int(re.search(r"(\d+) passed", tail).group(1))
    skipped = int((re.search(r"(\d+) skipped", tail) or [0, 0])[1])
    return passed, skipped


def run_mutations():
    proc = subprocess.run([sys.executable, "scripts/mutate.py", "--md"], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise SystemExit("a mutation escaped or the baseline is red; nothing written:\n" + proc.stderr[-2000:])
    rows = [line for line in proc.stdout.splitlines() if line.startswith("| ") and "`" in line]
    return len(rows), proc.stdout.strip()


def render_deployment(rec):
    here = hashlib.sha256(SOURCE.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    if rec["source_sha256"] != here:
        raise SystemExit("deployments/studionet.json records a different contract file; redeploy "
                         "with pnpm deploy:contract before measuring")
    addr = rec["contract"]
    deploy = [s for s in rec["steps"] if s["step"] == "deploy"][0]
    filed = [s for s in rec["steps"] if s.get("method") == "certify" and s["ok"]]
    out = [
        f"Deployed on studionet at [`{addr}`]({EXPLORER}/address/{addr}) (deploy {tx(deploy['tx'])}). "
        f"Every value below was read back from the chain by `scripts/seed.mjs` and written to "
        f"[`deployments/studionet.json`](deployments/studionet.json); none of it is typed by hand.",
        "",
        "| # | Translation | Readings, pair by pair | Verdict | Standing | Transaction |",
        "|---|---|---|---|---|---|",
    ]
    labels = ["faithful", "one number changed (30 to 13)", "one negation dropped"]
    for k, f in enumerate(rec["filings"]):
        readings = " / ".join(f"{s['reading']} ({s['how']})" for s in rec["segments"][k])
        label = labels[k] if k < len(labels) else f["title"]
        out.append(f"| {k} | {label} | {readings} | **{f['verdict']}** | {rec['standing'][k]} | "
                   f"{tx(filed[k]['tx'])} |")
    out += ["", "The reason each leader gave (leader-supplied, sanitised, not part of consensus):", ""]
    for k, f in enumerate(rec["filings"]):
        out.append(f"- **{k}, {f['verdict']}:** {f['why'] or 'no model was asked: every pair was counted'}")
    out += ["", "What the contract refused, on chain, and the one write that followed:", "",
            "| Step | Outcome | Transaction |", "|---|---|---|"]
    for s in rec["steps"]:
        if s["step"] == "deploy" or (s.get("method") == "certify" and s["ok"]):
            continue
        outcome = "ok" if s["ok"] else "refused: " + cell(s["refusal"].replace("[EXPECTED] ", ""))
        out.append(f"| {s['step']} | {outcome} | {tx(s['tx'])} |")
    out += ["", "`tests/test_runbook.py::TestTheRecord` replays these readings through this repository's "
                "contract, and checks that every counted pair is exactly one the number check picks."]
    return "\n".join(out)


def replace(text, name, body):
    start, end = f"<!-- measured:{name}:start -->", f"<!-- measured:{name}:end -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"README.md has no {name} markers")
    return pattern.sub(lambda _: f"{start}\n{body}\n{end}", text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    passed, skipped = run_tests()
    tests = (f"Measured: **{passed} passed**, {skipped} skipped, including the checks of the live record "
             f"in `deployments/studionet.json`, which run once `pnpm seed:contract` has written it. "
             f"The same record is checked against the chain itself by `pnpm e2e:contract`.")
    n, table = run_mutations()
    mutations = f"Measured: **{n} mutations, {n} caught, 0 escaped.**\n\n{table}"
    if RECORD.exists():
        rec = json.loads(RECORD.read_text(encoding="utf-8"))
        deployment = render_deployment(rec)
        where = rec["contract"]
    else:
        deployment, where = NOT_DEPLOYED, "not deployed yet"

    text = README.read_text(encoding="utf-8")
    text = replace(text, "tests", tests)
    text = replace(text, "mutations", mutations)
    text = replace(text, "deployment", deployment)
    print(f"  tests      {passed} passed, {skipped} skipped")
    print(f"  mutations  {n} caught, 0 escaped")
    print(f"  deployment {where}")
    if args.write:
        README.write_text(text, encoding="utf-8", newline="\n")
        print("  README.md written")


if __name__ == "__main__":
    main()
