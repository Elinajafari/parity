"""
The shared vectors are the contract's own answers.

packages/shared/number-vectors.json is what the TypeScript port of
the number check is tested against. If the vectors were hand-written, the port
could agree with them and disagree with the contract. So this test recomputes
every vector from the contract's functions and fails if any has drifted:
regenerate with `UPDATE_VECTORS=1 pytest tests/test_vectors.py`.
"""

import json
import os
import pathlib

import glsim as S

M = S.load_contract("parity.py")
VECTORS = pathlib.Path(__file__).absolute().parent.parent.parent / "shared" / "number-vectors.json"


def recompute(v):
    return {
        "numbers_of": [{"text": x["text"], "numbers": M.numbers_of(x["text"])} for x in v["numbers_of"]],
        "numbers_differ": [{"source": x["source"], "target": x["target"],
                            "differ": M.numbers_differ(x["source"], x["target"])} for x in v["numbers_differ"]],
        "verdict_of": [{"readings": x["readings"], "verdict": M.verdict_of(x["readings"])} for x in v["verdict_of"]],
        "clean_text": [{"raw": x["raw"], "clean": M.clean_text(x["raw"])} for x in v["clean_text"]],
        "filing_key": [{**x, "key": M.filing_key(x["source_lang"], x["target_lang"], x["sources"], x["targets"])}
                       for x in v["filing_key"]],
    }


def test_every_shared_vector_is_what_the_contract_computes():
    stored = json.loads(VECTORS.read_text(encoding="utf-8"))
    fresh = recompute(stored)
    if os.environ.get("UPDATE_VECTORS"):
        VECTORS.write_text(json.dumps(fresh, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    assert stored == fresh, "number-vectors.json has drifted from the contract; UPDATE_VECTORS=1"


def test_the_vectors_cover_every_script_and_both_outcomes():
    stored = json.loads(VECTORS.read_text(encoding="utf-8"))
    texts = "".join(x["text"] for x in stored["numbers_of"])
    assert any(0x06F0 <= ord(c) <= 0x06F9 for c in texts) and any(0x0660 <= ord(c) <= 0x0669 for c in texts)
    assert {x["differ"] for x in stored["numbers_differ"]} == {True, False}
    assert {x["verdict"] for x in stored["verdict_of"]} == {"certified", "rejected", "inconclusive"}
