# Parity

**Translations certified pair by pair on GenLayer.** The name is the promise:
the translation says the same thing as the source, pair for pair, or it is not
certified.

Anyone files a source text and its translation, cut into the same number of
segments. The contract counts the numbers in every pair itself, in Latin,
Persian and Arabic-Indic digits, so "30 days" turning into "13 days" is caught
without asking anyone. GenLayer's validators read only the pairs whose numbers
agree, one token each, in two orders, and must agree on every one. The verdict
is arithmetic on those tokens, stored on-chain, where any contract can read it
in one call.

**Live on studionet at `0x5F4648f5a5E9428FEA8Dd8e6Ec9Eb7c1bd36ce58`.**
Intelligent contract + shared type layer + scripts that deploy, seed, verify
and prove it, not a standalone contract.

> Every transaction of the live demo, and the wallet that sent it, read back
> from the chain: **[EVIDENCE.md](EVIDENCE.md)**.

---

## Why this exists

A translation fails quietly. "Payment is due within 30 days" becomes "within
13 days"; "the supplier may not assign" becomes "the supplier may assign"; a
condition is dropped because it read awkwardly. Contracts, notices, medical
leaflets and court papers are translated every day by people the reader never
meets, and the reader has no way to check.

Asking a model "is this a good translation?" does not fix it. It gets a
confident yes about fluent text, and a fluent translation is exactly the one
whose errors nobody catches. And if one party runs the model, the other party
has no reason to accept its answer.

### In plain terms

You file the original text and its translation, cut into matching pieces:
sentence one with sentence one, sentence two with sentence two. For every
pair, the contract first compares the numbers itself. If a number changed,
that pair is marked altered on the spot, and no AI ever sees it. The pairs
whose numbers match go to GenLayer's validators, each of which reads them
twice, in two different orders, and says for each pair: faithful, altered or
unclear. They have to agree exactly. Then the contract does the sums:

- every pair faithful → **certified**
- any pair altered → **rejected**
- otherwise → **inconclusive**

The result is public and permanent, and another contract can refuse to act on
a translation that is not certified.

### Why this needs GenLayer specifically

Whether a sentence in Persian says what a sentence in English says is a
judgment about meaning in natural language. A normal smart contract cannot
make it. An LLM can, but a single model run by one party is not a verdict the
other party has to accept.

Here the reading is done by a validator quorum under consensus rules, and the
verdict lands on the same chain as the contracts that depend on it, with
nobody in between. Everything that does not need judgment is kept away from
the model: numbers are counted by code, the verdict is arithmetic, and a
reading that changes with the order the pairs were shown is recorded as
unclear rather than trusted. A model answer that cannot be parsed fails
closed: it is raised as `[LLM_ERROR]`, which no validator agrees with, so a
broken model can never certify anything.

### How you actually use it

1. **File a translation**: call `certify(title, source_lang, target_lang,
   source, translation)` with the segments joined by `|`, from GenLayer
   Studio, genlayer-js, or `packages/contracts/scripts/seed.mjs` as a worked
   example. You are recorded as the filer.
2. **Read the verdict**: `filing(id)` gives the verdict and how many pairs
   were altered, unclear or counted by code; `segments_of(id)` gives every pair
   with its reading and whether it was `counted` or `read`.
3. **Rely on it from another contract**: `standing(id)` returns one word:
   `certified`, `rejected`, `inconclusive` or `withdrawn`.

   ```python
   parity = gl.get_contract_at(Address(PARITY))
   if parity.view().standing(filing_id) != "certified":
       raise gl.vm.UserError("[EXPECTED] that translation is not certified")
   ```
4. **Withdraw**: the filer can withdraw a filing; its row and its verdict stay
   on record.

The same translation cannot be filed twice: the question has been answered.

## Stack

| Layer | Tech |
|---|---|
| Contract | GenLayer Intelligent Contract, Python (GenVM): [`packages/contracts/parity.py`](packages/contracts/parity.py) |
| Consensus | custom leader/validator with `gl.vm.run_nondet_unsafe`: a free structural check, then exact agreement on the whole token vector |
| Tests | pytest on a GenVM stand-in that runs the real file, plus a mutation pass that breaks every defence on purpose |
| Chain client | `genlayer-js` 1.1.8: deploy, seed, e2e, verify and evidence scripts |
| Types | [`packages/shared`](packages/shared): view types, parsers and a port of the number check, tested against vectors generated from the contract |

There is no backend and no database. Every value in this repository's record
was read back from the chain.

---

## Quick start

```bash
pnpm install
pip install -r packages/contracts/requirements-dev.txt

pnpm test               # contract (pytest) + shared (vitest), no chain needed
```

Deploy your own copy and put the whole demo on the explorer:

```bash
pnpm deploy:contract    # a fresh deployer wallet deploys packages/contracts/parity.py
pnpm seed:contract      # 3 filings, 3 refusals, 1 withdrawal, from two more wallets
pnpm e2e:contract       # re-reads every transaction and every view: PASS/FAIL
pnpm evidence:contract  # rewrites EVIDENCE.md from the chain
```

| Command | What it does |
|---|---|
| `pnpm test` | contract and shared suites |
| `pnpm test:contract` | pytest against `parity.py`, no chain needed |
| `pnpm test:shared` | vitest: the TypeScript port against the contract's vectors, and the parsers against the live record |
| `pnpm typecheck` | `tsc --noEmit` on the shared package |
| `pnpm mutate:contract` | removes every defence one at a time; every mutant must be caught by a named test |
| `pnpm measure:contract` | runs the suite and the mutation pass and renders the numbers into the contract README |
| `pnpm lint:genvm` | GenVM linter on the contract, pinned to the runner it depends on |
| `pnpm deploy:contract` | deploy to studionet (a throwaway deployer key) |
| `pnpm seed:contract` | the demo: every verdict and every refusal, recorded |
| `pnpm e2e:contract` | the record checked against the live chain |
| `pnpm verify:contract` | the deployed source, byte for byte against the file, and linted |
| `pnpm evidence:contract` | EVIDENCE.md: every transaction and its sender, from the chain |
| `pnpm demo:contract` | deploy, seed, e2e and evidence in one go |

### Configuration

Copy `.env.example` to `.env`. On studionet nothing is needed: every role gets
a wallet made in memory for the run, and no key is ever written to disk. On any
other network (`GENLAYER_NETWORK=testnet-asimov`) the scripts refuse to run
without `DEPLOYER_PRIVATE_KEY`, `FILER_PRIVATE_KEY` and `OTHER_PRIVATE_KEY`.

## The live demo

| # | Filing | Pairs | Verdict |
|---|---|---|---|
| 0 | a faithful Persian translation of a supply clause | faithful (read) · faithful (read) · faithful (read) | **certified** |
| 1 | the same with "30 days" changed to "13 days" | **altered (counted)** · faithful · faithful | **rejected**, then withdrawn by its filer |
| 2 | the same with "may not" changed to "may" | faithful · faithful · **altered (read)** | **rejected** |

Plus three refusals, each from the wallet it is about: a translation missing a
segment, the same translation filed again by someone else, and a stranger
trying to withdraw another filer's filing. Full detail, with every hash:
[EVIDENCE.md](EVIDENCE.md) and
[`packages/contracts/README.md`](packages/contracts/README.md#verified-against-the-live-deployment).

## Repo layout

```
.
├─ packages/
│  ├─ contracts/                 the Intelligent Contract and everything that proves it
│  │  ├─ parity.py               the contract
│  │  ├─ tests/                  pytest on a GenVM stand-in (see tests/README.md)
│  │  ├─ scripts/                deploy · seed · e2e · verify · evidence · lint · mutate · measure
│  │  ├─ demo/demo.json          the demo, read by the seed script AND the tests
│  │  ├─ deployments/            studionet.json, written by the scripts, never by hand
│  │  ├─ lib/                    the counting and agreement rules, generated from the contract
│  │  └─ DECISIONS.md            why every rule is the way it is
│  └─ shared/                    types, parsers, contract-shape.json, the number-check port
├─ EVIDENCE.md                   every live transaction and its sender
├─ .env.example
└─ package.json · pnpm-workspace.yaml
```

## License

MIT © 2026 Elina ([@Elinajafari](https://github.com/Elinajafari))
