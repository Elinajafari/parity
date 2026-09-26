# Parity - GenLayer Intelligent Contract

[`parity.py`](./parity.py) is the whole protocol: anyone files a source text
and its translation cut into pairs; the contract counts every pair's numbers
itself; validators read the remaining pairs by consensus, in two orders; the
verdict is arithmetic on their tokens, and another contract reads it in one
call.

## Core rule

```
a pair whose numbers differ is altered, and no model ever sees it
verdict = rejected   if any pair is altered
          inconclusive if any pair is unclear
          certified    only if every pair is faithful
```

The model is never asked for the verdict. It gives one token per pair, from a
closed set, and the contract does the rest.

## Lifecycle

```
filer:   certify(title, source_lang, target_lang, source, translation)
           -> bounds + replay guard (free) -> count numbers -> [validators read, both orders] -> verdict
filer:   withdraw(id)               the row and its verdict stay; standing() says withdrawn
anyone:  count, standing, filing, segments_of, find, filings_of
```

Judgment fails **closed**: an unusable model answer is retried once inside
the block and then raised as `[LLM_ERROR]`, which no validator agrees with.
It is never read as unclear, and never as a verdict.

## Deploy

```bash
pnpm install                          # from the repo root
pnpm deploy:contract                  # studionet, a deployer key made for this run
pnpm deploy:contract testnet-asimov   # needs DEPLOYER_PRIVATE_KEY in .env
pnpm seed:contract                    # the demo, recorded in deployments/studionet.json
pnpm e2e:contract                     # the record checked against the chain
pnpm verify:contract                  # deployed source == parity.py, and genvm-lint on it
pnpm evidence:contract                # EVIDENCE.md at the repo root, from the chain
```

Every script reads a transaction's outcome from the leader's result
(`return` or `rollback`), never from `ACCEPTED` alone: the committee accepts a
refusal too. Sends are nonce-guarded, so a lost answer is never sent twice.
Why each rule is the way it is: [DECISIONS.md](DECISIONS.md).

## Surface

| Thing | What it is |
|---|---|
| **Filing** | a title, two languages, and N pairs (N ≤ 8) of source and translation segments, the filer, and the verdict |
| **Segment** | one pair, its reading, and how it was decided: `counted` by code or `read` by validators |
| **Reading** | `faithful` · `altered` · `unclear` |
| **Verdict** | `certified` (every pair faithful) · `rejected` (any altered) · `inconclusive` (otherwise), computed, never asked for |
| **Standing** | the verdict, or `withdrawn` once the filer withdraws; the row and its verdict stay |
| **Key** | sha256 of both language names and both texts: the same translation is asked once |

| Write | Caller | Why |
|---|---|---|
| `certify(title, source_lang, target_lang, source, translation)` | anyone, deliberately | the caller is recorded as the filer |
| `withdraw(id)` | the filer | the row and its verdict stay; `standing()` reports it withdrawn |

| View | Returns |
|---|---|
| `count()` | number of filings |
| `standing(id)` | one word for another contract: `certified`, `rejected`, `inconclusive` or `withdrawn` |
| `filing(id)` | filer, title, languages, time, verdict, and how many pairs were altered, unclear and counted |
| `segments_of(id)` | every pair, its reading, and whether it was `counted` or `read` |
| `find(key)` | the filing under `filing_key(...)`, or -1 |
| `filings_of(address)` | a filer's filings, newest first, at most 20 |

```python
parity = gl.get_contract_at(Address(PARITY))
if parity.view().standing(filing_id) != "certified":
    raise gl.vm.UserError("[EXPECTED] that translation is not certified")
```

## How it holds together

```
certify()
  ├─ clean + bound every input            free: a refusal costs no model call
  ├─ count, per pair                      numbers_of(source) vs numbers_of(target)
  │     differ → altered (counted)        never shown to a model
  └─ nondet block
        leader                            validator
        read the remaining pairs          refuse a malformed vector (free)
        in filed order, then reversed     read both orders itself
        same token → it, else unclear     match the leader exactly, or disagree
                                          an [LLM_ERROR] is never agreed with
  verdict = arithmetic(tokens) → stored, with the leader's sentence labelled as not consensus
```

**The count.** For each pair the contract extracts every run of digits on both
sides and compares them as numbers:

| Rule | Why |
|---|---|
| `0-9`, Persian `۰-۹` and Arabic-Indic `٠-٩` are the same ten digits | a Persian translation writes 30 as `۳۰` |
| any non-digit splits a run | `1,000`, `1.000` and `۱٬۰۰۰` split the same way |
| leading zeros are dropped | `05` and `5` are one number |
| both sides are sorted | word order moves between languages, and numbers move with it |
| a pair differs only when **both** sides write numerals | a number spelled out in words is the validators' question |

**The reading.** The block sees the title, the two language names and the
numbered pairs still to be read, and gives one token per pair. It asks twice,
with the pairs in filed order and then reversed and renumbered, source and
translation reversed together. The same token in both orders stands; a
difference is `unclear`, which stops a certificate. The uncertainty goes into
the value, never into the comparison.

## Threat model

| Attack | What stops it |
|---|---|
| A leader lies about a reading | every validator reads both orders itself and must match exactly |
| A broken model "certifies" by failing | an unusable answer is retried once, then raised as `[LLM_ERROR]`, which no validator agrees with |
| A model is talked past a changed number | numbers never reach a model; they are counted |
| A reading that depends on the order it was shown | both orders inside one block; a difference is `unclear`, which blocks a certificate |
| Prompt injection inside a segment | `fence()` replaces `< > [ ]` at the prompt boundary and the contract numbers the rows itself; a static test fails on any unfenced interpolation |
| Shopping for a better verdict by refiling | the key covers both languages and both texts, so the same question is refused |
| Someone withdraws another's filing | `withdraw` checks the filer |
| A script reports "done" when the contract refused | success is the leader's `return`, not `ACCEPTED`; a `rollback` is recorded with the contract's own sentence |

## Tests

<!-- measured:tests:start -->
Measured: **100 passed**, 0 skipped, including the checks of the live record in `deployments/studionet.json`, which run once `pnpm seed:contract` has written it. The same record is checked against the chain itself by `pnpm e2e:contract`.
<!-- measured:tests:end -->

The suite runs on [`tests/glsim.py`](tests/glsim.py), a small GenVM stand-in
that executes the real contract file, gives the leader and the validator their
own mock answers, can make a leader lie, and refuses what GenVM refuses. What
each file covers, and what every demo transaction proves, is in
[tests/README.md](tests/README.md).

**The tests have teeth.** [`scripts/mutate.py`](scripts/mutate.py) removes every
defence one at a time and names the test that caught each mutant. It refuses to
run on a red baseline and exits non-zero if anything escapes.

<!-- measured:mutations:start -->
Measured: **62 mutations, 62 caught, 0 escaped.**

| Mutation | Caught by |
|---|---|
| Persian digits are not read as digits | `test_a_changed_number_is_counted_and_never_reaches_a_model` |
| Arabic-Indic digits are not read as digits | `test_every_script_s_digits_are_the_same_digits` |
| the Persian block is read one digit off | `test_a_faithful_translation_is_certified` |
| leading zeros make 05 and 5 different numbers | `test_numbers_are_runs_of_digits_sorted_without_leading_zeros` |
| numbers are compared in the order they appear, so word order breaks them | `test_numbers_are_runs_of_digits_sorted_without_leading_zeros` |
| the last number in a text is dropped | `test_numbers_are_runs_of_digits_sorted_without_leading_zeros` |
| a number written in words counts as a mismatch | `test_caller_text_is_stored_verbatim_and_fenced_only_at_the_prompt` |
| the count never fires | `test_a_changed_number_is_counted_and_never_reaches_a_model` |
| a counted pair is sent to the model anyway | `test_a_changed_number_is_counted_and_never_reaches_a_model` |
| a counted pair is marked faithful | `test_a_changed_number_is_counted_and_never_reaches_a_model` |
| a disagreement between the orders keeps the forward reading | `test_a_pair_the_two_orders_read_differently_is_unclear` |
| a disagreement between the orders folds to faithful | `test_a_pair_the_two_orders_read_differently_is_unclear` |
| a disagreement between the orders folds to altered | `test_a_pair_the_two_orders_read_differently_is_unclear` |
| the reversed pass is never asked | `test_a_pair_the_two_orders_read_differently_is_unclear` |
| the reversed answer is not read back into the filed order | `test_a_dropped_negation_is_read_as_altered` |
| the translations are not reversed with their sources | `test_the_reversed_prompt_reverses_both_blocks_together` |
| a slot with an unknown token is read as empty | `test_a_vector_is_all_or_nothing` |
| any word is accepted as a token | `test_a_vector_is_all_or_nothing` |
| an unusable answer is not retried | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| an unusable answer is read as unclear | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| an answer that is not an object crashes the block | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| the free structural layer is skipped | `test_a_malformed_proposal_is_refused_with_zero_validator_prompts` |
| a validator agrees with a leader that raised | `test_an_unusable_answer_is_an_error_and_never_a_verdict` |
| a validator trusts the leader | `test_nodes_that_read_a_pair_differently_do_not_agree` |
| a validator whose own model failed agrees | `test_a_validator_whose_model_fails_does_not_agree` |
| agreement compares the first pair only | `test_nodes_that_read_a_pair_differently_do_not_agree` |
| the structural check accepts any word | `test_a_malformed_proposal_is_refused_with_zero_validator_prompts` |
| the structural check accepts any length | `test_structure` |
| an altered pair does not reject | `test_a_changed_number_is_counted_and_never_reaches_a_model` |
| an unclear pair certifies | `test_an_unclear_pair_makes_the_filing_inconclusive` |
| unclear outranks altered | `test_the_verdict_table` |
| the counted pairs are not counted on the filing | `test_a_changed_number_is_counted_and_never_reaches_a_model` |
| the same translation can be checked again | `test_the_same_translation_cannot_be_checked_twice` |
| the replay guard ignores the target language | `test_the_key_covers_both_languages_and_both_texts` |
| the replay guard is defeated by capital letters | `test_the_same_translation_cannot_be_checked_twice` |
| a filing is not linked to the filer's previous one | `test_a_filer_walks_only_their_own_filings_newest_first_one_page_at_most` |
| the filer's newest filing is not recorded | `test_a_filer_walks_only_their_own_filings_newest_first_one_page_at_most` |
| the filing is not indexed by its key | `test_the_same_translation_cannot_be_checked_twice` |
| anyone may withdraw anyone's filing | `test_nobody_else_may_withdraw` |
| a filing can be withdrawn twice | `test_the_filer_may_withdraw_and_the_verdict_stays` |
| standing forgets a withdrawal | `test_the_filer_may_withdraw_and_the_verdict_stays` |
| a negative filing id reads the newest filing | `test_a_read_with_a_bad_id_is_a_user_error` |
| a listing walks past the page limit | `test_a_filer_walks_only_their_own_filings_newest_first_one_page_at_most` |
| mismatched segment counts are paired up anyway | `test_the_segment_bounds` |
| empty segments are dropped, silently realigning every pair after them | `test_the_segment_bounds` |
| more than eight segments are accepted | `test_the_segment_bounds` |
| a one-character segment is accepted | `test_the_segment_bounds` |
| an over-long segment is accepted | `test_the_segment_bounds` |
| a translation into the same language is accepted | `test_the_language_bounds` |
| the title is unbounded | `test_the_title_bounds` |
| a language name is unbounded | `test_the_language_bounds` |
| the fence is removed | `test_caller_text_is_stored_verbatim_and_fenced_only_at_the_prompt` |
| the fence leaves square brackets | `test_caller_text_is_stored_verbatim_and_fenced_only_at_the_prompt` |
| the fence deletes instead of replacing | `test_the_fence_replaces_and_preserves_length` |
| the translation rows reach the prompt unfenced | `test_caller_text_is_stored_verbatim_and_fenced_only_at_the_prompt` |
| the source rows reach the prompt unfenced | `test_every_value_interpolated_into_the_prompt_is_fenced_or_ours` |
| the title reaches the prompt unfenced | `test_every_value_interpolated_into_the_prompt_is_fenced_or_ours` |
| the language names reach the prompt unfenced | `test_every_value_interpolated_into_the_prompt_is_fenced_or_ours` |
| the prompt no longer states the count | `test_the_count_is_stated_and_the_example_is_never_a_valid_answer` |
| the answer example is a real answer | `test_the_count_is_stated_and_the_example_is_never_a_valid_answer` |
| a leader's reason is stored as sent | `test_the_reason_is_not_compared_and_is_stored_sanitised` |
| a leader's reason is stored uncapped | `test_the_reason_is_not_compared_and_is_stored_sanitised` |
<!-- measured:mutations:end -->

## Verified against the live deployment

<!-- measured:deployment:start -->
Deployed on studionet at [`0x5F4648f5a5E9428FEA8Dd8e6Ec9Eb7c1bd36ce58`](https://explorer-studio.genlayer.com/address/0x5F4648f5a5E9428FEA8Dd8e6Ec9Eb7c1bd36ce58) (deploy [`0x0dbc471e...`](https://explorer-studio.genlayer.com/tx/0x0dbc471ebed05e014dc634bb010a0e000417707a511a3d6a2926075693999e4d)). Every value below was read back from the chain by `scripts/seed.mjs` and written to [`deployments/studionet.json`](deployments/studionet.json); none of it is typed by hand.

| # | Translation | Readings, pair by pair | Verdict | Standing | Transaction |
|---|---|---|---|---|---|
| 0 | faithful | faithful (read) / faithful (read) / faithful (read) | **certified** | certified | [`0xa03bda3d...`](https://explorer-studio.genlayer.com/tx/0xa03bda3dbdfae6358ed378c529db8ab1909b5df9c3bdfb8f95ccd209a59f0d99) |
| 1 | one number changed (30 to 13) | altered (counted) / faithful (read) / faithful (read) | **rejected** | withdrawn | [`0xfa8a253b...`](https://explorer-studio.genlayer.com/tx/0xfa8a253b27547328c22e32b5f061a3b3194a3437a23991458387e43314305653) |
| 2 | one negation dropped | faithful (read) / faithful (read) / altered (read) | **rejected** | rejected | [`0xa96d1de3...`](https://explorer-studio.genlayer.com/tx/0xa96d1de32098b219af95d38d212903feaf71700ae14be75b462ec9037bae5da5) |

The reason each leader gave (leader-supplied, sanitised, not part of consensus):

- **0, certified:** All three translations accurately convey the source meaning.
- **1, rejected:** Both translations accurately convey the original meaning without additions or omissions.
- **2, rejected:** Pair 2 reverses negation: source prohibits assignment without consent; translation permits it.

What the contract refused, on chain, and the one write that followed:

| Step | Outcome | Transaction |
|---|---|---|
| a translation missing a segment | refused: the source has 3 segments and the translation 2; they are checked pair by pair | [`0x70b854cc...`](https://explorer-studio.genlayer.com/tx/0x70b854cc8e73d4a50eac671766b94c4e292fb511bd72acfba4642599bc137b58) |
| the same translation checked again | refused: this translation was already checked as filing 0; that verdict stands | [`0x67afe76f...`](https://explorer-studio.genlayer.com/tx/0x67afe76f15f9eb38208241b16e3ea13b52077175845b953dd787b2b10e89e360) |
| someone else withdraws filing 1 | refused: only the filer may withdraw a filing | [`0xea11bcd4...`](https://explorer-studio.genlayer.com/tx/0xea11bcd4595a6d0fa51507663e1b830aa36671ec6ec52b4638ed8cf75e3b48e1) |
| the filer withdraws the wrong number | ok | [`0x36f11a96...`](https://explorer-studio.genlayer.com/tx/0x36f11a96b098339988025672011980e8839320de57e6ce27210908d7af2e7705) |

`tests/test_runbook.py::TestTheRecord` replays these readings through this repository's contract, and checks that every counted pair is exactly one the number check picks.
<!-- measured:deployment:end -->

On top of the record: `pnpm e2e:contract` asks the chain again for every transaction and
every view and checks each against the record, and `pnpm verify:contract` reads the
deployed source back with `gen_getContractCode`, compares it byte for byte with
`packages/contracts/parity.py`, and runs genvm-lint on the deployed bytes.

## Known limits

- It judges meaning, not style. A clumsy but faithful sentence is faithful.
- Numbers written as words are read by validators, not counted.
- Cutting a text into pairs is the filer's job; a certificate is about the pairs as filed.
- At most 8 pairs of at most 400 characters per filing.
- StudioNet is a test network; its state can be reset.

## Path forward

- Units and currencies alongside numbers ("30 days" vs "30 weeks").
- A fee per filing on a funded network, refunded on `certified`.
- Whole documents as linked filings.
