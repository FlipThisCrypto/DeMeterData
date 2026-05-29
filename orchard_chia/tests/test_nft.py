# SPDX-License-Identifier: Apache-2.0
"""Tests for the pure functions in orchard_chia.nft.

Hermetic — no wallet, no network. Tests the metadata generator,
canonicalization, hashing, and mint-plan validation logic.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchard_chia.nft import generate, mint


# ---------------- generate ----------------

def test_collection_metadata_shape():
    c = generate.build_collection_metadata()
    assert c["id"] == generate.ORCHARD_GENESIS_COLLECTION_ID
    assert c["name"] == generate.ORCHARD_GENESIS_COLLECTION_NAME
    assert any(a["type"] == "description" for a in c["attributes"])


def test_pass_metadata_basic():
    p = generate.build_pass_metadata(pass_number=1)
    assert p["format"] == "CHIP-0007"
    assert p["name"] == "Orchard Pass #0001"
    assert p["series_number"] == 1
    assert p["series_total"] == generate.GENESIS_TOTAL
    assert p["sensitive_content"] is False
    # Collection reference matches the collection metadata.
    assert p["collection"]["id"] == generate.ORCHARD_GENESIS_COLLECTION_ID
    # Standard genesis attributes are present.
    traits = {a["trait_type"]: a["value"] for a in p["attributes"]}
    assert traits["Generation"] == "Genesis"
    assert traits["Pass Number"] == "0001"
    assert traits["Reward Token"] == "$JUICE"


def test_pass_metadata_pass_number_bounds():
    with pytest.raises(ValueError):
        generate.build_pass_metadata(pass_number=0)
    with pytest.raises(ValueError):
        generate.build_pass_metadata(pass_number=11)
    # Edge cases at the bounds work.
    generate.build_pass_metadata(pass_number=1)
    generate.build_pass_metadata(pass_number=10)


def test_pass_metadata_extra_attributes():
    p = generate.build_pass_metadata(
        pass_number=3,
        extra_attributes=[{"trait_type": "Animator", "value": "Richard"}],
    )
    traits = {a["trait_type"]: a["value"] for a in p["attributes"]}
    assert traits["Animator"] == "Richard"


def test_canonical_json_is_deterministic():
    p = generate.build_pass_metadata(pass_number=5)
    a = generate.canonical_json(p)
    b = generate.canonical_json(p)
    assert a == b
    # Re-encoding through the same canonicalizer must produce the same
    # bytes. Note: we don't ban ", " from the *output string* because
    # value contents can legitimately contain it (e.g. descriptions);
    # the JSON *structural* separators are what matter.
    parsed = json.loads(a)
    assert generate.canonical_json(parsed) == a
    # Keys are sorted (top-level).
    assert list(parsed.keys()) == sorted(parsed.keys())


def test_sha256_hex_matches_known_value():
    h = generate.sha256_hex(b"hello world")
    assert h == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_write_genesis_batch(tmp_path: Path):
    written = generate.write_genesis_batch(tmp_path, total=10)
    assert len(written) == 10
    # All 10 files exist with the expected zero-padded names.
    for n in range(1, 11):
        p = tmp_path / f"{n:04d}.json"
        assert p.exists()
        doc = json.loads(p.read_text(encoding="utf-8"))
        assert doc["series_number"] == n
        assert doc["series_total"] == 10
        assert doc["collection"]["id"] == generate.ORCHARD_GENESIS_COLLECTION_ID


# ---------------- mint plan validation ----------------

GOOD_PLAN_YAML = """
collection_id: "f9a0c0a0-0001-4000-8000-000000000001"
target_address: "xch1abcdef"
royalty_address: "xch1abcdef"
royalty_percentage: 0
edition_total: 2
fee_mojos: 0
passes:
  - edition_number: 1
    metadata_file: "metadata/0001.json"
    data_uris: ["ipfs://bafy.../001.mp4"]
    data_hash: "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
    meta_uris: ["ipfs://bafy.../0001.json"]
    meta_hash: "ffeeddccbbaa99887766554433221100ffeeddccbbaa99887766554433221100"
  - edition_number: 2
    metadata_file: "metadata/0002.json"
    data_uris: ["ipfs://bafy.../002.mp4"]
    data_hash: "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff"
    meta_uris: ["ipfs://bafy.../0002.json"]
    meta_hash: "ffeeddccbbaa99887766554433221100ffeeddccbbaa99887766554433221100"
"""


def test_load_plan(tmp_path: Path):
    p = tmp_path / "plan.yaml"
    p.write_text(GOOD_PLAN_YAML, encoding="utf-8")
    plan = mint.load_plan(p)
    assert plan.edition_total == 2
    assert len(plan.passes) == 2
    assert plan.passes[0].edition_number == 1


def test_validate_good_plan(tmp_path: Path):
    p = tmp_path / "plan.yaml"
    p.write_text(GOOD_PLAN_YAML, encoding="utf-8")
    plan = mint.load_plan(p)
    # Stub the metadata files so the file-exists check passes.
    (tmp_path / "metadata").mkdir()
    (tmp_path / "metadata" / "0001.json").write_text("{}", encoding="utf-8")
    (tmp_path / "metadata" / "0002.json").write_text("{}", encoding="utf-8")
    problems = mint.validate_plan(plan, plan_path=p)
    assert problems == []


def test_validate_catches_bad_address(tmp_path: Path):
    p = tmp_path / "plan.yaml"
    yaml_bad = GOOD_PLAN_YAML.replace('"xch1abcdef"', '"NOT_AN_XCH_ADDRESS"')
    p.write_text(yaml_bad, encoding="utf-8")
    plan = mint.load_plan(p)
    problems = mint.validate_plan(plan, plan_path=None)
    assert any("target_address" in pr for pr in problems)


def test_validate_catches_bad_hash_length(tmp_path: Path):
    p = tmp_path / "plan.yaml"
    yaml_bad = GOOD_PLAN_YAML.replace(
        "data_hash: \"00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff\"",
        "data_hash: \"deadbeef\"",
    )
    p.write_text(yaml_bad, encoding="utf-8")
    plan = mint.load_plan(p)
    problems = mint.validate_plan(plan, plan_path=None)
    assert any("data_hash" in pr for pr in problems)


def test_validate_catches_empty_uris(tmp_path: Path):
    p = tmp_path / "plan.yaml"
    yaml_bad = GOOD_PLAN_YAML.replace(
        'data_uris: ["ipfs://bafy.../001.mp4"]',
        'data_uris: []',
    )
    p.write_text(yaml_bad, encoding="utf-8")
    plan = mint.load_plan(p)
    problems = mint.validate_plan(plan, plan_path=None)
    assert any("data_uris is empty" in pr for pr in problems)


def test_validate_catches_duplicate_edition(tmp_path: Path):
    p = tmp_path / "plan.yaml"
    yaml_bad = GOOD_PLAN_YAML.replace("edition_number: 2", "edition_number: 1")
    p.write_text(yaml_bad, encoding="utf-8")
    plan = mint.load_plan(p)
    problems = mint.validate_plan(plan, plan_path=None)
    assert any("duplicate edition_number" in pr for pr in problems)
