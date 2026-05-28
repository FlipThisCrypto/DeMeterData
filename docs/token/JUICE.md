# $JUICE — Token Reference (Public)

> Public-safe information about the $JUICE CAT. The original creation log (`docs/Juice Token.docx`) contains operator-private wallet info and is **excluded from the repo by `.gitignore`** — never commit it.

![$JUICE logo](../photos/logo.png)

## Identity

| Field          | Value                                                                |
|----------------|----------------------------------------------------------------------|
| Name           | $JUICE                                                               |
| Type           | CAT (Chia Asset Token)                                               |
| Blockchain     | Chia mainnet                                                         |
| Asset ID       | `285164e6af80202d2b07fa3cc6ae47ff2906029365a83c50fcab25a56b937121`   |
| Eve Coin ID    | `2ff338ed6fb3161d48eed7f112d3c6077e90c517dc4534bfba8ad3975b7f5e63`   |
| Issuance       | Single issuance                                                      |
| Total Supply   | 100,000,000 JUICE                                                    |
| Project        | The Orchard                                                          |

## Verifying the token

Anyone can verify the $JUICE token on-chain by querying for the Asset ID or Eve Coin ID through:

- The Chia reference wallet (`chia wallet show` after adding the CAT)
- A Chia block explorer (e.g., [SpaceScan](https://www.spacescan.io/), [Mintgarden](https://mintgarden.io/))
- A full node RPC call against the Asset ID

## Description

JUICE is the native reward token of **The Orchard** — an open-source DePIN ecosystem on the Chia blockchain focused on decentralized sensor networks, real-world telemetry, environmental data, and community-built infrastructure.

The token is hardware-first and infrastructure-first: it pays operators for running real-world sensing Trees, not for speculative behavior. See [`../VISION.md`](../VISION.md) for the design philosophy.

## How $JUICE is distributed

See [reward economics in the README](../../README.md#reward-model-v1-tunable) and the manual-payout flow in [`../../chia/README.md`](../../chia/README.md). v1 distribution is a manual Season harvest from the issuer wallet; future versions may move to on-chain claim flows (out of scope for v1).

## What's *not* in this file

The operator's wallet fingerprint, wallet id, and wallet label are intentionally **not** documented here. They live in:

- The local `chia/config.yaml` (gitignored)
- The local `docs/Juice Token.docx` (gitignored)
- Memory at `~/.claude/.../memory/project_token_juice_private.md` (local only, not in this repo)

Operators forking this project will create their **own** CAT and substitute their own asset id. This file is the template.
