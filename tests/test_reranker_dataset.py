import json
from collections import Counter
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "datasets" / "reranker"
pytestmark = pytest.mark.skipif(not (DATA / "queries.jsonl").exists(),
                                reason="lancer datasets/build_reranker_dataset.py")


def _load(name):
    return [json.loads(line) for line in (DATA / name).read_text(encoding="utf-8").splitlines()]


def _doc(passage_id):
    return passage_id.split("#")[0]


def test_size_matches_specification():
    triplets = [t for s in ("train", "val", "test") for t in _load(f"triplets_{s}.jsonl")]
    assert 800 <= len(triplets) <= 1500


def test_negatives_are_never_relevant():
    queries = {q["query_id"]: q for q in _load("queries.jsonl")}
    for s in ("train", "val", "test"):
        for t in _load(f"triplets_{s}.jsonl"):
            assert t["negative_passage_id"] not in queries[t["query_id"]]["relevant_passage_ids"]


def test_splits_do_not_share_documents():
    docs = {s: {_doc(pid) for t in _load(f"triplets_{s}.jsonl")
                for pid in (t["positive_passage_id"], t["negative_passage_id"])}
            for s in ("train", "val", "test")}
    assert not docs["train"] & docs["val"]
    assert not docs["train"] & docs["test"]
    assert not docs["val"] & docs["test"]


def test_hard_negative_kinds_present():
    kinds = Counter(t["negative_kind"] for s in ("train", "val", "test") for t in _load(f"triplets_{s}.jsonl"))
    assert kinds["cross_family"] >= 200
    assert kinds["superseded"] >= 1


def test_superseded_flange_torque_is_a_negative():
    triplets = _load("triplets_train.jsonl") + _load("triplets_val.jsonl") + _load("triplets_test.jsonl")
    flange = [t for t in triplets if "bride de refoulement" in t["question"] and "60 N·m" in t["positive"]]
    assert flange and any("45 N·m" in t["negative"] for t in flange)
