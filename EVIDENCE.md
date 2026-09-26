# Evidence: Parity on GenLayer StudioNet

Every row below was read back from the chain by `scripts/evidence.mjs`: the
sender, the status and the outcome come from the node's answer for each hash,
not from the deployment record. Every outcome on chain matches the record.

- **Contract:** [`0x5F4648f5a5E9428FEA8Dd8e6Ec9Eb7c1bd36ce58`](https://explorer-studio.genlayer.com/address/0x5F4648f5a5E9428FEA8Dd8e6Ec9Eb7c1bd36ce58)
- **Deploy transaction:** [`0x0dbc471e…9e4d`](https://explorer-studio.genlayer.com/tx/0x0dbc471ebed05e014dc634bb010a0e000417707a511a3d6a2926075693999e4d)
- **Source sha256:** `08de14954169b5140fe11902f90ede66ff00e3da86a67dca6f7d31de17ce6d5e`
- **Transactions:** 8, from 3 different wallets
- **Generated:** 2026-09-26 12:27 UTC

## Wallets

Each wallet was made in memory for this run, and its key was never written
anywhere. Click an address to see every transaction it sent.

| Role | Address | Transactions sent |
|---|---|---|
| deployer | [`0x7A2855755c2a734406B87625434A0DEe24696aA5`](https://explorer-studio.genlayer.com/address/0x7A2855755c2a734406B87625434A0DEe24696aA5) | 1 |
| filer | [`0x194370B59F1475376016881A3E7F927957632e14`](https://explorer-studio.genlayer.com/address/0x194370B59F1475376016881A3E7F927957632e14) | 5 |
| other | [`0x2c529B5138034F233E00A1e9C24a6D44ca631444`](https://explorer-studio.genlayer.com/address/0x2c529B5138034F233E00A1e9C24a6D44ca631444) | 2 |

## Transactions, in order

"refused" is a transaction the contract was meant to refuse: the committee
agreed on the refusal, and the sentence is the contract's own.

| # | Step | Sent by | Method | On chain | Outcome | Tx |
|---|---|---|---|---|---|---|
| 0 | deploy | deployer [`0x7A28…6aA5`](https://explorer-studio.genlayer.com/address/0x7A2855755c2a734406B87625434A0DEe24696aA5) | `deploy` | FINALIZED · MAJORITY_AGREE | executed | [`0x0dbc471e…9e4d`](https://explorer-studio.genlayer.com/tx/0x0dbc471ebed05e014dc634bb010a0e000417707a511a3d6a2926075693999e4d) |
| 1 | filing 0: faithful (expected certified) | filer [`0x1943…2e14`](https://explorer-studio.genlayer.com/address/0x194370B59F1475376016881A3E7F927957632e14) | `certify` | FINALIZED · MAJORITY_AGREE | executed | [`0xa03bda3d…0d99`](https://explorer-studio.genlayer.com/tx/0xa03bda3dbdfae6358ed378c529db8ab1909b5df9c3bdfb8f95ccd209a59f0d99) |
| 2 | filing 1: wrong number (expected rejected) | filer [`0x1943…2e14`](https://explorer-studio.genlayer.com/address/0x194370B59F1475376016881A3E7F927957632e14) | `certify` | FINALIZED · MAJORITY_AGREE | executed | [`0xfa8a253b…5653`](https://explorer-studio.genlayer.com/tx/0xfa8a253b27547328c22e32b5f061a3b3194a3437a23991458387e43314305653) |
| 3 | filing 2: dropped not (expected rejected) | filer [`0x1943…2e14`](https://explorer-studio.genlayer.com/address/0x194370B59F1475376016881A3E7F927957632e14) | `certify` | FINALIZED · MAJORITY_AGREE | executed | [`0xa96d1de3…5da5`](https://explorer-studio.genlayer.com/tx/0xa96d1de32098b219af95d38d212903feaf71700ae14be75b462ec9037bae5da5) |
| 4 | a translation missing a segment | filer [`0x1943…2e14`](https://explorer-studio.genlayer.com/address/0x194370B59F1475376016881A3E7F927957632e14) | `certify` | FINALIZED · MAJORITY_AGREE | refused: the source has 3 segments and the translation 2; they are checked pair by pair | [`0x70b854cc…7b58`](https://explorer-studio.genlayer.com/tx/0x70b854cc8e73d4a50eac671766b94c4e292fb511bd72acfba4642599bc137b58) |
| 5 | the same translation checked again | other [`0x2c52…1444`](https://explorer-studio.genlayer.com/address/0x2c529B5138034F233E00A1e9C24a6D44ca631444) | `certify` | FINALIZED · MAJORITY_AGREE | refused: this translation was already checked as filing 0; that verdict stands | [`0x67afe76f…e360`](https://explorer-studio.genlayer.com/tx/0x67afe76f15f9eb38208241b16e3ea13b52077175845b953dd787b2b10e89e360) |
| 6 | someone else withdraws filing 1 | other [`0x2c52…1444`](https://explorer-studio.genlayer.com/address/0x2c529B5138034F233E00A1e9C24a6D44ca631444) | `withdraw` | FINALIZED · MAJORITY_AGREE | refused: only the filer may withdraw a filing | [`0xea11bcd4…48e1`](https://explorer-studio.genlayer.com/tx/0xea11bcd4595a6d0fa51507663e1b830aa36671ec6ec52b4638ed8cf75e3b48e1) |
| 7 | the filer withdraws the wrong number | filer [`0x1943…2e14`](https://explorer-studio.genlayer.com/address/0x194370B59F1475376016881A3E7F927957632e14) | `withdraw` | FINALIZED · MAJORITY_AGREE | executed | [`0x36f11a96…7705`](https://explorer-studio.genlayer.com/tx/0x36f11a96b098339988025672011980e8839320de57e6ce27210908d7af2e7705) |
