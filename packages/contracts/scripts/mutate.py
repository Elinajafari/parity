"""Mutation pass: break every defence on purpose, confirm a test notices.

Passing tests prove nothing on their own. Each entry below is a small edit to
the contract that removes a defence. The suite must fail for every one of them,
and this script records WHICH test caught it, so the table in the README is
measured rather than claimed.

    python scripts/mutate.py            # run them all, print what caught what
    python scripts/mutate.py --md       # emit the markdown table for the README

An escaping mutation is a finding, not a nuisance: either a missing test, or a
later defence strict enough that an earlier test can no longer fail. The script
exits non-zero if anything escapes, and refuses to run on a red baseline.

Three rules keep the harness honest:

  * the unmutated suite must be green before anything is mutated;
  * a find string that is missing, or matches more than once, is a failure of
    the harness, never a skip, so refactoring cannot quietly turn a row off;
  * scripts/lift.py runs inside every mutated copy before the suite, so the lib
    parity test can never stand in for the behavioural test a mutation deserves.
"""

import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).absolute().parent.parent
TARGET = "parity.py"

FOLD = "        out.append(forward[i] if forward[i] == reverse_unreversed[i] else UNCLEAR)"
FENCE = '    return str(raw).replace("<", "(").replace(">", ")").replace("[", "(").replace("]", ")")'

MUTATIONS = [
    # -- the count: numbers decided without a model
    ("Persian digits are not read as digits",
     "    if PERSIAN_ZERO <= o <= PERSIAN_ZERO + 9:\n        return str(o - PERSIAN_ZERO)\n", ""),
    ("Arabic-Indic digits are not read as digits",
     "    if ARABIC_ZERO <= o <= ARABIC_ZERO + 9:\n        return str(o - ARABIC_ZERO)\n", ""),
    ("the Persian block is read one digit off",
     "        return str(o - PERSIAN_ZERO)", "        return str(o - PERSIAN_ZERO + 1)"),
    ("leading zeros make 05 and 5 different numbers",
     "    return sorted(str(int(r)) for r in runs)", "    return sorted(runs)"),
    ("numbers are compared in the order they appear, so word order breaks them",
     "    return sorted(str(int(r)) for r in runs)", "    return [str(int(r)) for r in runs]"),
    ("the last number in a text is dropped",
     '    if cur != "":\n        runs.append(cur)\n    return sorted', "    return sorted"),
    ("a number written in words counts as a mismatch",
     "    if len(a) == 0 or len(b) == 0:\n        return False\n", ""),
    ("the count never fires", "    return a != b", "    return False"),
    ("a counted pair is sent to the model anyway",
     "            if numbers_differ(sources[k], targets[k]):", "            if False:"),
    ("a counted pair is marked faithful",
     "                readings[k] = ALTERED\n                hows[k] = COUNTED",
     "                readings[k] = FAITHFUL\n                hows[k] = COUNTED"),

    # -- the mirror
    ("a disagreement between the orders keeps the forward reading", FOLD, "        out.append(forward[i])"),
    ("a disagreement between the orders folds to faithful", FOLD, FOLD.replace("else UNCLEAR", "else FAITHFUL")),
    ("a disagreement between the orders folds to altered", FOLD, FOLD.replace("else UNCLEAR", "else ALTERED")),
    ("the reversed pass is never asked",
     "                rev, _ = read_once(t, sl, tl, r_src, r_tgt, m)",
     "                rev = list(reversed(fwd))"),
    ("the reversed answer is not read back into the filed order",
     "                folded = reconcile(fwd, list(reversed(rev)))",
     "                folded = reconcile(fwd, rev)"),
    ("the translations are not reversed with their sources",
     "            r_tgt = list(reversed(a_tgt))", "            r_tgt = list(a_tgt)"),

    # -- reading the model
    ("a slot with an unknown token is read as empty",
     '        t = normalise_token(p)\n        if t == "":\n            return None\n', "        t = normalise_token(p)\n"),
    ("any word is accepted as a token", '    if s in TOKENS:\n        return s\n    return ""', "    return s"),
    ("an unusable answer is not retried", "    for _ in range(2):", "    for _ in range(1):"),
    ("an unusable answer is read as unclear",
     '    raise gl.vm.UserError(f"{ERR_LLM} the model gave no usable reading of the {n} pairs")',
     '    return [UNCLEAR] * n, ""'),
    ("an answer that is not an object crashes the block", "        if isinstance(raw, dict):", "        if True:"),

    # -- the validator
    ("the free structural layer is skipped",
     "                if not structurally_sound(proposed, m):\n                    return False\n                try:",
     "                try:"),
    ("a validator agrees with a leader that raised",
     "                    # An [LLM_ERROR] is never agreed with.\n                    return False",
     "                    # An [LLM_ERROR] is never agreed with.\n                    return True"),
    ("a validator trusts the leader",
     '                return parity_agrees(parse_proposal(mine["readings"], m), proposed, m)',
     "                return True"),
    ("a validator whose own model failed agrees",
     "                except gl.vm.UserError:\n                    return False",
     "                except gl.vm.UserError:\n                    return True"),
    ("agreement compares the first pair only", "    return mine == theirs", "    return mine[0] == theirs[0]"),
    ("the structural check accepts any word",
     "    for t in vector:\n        if t not in TOKENS:\n            return False\n", ""),
    ("the structural check accepts any length",
     "    if vector is None or n == 0 or len(vector) != n:", "    if vector is None or n == 0:"),

    # -- the verdict
    ("an altered pair does not reject", "    if ALTERED in readings:\n        return REJECTED\n", ""),
    ("an unclear pair certifies", "    if UNCLEAR in readings:\n        return INCONCLUSIVE\n", ""),
    ("unclear outranks altered",
     "    if ALTERED in readings:\n        return REJECTED\n    if UNCLEAR in readings:\n        return INCONCLUSIVE\n",
     "    if UNCLEAR in readings:\n        return INCONCLUSIVE\n    if ALTERED in readings:\n        return REJECTED\n"),
    ("the counted pairs are not counted on the filing",
     "                n_counted=u256(hows.count(COUNTED)),", "                n_counted=u256(0),"),

    # -- the registry
    ("the same translation can be checked again", "        if seen > 0:", "        if False:"),
    ("the replay guard ignores the target language",
     'return digest(clean_text(source_lang).lower() + "\\n" + clean_text(target_lang).lower() + "\\n"',
     'return digest(clean_text(source_lang).lower() + "\\n" + "\\n"'),
    ("the replay guard is defeated by capital letters",
     'return digest(clean_text(source_lang).lower() + "\\n" + clean_text(target_lang).lower() + "\\n"',
     'return digest(clean_text(source_lang) + "\\n" + clean_text(target_lang) + "\\n"'),
    ("a filing is not linked to the filer's previous one",
     "                prev_by_filer=u256(int(self.last_by_filer.get(sender, u256(0)))),",
     "                prev_by_filer=u256(0),"),
    ("the filer's newest filing is not recorded", "        self.last_by_filer[sender] = u256(idx + 1)\n", ""),
    ("the filing is not indexed by its key", "        self.by_key[key] = u256(idx + 1)\n", ""),
    ("anyone may withdraw anyone's filing", "        if gl.message.sender_address != f.filer:", "        if False:"),
    ("a filing can be withdrawn twice", "        if bool(f.withdrawn):\n            raise", "        if False:\n            raise"),
    ("standing forgets a withdrawal", "        if bool(f.withdrawn):\n            return WITHDRAWN\n", ""),
    ("a negative filing id reads the newest filing",
     "        if i < 0 or i >= len(self.filings):", "        if i >= len(self.filings):"),
    ("a listing walks past the page limit", "        while i > 0 and len(rows) < PAGE:", "        while i > 0:"),

    # -- input bounds
    ("mismatched segment counts are paired up anyway", "        if len(sources) != len(targets):", "        if False:"),
    ("empty segments are dropped, silently realigning every pair after them",
     '    return [clean_text(part) for part in str(text).split("|")]',
     '    return [clean_text(part) for part in str(text).split("|") if clean_text(part) != ""]'),
    ("more than eight segments are accepted", "        if n > MAX_SEGMENTS:", "        if False:"),
    ("a one-character segment is accepted", "            if len(seg) < MIN_SEGMENT:", "            if False:"),
    ("an over-long segment is accepted", "            if len(seg) > MAX_SEGMENT:", "            if False:"),
    ("a translation into the same language is accepted", "        if sl.lower() == tl.lower():", "        if False:"),
    ("the title is unbounded", "        if len(t) < MIN_TITLE or len(t) > MAX_TITLE:", "        if False:"),
    ("a language name is unbounded",
     "            if len(lang) < MIN_LANG or len(lang) > MAX_LANG:", "            if False:"),

    # -- the prompt boundary
    ("the fence is removed", FENCE, "    return str(raw)"),
    ("the fence leaves square brackets", FENCE, '    return str(raw).replace("<", "(").replace(">", ")")'),
    ("the fence deletes instead of replacing", FENCE,
     '    return str(raw).replace("<", "").replace(">", "").replace("[", "").replace("]", "")'),
    ("the translation rows reach the prompt unfenced",
     '    tgt_rows = "\\n".join(f"[{k}] {fence(targets[k])}" for k in range(n))',
     '    tgt_rows = "\\n".join(f"[{k}] {targets[k]}" for k in range(n))'),
    ("the source rows reach the prompt unfenced",
     '    src_rows = "\\n".join(f"[{k}] {fence(sources[k])}" for k in range(n))',
     '    src_rows = "\\n".join(f"[{k}] {sources[k]}" for k in range(n))'),
    ("the title reaches the prompt unfenced", "{fence(title)}", "{title}"),
    ("the language names reach the prompt unfenced",
     "from {fence(source_lang)} to {fence(target_lang)}", "from {source_lang} to {target_lang}"),
    ("the prompt no longer states the count",
     "Number of pairs: {n}. Number of tokens in your answer: {n}.", "Answer carefully."),
    ("the answer example is a real answer",
     '    example = "|".join(f"t{k}" for k in range(n))', '    example = "|".join("faithful" for k in range(n))'),
    ("a leader's reason is stored as sent",
     '            why = sanitise_reason(res.get("because", ""))', '            why = str(res.get("because", ""))'),
    ("a leader's reason is stored uncapped",
     '    return " ".join("".join(out).split())[:limit]', '    return " ".join("".join(out).split())'),
]


PYTEST = [sys.executable, "-m", "pytest", "tests/", "-x", "-q", "--no-header", "-p", "no:cacheprovider"]


def copy_repo(tmp):
    dst = pathlib.Path(tmp) / "repo"
    # The live record stays behind: a mutant is judged by the offline suite,
    # and the record's own checks would only re-read the chain's answers.
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(
        "__pycache__", ".pytest_cache", ".git", "artifacts", "*.pyc", "node_modules", "deployments"))
    # tests/test_vectors.py and tests/test_shape.py read ../shared; a mutant
    # must face the same vectors and the same described surface.
    shared = pathlib.Path(tmp) / "shared"
    shared.mkdir()
    for name in ("number-vectors.json", "contract-shape.json"):
        shutil.copy(ROOT.parent / "shared" / name, shared / name)
    return dst


def run_one(label, find, replace):
    with tempfile.TemporaryDirectory() as tmp:
        dst = copy_repo(tmp)
        target = dst / TARGET
        src = target.read_text(encoding="utf-8")
        hits = src.count(find)
        if hits == 0:
            return "PATTERN NOT FOUND", None
        if hits > 1:
            return "PATTERN NOT UNIQUE", None
        target.write_text(src.replace(find, replace, 1), encoding="utf-8", newline="\n")
        subprocess.run([sys.executable, "scripts/lift.py"], cwd=dst, capture_output=True)
        proc = subprocess.run(PYTEST, cwd=dst, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
        if proc.returncode == 0:
            return "ESCAPED", None
        text = proc.stdout + proc.stderr
        m = re.search(r"^(?:FAILED|ERROR) (\S+?)::(\S+?)(?:\[|\s|$)", text, re.M)
        if m:
            return "caught", m.group(2).split("::")[-1]
        m = re.search(r"^E\s+(\w*(?:Error|Exception))", text, re.M)
        if m:
            return "caught", m.group(1) + " at import"
        return "caught", "unnamed failure"


def baseline_is_green():
    with tempfile.TemporaryDirectory() as tmp:
        dst = copy_repo(tmp)
        proc = subprocess.run(PYTEST, cwd=dst, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="store_true", help="emit the README table")
    args = ap.parse_args()

    green, tail = baseline_is_green()
    if not green:
        print("the unmutated suite is not green; every mutation would look caught:\n" + tail, file=sys.stderr)
        return 2

    rows, escaped = [], []
    for label, find, replace in MUTATIONS:
        status, test = run_one(label, find, replace)
        if status == "caught":
            rows.append((label, test))
            if not args.md:
                print("  caught   %-70s %s" % (label, test), flush=True)
        else:
            escaped.append((label, status))
            print("  %-8s %s" % (status, label), file=sys.stderr, flush=True)

    if args.md:
        print("| Mutation | Caught by |")
        print("|---|---|")
        for label, test in rows:
            print("| %s | `%s` |" % (label, test))
    else:
        print()
        print("  %d mutations, %d caught, %d escaped" % (len(MUTATIONS), len(rows), len(escaped)))
    return 1 if escaped else 0


if __name__ == "__main__":
    sys.exit(main())
