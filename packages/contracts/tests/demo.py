"""The demo's data, loaded from demo/demo.json.

scripts/seed.mjs sends exactly these strings to StudioNet and the tests replay
them offline, so the demo on the explorer and the demo the tests check are one
file, and cannot drift apart.
"""

import json
import pathlib

_DATA = json.loads((pathlib.Path(__file__).absolute().parent.parent / "demo" / "demo.json").read_text(encoding="utf-8"))

TITLE = _DATA["title"]
SOURCE_LANG = _DATA["source_lang"]
TARGET_LANG = _DATA["target_lang"]
SOURCE = _DATA["source"]
_BY_NAME = {f["name"]: f["translation"] for f in _DATA["filings"]}
FAITHFUL = _BY_NAME["faithful"]
WRONG_NUMBER = _BY_NAME["wrong_number"]
DROPPED_NOT = _BY_NAME["dropped_not"]
FILINGS = [(f["expected"], f["translation"]) for f in _DATA["filings"]]


def joined(segments):
    return "|".join(segments)
