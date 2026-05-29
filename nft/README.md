# nft/ — Orchard Pass collection content

This folder holds the **public-content** side of the Orchard Pass NFT collection: the CHIP-7 metadata JSON files and the collection-level metadata document. The **Python code** that generates these files and mints the NFTs lives at [`../orchard_chia/nft/`](../orchard_chia/nft/) — separation of concerns: content here, behavior there.

> **One Orchard Pass per Tree, one Tree per Pass.** Holding a Pass is the on-chain credential that lets a wallet register a Tree with the oracle and receive $JUICE for verified Season uptime. The genesis batch is **10 video NFTs** — short videos minted as the first 10 Passes.

## Files

```
nft/
├── README.md
├── collection.json          # CHIP-7 collection-level metadata
├── metadata/                # one CHIP-7 doc per Pass
│   ├── 0001.json
│   ├── 0002.json
│   ├── ...
│   └── 0010.json
├── mint_plan.example.yaml   # template — copy to mint_plan.yaml, fill in
└── mint_plan.yaml           # YOUR mint plan (gitignored if you want)
```

`collection.json` and the `metadata/NNNN.json` files are produced by:

```powershell
python -m orchard_chia.nft generate
```

…and committed so anyone can see exactly what we'll mint. **Re-running `generate` re-creates them — don't hand-edit unless you're ready for it to be overwritten.** If you want per-Pass customization (e.g., a unique name or extra trait per Pass), modify `orchard_chia/nft/generate.py`'s `build_pass_metadata()` call sites and re-run.

## CHIP-7 metadata standard

Each Pass JSON conforms to [CHIP-0007](https://github.com/Chia-Network/chips/blob/main/CHIPs/chip-0007.md), the de-facto NFT metadata standard on Chia. Genesis attributes that ship with every Pass:

| Trait | Value |
|-------|-------|
| Pass Number   | 0001 .. 0010 |
| Generation    | Genesis |
| Tier          | Founder |
| Reward Token  | $JUICE |
| Node Type     | ESP32-class Tree |
| Network       | Chia Mainnet |

The collection id is **`f9a0c0a0-0001-4000-8000-000000000001`** — locked in `orchard_chia/nft/generate.py`. Every Pass references that id, and the on-chain ownership-verification code (and future operator-side wallet checks) compare against it.

## Full mint workflow

### 1. Produce the videos

Each Pass is backed by one short video file (mp4 recommended). Make 10 of them — one per Pass. Files don't go in this folder; they live wherever you keep your media.

### 2. Upload media + metadata to IPFS

Recommended host: [nft.storage](https://nft.storage/) (free, Filecoin-backed, Chia-friendly). Pinata and web3.storage also work. Or any HTTPS server.

For each video file, you need:
- A persistent URI (ideally `ipfs://...` and an `https://...` gateway URL too — give the NFT redundancy)
- The SHA-256 of the file bytes (in hex). Compute with `python -m orchard_chia.nft` … *(see "Hashes" below)*

For each metadata JSON file (`metadata/NNNN.json`), same:
- A persistent URI
- The SHA-256

You'll end up with 20 URIs + 20 hashes total (10 videos + 10 JSONs).

### 3. Build the mint plan

Copy the template and fill it in:

```powershell
copy nft\mint_plan.example.yaml nft\mint_plan.yaml
notepad nft\mint_plan.yaml
```

For each Pass, set:
- `data_uris`: where the video lives (one or many)
- `data_hash`: SHA-256 of the video
- `meta_uris`: where the metadata JSON lives
- `meta_hash`: SHA-256 of the metadata JSON
- `metadata_file`: relative path to the local metadata file (for validation)

Set the top-level `target_address` and `royalty_address` to a wallet address you control. **The genesis batch mints to your own wallet** — you'll transfer Passes to operators separately via standard NFT transfers as they sign up. Cleaner than collecting 10 addresses upfront.

### 4. Validate the plan

```powershell
python -m orchard_chia.nft validate --plan nft/mint_plan.yaml
```

Catches: bad address shapes, wrong-length hashes, missing URIs, duplicate edition numbers, missing metadata files.

### 5. Mint

```powershell
python -m orchard_chia.nft mint --plan nft/mint_plan.yaml
```

Calls `nft_mint_nft` on the Chia reference wallet for each Pass. Per-mint result is written to `nft/mint_results.json`. Each mint costs ~0.0001 XCH in network fees (10 mints = ~0.001 XCH total).

### 6. Verify

After the mints settle (a few minutes), list the Passes your wallet now holds:

```powershell
python -m orchard_chia.nft verify --wallet-id <NFT_WALLET_ID>
```

(NFT wallet id is shown by `chia wallet show`.) Should list 10 Passes, one per edition.

## Hashes — how to compute them

For now, compute manually:

```powershell
python -c "import hashlib; print(hashlib.sha256(open(r'C:\path\to\video.mp4','rb').read()).hexdigest())"
```

Or batch all videos in a folder:

```powershell
Get-ChildItem *.mp4 | ForEach-Object { "$($_.Name)  $(python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" $_.FullName)" }
```

A future v1.1 helper will automate this — for now, manual is fine for 10 files.

## Status

| Phase | Component | Status |
|-------|-----------|--------|
| 6 | CHIP-7 generator + 10 metadata stubs | ✅ Generated |
| 6 | Mint plan template                 | ✅ At `mint_plan.example.yaml` |
| 6 | Mint pipeline (`nft_mint_nft` RPC) | ✅ Code + tests, awaiting video URIs |
| 6 | Verify helper (wallet ownership)   | ✅ Code + tests |
| 6.5 | Oracle `/register` gate           | ⬜ Deferred to Phase 7 |
