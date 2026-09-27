# Evidence: Parity, second round on GenLayer StudioNet

Every row below was read back from the chain by `scripts/evidence.mjs`: the
sender, the status and the outcome come from the node's answer for each hash,
not from the deployment record. Every outcome on chain matches the record.

- **Contract:** [`0x5F4648f5a5E9428FEA8Dd8e6Ec9Eb7c1bd36ce58`](https://explorer-studio.genlayer.com/address/0x5F4648f5a5E9428FEA8Dd8e6Ec9Eb7c1bd36ce58)
- **Round:** new wallets on the contract already deployed; no deploy in this round
- **The deployment itself:** [EVIDENCE.md](EVIDENCE.md)
- **Transactions:** 5, from 2 different wallets
- **Generated:** 2026-09-26 16:12 UTC

## Wallets

Each wallet was made in memory for this run, and its key was never written
anywhere. Click an address to see every transaction it sent.

| Role | Address | Transactions sent |
|---|---|---|
| filer_a | [`0x1F0A830FAd38B2Ff15835a7AfE465409c457e088`](https://explorer-studio.genlayer.com/address/0x1F0A830FAd38B2Ff15835a7AfE465409c457e088) | 2 |
| filer_b | [`0xdB091B8F6ad722f43BfE79aac3C38fdb221466Ea`](https://explorer-studio.genlayer.com/address/0xdB091B8F6ad722f43BfE79aac3C38fdb221466Ea) | 3 |

## Transactions, in order

"refused" is a transaction the contract was meant to refuse: the committee
agreed on the refusal, and the sentence is the contract's own.

| # | Step | Sent by | Method | On chain | Outcome | Tx |
|---|---|---|---|---|---|---|
| 0 | filing 3: a faithful translation (expected certified) | filer_a [`0x1F0A…e088`](https://explorer-studio.genlayer.com/address/0x1F0A830FAd38B2Ff15835a7AfE465409c457e088) | `certify` | FINALIZED · MAJORITY_AGREE | executed | [`0x5056538f…1644`](https://explorer-studio.genlayer.com/tx/0x5056538fecdf91b49b6274b292d398d1dbc01a49cc183251393ee8450f781644) |
| 1 | filing 4: both numbers changed (expected rejected, no model) | filer_b [`0xdB09…66Ea`](https://explorer-studio.genlayer.com/address/0xdB091B8F6ad722f43BfE79aac3C38fdb221466Ea) | `certify` | FINALIZED · MAJORITY_AGREE | executed | [`0x118aa49b…34e4`](https://explorer-studio.genlayer.com/tx/0x118aa49b5669324543393d27d7f560163cc5aaf1b51aa6318223b0cd29b034e4) |
| 2 | filer B withdraws filing 3 | filer_b [`0xdB09…66Ea`](https://explorer-studio.genlayer.com/address/0xdB091B8F6ad722f43BfE79aac3C38fdb221466Ea) | `withdraw` | FINALIZED · MAJORITY_AGREE | refused: only the filer may withdraw a filing | [`0xbb89ff42…fc10`](https://explorer-studio.genlayer.com/tx/0xbb89ff4205225db7d9c3554346b6e79bb826cfa31e83110a62448d706d56fc10) |
| 3 | the same translation filed again | filer_a [`0x1F0A…e088`](https://explorer-studio.genlayer.com/address/0x1F0A830FAd38B2Ff15835a7AfE465409c457e088) | `certify` | ACCEPTED · MAJORITY_AGREE | refused: this translation was already checked as filing 3; that verdict stands | [`0x6f8e80a3…982f`](https://explorer-studio.genlayer.com/tx/0x6f8e80a365108030d438f3f4e6784db52545dfc57f3d3ab5e7dc58f9fa73982f) |
| 4 | filer B withdraws its own filing 4 | filer_b [`0xdB09…66Ea`](https://explorer-studio.genlayer.com/address/0xdB091B8F6ad722f43BfE79aac3C38fdb221466Ea) | `withdraw` | ACCEPTED · MAJORITY_AGREE | executed | [`0x4ed3e629…3b5e`](https://explorer-studio.genlayer.com/tx/0x4ed3e629e397e01d25467c8030973f7f6b526f38c3f988158499d29682a93b5e) |
