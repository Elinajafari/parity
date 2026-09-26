# Contract tests

Parity is tested at four levels, from the cheapest to the one that costs real
transactions. Each level has one command.

| Level | Command | Needs | What it proves |
|---|---|---|---|
| 1. Offline suite | `pnpm test:contract` | Python + pytest | the contract file itself behaves as specified, including against a lying leader |
| 2. Mutation pass | `pnpm mutate:contract` | same | every defence is covered by a test that fails without it |
| 3. Live demo | `pnpm deploy:contract && pnpm seed:contract` | Node 20+ | the same behaviour happens on StudioNet, with real validators and real models |
| 4. Chain checks | `pnpm e2e:contract`, `pnpm verify:contract`, `pnpm evidence:contract` | Node 20+ | what the record claims is what the chain holds, and what is deployed is this file |

## 1. The offline suite

```bash
pip install -r requirements-dev.txt
pnpm test:contract   # from the repo root, or here: python -m pytest tests -q
```

It runs the real `packages/contracts/parity.py` on [`tests/glsim.py`](glsim.py), a
small GenVM stand-in. The stand-in gives the leader and each validator their own
mock model answers, can make a leader lie, and refuses what GenVM refuses, such
as a storage field of a type GenVM cannot store.

| File | What it covers |
|---|---|
| [`test_logic.py`](test_logic.py) | the pure rules: digits in every script, separators, leading zeros, sorting, the number check, the fold of the two orders, the agreement rule, the verdict table, the replay key, the fence, and that `lib/parity_consensus.py` is exactly the contract's code |
| [`test_e2e.py`](test_e2e.py) | the contract executed end to end: a changed number is counted and never reaches a model; a dropped negation is read as altered; a pair the two orders read differently is `unclear`; a validator refuses a lying or malformed leader (a malformed one costs it zero prompts); an `[LLM_ERROR]` is never agreed with; the registry, the replay guard, withdrawals, bounds; and static checks over the parsed source (every prompt value fenced, runner pinned, class named after the product, pure ASCII, no forbidden storage type) |
| [`test_runbook.py`](test_runbook.py) | the live demo replayed offline from [`demo/demo.json`](../demo/demo.json) before any transaction is spent; and once `deployments/studionet.json` exists, the validators' real readings are replayed through this file, which must store exactly what the deployed contract stored |
| [`test_vectors.py`](test_vectors.py) | `packages/shared/number-vectors.json` is exactly what this contract's number check, verdict table, text cleaning and replay key compute, so the TypeScript port in `packages/shared` is tested against the contract's own answers (`UPDATE_VECTORS=1` regenerates it) |
| [`test_shape.py`](test_shape.py) | `packages/shared/contract-shape.json` describes every public write and view, its parameters and types, and the fields the live deployment returned, exactly; any drift on either side fails |

The last group, `TestTheRecord`, is skipped until a deployment has been
recorded, and then runs every time.

## 2. The mutation pass

```bash
pnpm mutate:contract
```

[`scripts/mutate.py`](../scripts/mutate.py) makes 62 small edits to a copy of the
contract, each one removing a defence ("Persian digits are not read as digits",
"a validator trusts the leader", "anyone may withdraw anyone's filing", ...),
runs the suite against each, and names the test that failed. A mutant that
survives is a missing test, and the script exits non-zero. It refuses to run on
a red baseline, and a mutation whose target text is missing or ambiguous is a
failure, never a skip. The table in the README is its output.

## 3. The live demo

```bash
pnpm install
pnpm deploy:contract          # a fresh deployer wallet deploys packages/contracts/parity.py
pnpm seed:contract            # a fresh filer and a fresh stranger run the demo
```

Three wallets, one role each, all made in memory for the run:

| Wallet | Does |
|---|---|
| deployer | deploys the contract, nothing else |
| filer | files the three translations, tries one malformed filing, withdraws one |
| other | a stranger: asks a question already answered, and tries to withdraw someone else's filing |

Every transaction, in order, and what it proves. The expected outcome is part
of the script: if the chain does anything else, the run stops, because the
record claims whatever it holds.

| # | Sent by | Call | Expected | What it proves |
|---|---|---|---|---|
| 0 | deployer | deploy | deployed | the file deploys as it is; its sha256 is recorded |
| 1 | filer | `certify` faithful translation | **certified** | all three pairs are read `faithful` by validators, in both orders |
| 2 | filer | `certify` with 30 → ۱۳ | **rejected** | pair 0 is `altered (counted)`: the numbers were compared by code, across scripts, and no model saw that pair |
| 3 | filer | `certify` with "may not" → "may" | **rejected** | pair 2 is `altered (read)`: validators caught a dropped negation that carries no number |
| 4 | filer | `certify` with a missing segment | refused | 3 source segments against 2 are never paired up and silently shifted |
| 5 | other | `certify` the faithful translation again | refused | the same question is asked once, whoever asks it |
| 6 | other | `withdraw(1)` | refused | only the filer may withdraw |
| 7 | filer | `withdraw(1)` | executed | the filing is withdrawn; its row and its verdict stay |

The seed script then reads every filing, segment and standing back from the
chain into [`deployments/studionet.json`](../deployments/studionet.json).

## 4. Checking the chain, not the record

```bash
pnpm e2e:contract             # PASS/FAIL per check
pnpm verify:contract          # the deployed source, byte for byte, and genvm-lint on it
pnpm evidence:contract        # EVIDENCE.md
```

- **`e2e`** fetches every recorded transaction again and checks that the chain
  still says what the record says (executed, or refused with the same
  sentence), then re-reads every filing, every segment and every standing.
- **`verify`** reads the deployed source back with `gen_getContractCode`,
  compares it byte for byte with `packages/contracts/parity.py`, and runs genvm-lint on
  the bytes that came off the chain (pinned to GenVM `v0.3.0-rc7`).
- **`evidence`** builds [EVIDENCE.md](../../../EVIDENCE.md) from the chain's answers
  alone: for each hash the sender, the status and the outcome, plus a table of
  the wallets and how many transactions each sent. A row whose on-chain
  outcome disagrees with the record is marked.

A refusal still reaches ACCEPTED or FINALIZED: the committee agreed that the
contract refused. That is why every script reads the leader's result (`return`
or `rollback`) and never treats the status alone as success.

## Measuring

```bash
pnpm measure:contract
```

Runs the suite and the mutation pass now and renders their numbers, and the
live record, into the README. It writes nothing if the suite is red, a mutant
escapes, or the record is of a different contract file.
