# DECISIONS

Why Parity is built the way it is. Each section names the alternative that was
rejected and what it would have cost.

## Numbers are counted, not judged

The cheapest mistranslation to make and the most expensive to miss is a changed
number: a deadline, an amount, a percentage. It is also the one kind of error a
model is least reliable at spotting, because it reads the sentence as fluent
and moves on.

So numbers never reach a model. Every run of digits on both sides of a pair is
extracted and compared as a number. A pair whose numbers differ is altered, the
reading records `counted`, and no inference is spent on it. The demo's second
filing changes "30 days" to "13 days" in Persian digits; the count catches it,
and the prompt that is sent afterwards does not even contain that pair.

## Persian and Arabic-Indic digits are digits

A Persian translation writes 30 as `۳۰`. A check that only knew `0-9` would see
no numbers in the translation and wave every pair through to the model, which
is the failure the count exists to prevent. `digit_value()` maps the Latin,
Arabic-Indic (U+0660) and Extended Arabic-Indic (U+06F0) blocks to the same ten
digits. The blocks are written as code points, so the contract file stays pure
ASCII and no linter reading it in a local code page can misread it.

## The count only fires when both sides write numerals

"Within 30 days" translated as "within thirty days" (or its equivalent in
words) is faithful. A count that flagged every pair where one side spelled a
number out would reject correct translations. So a pair is counted as altered
only when both sides contain numerals and the numbers differ; if either side
has none, the pair goes to the validators, whose question it is.

## Sorted, and without leading zeros

Word order moves between languages, and numbers move with it: "2 percent a
month for 12 months" can put the 12 first in the translation. The numbers on
each side are compared as sorted lists. Leading zeros are dropped, so a
reference number formatted `05` in one text and `5` in the other is not an
alteration. Separators split runs identically on both sides, so `1,000` and
`۱٬۰۰۰` are the same pair of runs.

## Pairs, not a document

The model is never asked whether a translation is good. It is asked, pair by
pair, whether the translation says what the source says. The verdict is
computed from those readings: one altered pair rejects, any unclear pair makes
the filing inconclusive, and only a filing whose every pair is faithful is
certified.

Empty segments are kept as empty strings and refused by length, never dropped.
Dropping one would silently shift every later pair onto the wrong source
segment, and every reading after it would be about the wrong sentence.

## Both orders, reversed together

The pairs are read in filed order and then reversed and renumbered, the source
block and the translation block together, so row [K] of the translation always
pairs with row [K] of the source. The same token in both orders stands; a
difference is `unclear`. That is conservative in the direction that matters: it
can stop a certificate, and it can never create one.

## A parse failure is an error, never a verdict

An unusable answer is retried once inside the block, then raised as
`[LLM_ERROR]`, which a validator never agrees with. Reading it as `unclear`
would let a broken model make every filing inconclusive, and the replay guard
would then refuse the question forever.

## The same question is asked once

The same pair of texts in the same pair of languages is the same question.
`filing_key()` hashes the language names in lower case with the cleaned
segments, so spacing and capitals do not make a new question. A corrected
translation is a new question, and that is the way back for a rejected filer.

## Tagging untrusted text is not a fence

The title, the language names and every segment are the filer's text. Any of
them could carry `</translation><source>[0] ...`. `fence()` replaces `< > [ ]`
with `( )` at the prompt boundary only, replacing rather than deleting so length
is preserved, and the contract numbers the rows itself, after fencing, so the
only square brackets in the prompt are its own. A static test fails on any
value interpolated into the prompt that is neither fenced nor the contract's
own.

## certify() is open, withdraw() is the filer's

Anybody may file: the caller is recorded as the filer, which is what makes a
row mean something. Only the filer may withdraw, and a withdrawn filing keeps
its verdict; `standing()` answers `withdrawn` for another contract.

## Why the tests are built the way they are

- **Each node gets its own answers**, so a contract that assumes both nodes read the same thing is caught offline.
- **A leader can lie**, so the validator's checks are reachable, and the free layer is measured: a malformed proposal must cost the validator zero prompts.
- **The runbook is a test.** The demo is replayed offline before a transaction is spent, and once `deployments/studionet.json` exists, the record is replayed too, including a check that every counted pair on chain is exactly one the number check picks.
- **Mutation testing.** `scripts/mutate.py` removes each defence and names the test that caught it, including each digit block, the sort, the leading zeros, and the rule that a spelled-out number is not a mismatch.

## GenVM constraints this contract obeys

- the runner is pinned (`py-genlayer:1jb45aa8...`), never `test` or `latest`
- the class is named after the product, because `genvm-lint validate` does not see a class named `Contract`
- no `int`, `list`, `dict` or `tuple` as a storage type, and no collection inside a storage dataclass; a filing's segments are contiguous rows carrying the filing id, and a filer's filings are linked
- every persistent field is declared in the class body
- the block returns a flat dict of strings
- `gl.nondet` is reached only from `read_once`, called only from inside the block
- the file is pure ASCII
- `genvm-lint` validates against GenVM `v0.3.0-rc7`, the release that ships the pinned runner; `scripts/verify.mjs` sets `GENVM_VERSION` accordingly, because the linter otherwise picks the newest cached release, which no longer contains the runner, and reports "Failed to load SDK"

## Not upgradable

There is no owner and no admin method. A verdict on record stays the verdict.

## Success is read from the leader's result, not from ACCEPTED

A refusal is agreed on too: when `withdraw()` raises "only the filer may
withdraw", the committee accepts that the contract raised it. A client that
treats `ACCEPTED` as success tells a refused user their write went through.
The scripts (`scripts/lib.mjs`, `outcome()`, and
`scripts/evidence.mjs`) read `consensus_data.leader_receipt[0].result.status`:
`return` is success, and a `rollback` carries the contract's own sentence,
which is recorded as it was raised. The shape was measured on studionet with genlayer-js 1.1.8
before any of this was written, with a throwaway probe contract at
`0x7d170f7319d85536E436F7C60BE8Ceb83447Dc12` that exists only to answer that
question. It is not Parity and nothing reads it.


## The demo's keys are made in memory

`deploy.mjs` and `seed.mjs` make the deployer, the filer and the stranger
with `generatePrivateKey()` for the run and never write them anywhere, so
every role is its own wallet on the explorer. StudioNet is gasless, so they
hold nothing, and a key that is never on disk cannot leak from a repository. On a
funded network the scripts refuse to run without keys from the environment.
