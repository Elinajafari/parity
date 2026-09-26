"""
The demo, replayed offline.

scripts/seed.mjs puts the demo on StudioNet from demo/demo.json. This file
replays the same filings through the real contract in the simulator, so a demo
that could not succeed is caught before a transaction is spent on it.

When deployments/studionet.json exists, the replay goes further: it feeds the
simulator the readings the validators actually agreed on and checks that this
repository's contract stores exactly what the deployed one stored, that the
counted pairs are exactly the ones the number check picks, and that it refuses
exactly where the deployed one refused.

    pytest tests/test_runbook.py -v
"""

import hashlib
import json
import pathlib

import pytest

import glsim as S

CONTRACT_PATH = "parity.py"
M = S.load_contract(CONTRACT_PATH)
RECORD = pathlib.Path("deployments/studionet.json")

import demo as D

FILER = "0x" + "a1" * 20
OTHER = "0x" + "b2" * 20

CLOSING = [
    ("filer", "certify", D.FAITHFUL[:2], "refused"),
    ("other", "certify", D.FAITHFUL, "refused"),
    ("other", "withdraw", 1, "refused"),
    ("filer", "withdraw", 1, "ok"),
]

# what the validators are expected to read, over the pairs that are read
EXPECTED = [
    "faithful|faithful|faithful",    # filing 0: all three pairs read
    "faithful|faithful",             # filing 1: pair 0 is counted
    "faithful|faithful|altered",     # filing 2: all three read
]


def mocks_for(translation, vector):
    asked = [k for k in range(len(D.SOURCE)) if not M.numbers_differ(D.SOURCE[k], translation[k])]
    srcs = [D.SOURCE[k] for k in asked]
    if not srcs:
        return {}
    rev = "|".join(reversed(vector.split("|")))
    return {"<source>\n[0] " + srcs[0]: {"readings": vector, "because": "replayed"},
            "<source>\n[0] " + srcs[-1]: {"readings": rev if len(srcs) > 1 else vector, "because": "replayed"}}


def replay(vectors):
    c = S.deploy(CONTRACT_PATH)
    who = {"filer": FILER, "other": OTHER}
    outcomes = []
    for (_, translation), vector in zip(D.FILINGS, vectors):
        S.set_mocks(leader_prompts=mocks_for(translation, vector))
        S.set_sender(FILER)
        try:
            S.call(c, "certify", D.TITLE, D.SOURCE_LANG, D.TARGET_LANG, D.joined(D.SOURCE), D.joined(translation))
            outcomes.append(("ok", ""))
        except S.UserError as e:
            outcomes.append(("refused", e.message))
    for actor, method, arg, _ in CLOSING:
        S.set_mocks()
        S.set_sender(who[actor])
        try:
            if method == "certify":
                S.call(c, "certify", D.TITLE, D.SOURCE_LANG, D.TARGET_LANG, D.joined(D.SOURCE), D.joined(arg))
            else:
                S.call(c, method, arg)
            outcomes.append(("ok", ""))
        except S.UserError as e:
            outcomes.append(("refused", e.message))
    return c, outcomes


class TestDemoData:
    def test_every_translation_has_one_segment_per_source_segment(self):
        for _, translation in D.FILINGS:
            assert len(translation) == len(D.SOURCE)
            for seg in translation + D.SOURCE:
                assert M.MIN_SEGMENT <= len(M.clean_text(seg)) <= M.MAX_SEGMENT and "|" not in seg

    def test_each_demo_filing_changes_one_segment_from_the_faithful_one(self):
        for _, translation in D.FILINGS[1:]:
            assert sum(a != b for a, b in zip(translation, D.FAITHFUL)) == 1

    def test_the_wrong_number_is_the_only_pair_the_count_catches(self):
        assert [M.numbers_differ(s, t) for s, t in zip(D.SOURCE, D.WRONG_NUMBER)] == [True, False, False]
        assert not any(M.numbers_differ(s, t) for s, t in zip(D.SOURCE, D.FAITHFUL))
        assert not any(M.numbers_differ(s, t) for s, t in zip(D.SOURCE, D.DROPPED_NOT))

    def test_the_faithful_translation_carries_the_same_numbers_in_persian_digits(self):
        assert M.numbers_of(D.FAITHFUL[0]) == ["30"] and M.numbers_of(D.FAITHFUL[1]) == ["2"]
        assert all(ord(ch) < 48 or ord(ch) > 57 for ch in "".join(D.FAITHFUL))


class TestReplay:
    def test_the_demo_succeeds_and_refuses_exactly_where_it_says(self):
        _, outcomes = replay(EXPECTED)
        assert [o for o, _ in outcomes] == ["ok"] * 3 + [r[-1] for r in CLOSING]

    def test_the_refusals_say_why(self):
        _, outcomes = replay(EXPECTED)
        msgs = [m for o, m in outcomes if o == "refused"]
        assert "3 segments and the translation 2" in msgs[0]
        assert "already checked as filing 0" in msgs[1]
        assert "only the filer" in msgs[2]

    def test_the_expected_readings_give_the_expected_verdicts(self):
        c, _ = replay(EXPECTED)
        assert [c.filing(k)["verdict"] for k in range(3)] == [v for v, _ in D.FILINGS]
        assert [c.filing(k)["counted"] for k in range(3)] == [0, 1, 0]
        assert c.standing(1) == "withdrawn"


@pytest.mark.skipif(not RECORD.exists(), reason="no deployment recorded yet: pnpm seed:contract")
class TestTheRecord:
    def _record(self):
        return json.loads(RECORD.read_text(encoding="utf-8"))

    def test_the_record_is_of_this_source(self):
        here = hashlib.sha256(pathlib.Path(CONTRACT_PATH).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        assert self._record()["source_sha256"] == here, "the deployed contract is not this file; redeploy"

    def test_the_counted_pairs_are_exactly_the_ones_the_number_check_picks(self):
        for segs in self._record()["segments"]:
            for s in segs:
                assert (s["how"] == "counted") == M.numbers_differ(s["source"], s["target"])

    def test_every_step_on_chain_did_what_the_demo_expected(self):
        steps = [s for s in self._record()["steps"] if s["step"] != "deploy"]
        assert [("ok" if s["ok"] else "refused") for s in steps] == ["ok"] * 3 + [r[-1] for r in CLOSING]

    def test_this_contract_stores_what_the_deployed_one_stored(self):
        rec = self._record()
        agreed = ["|".join(s["reading"] for s in segs if s["how"] == "read") for segs in rec["segments"]]
        c, _ = replay(agreed)
        for k, f in enumerate(rec["filings"]):
            mine = c.filing(k)
            for field in ("verdict", "altered", "unclear", "counted", "segments", "title", "withdrawn"):
                assert mine[field] == f[field], (k, field)
        assert [c.standing(k) for k in range(len(rec["filings"]))] == rec["standing"]
