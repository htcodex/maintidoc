"""Évaluation de la recherche (semaine 2) : 30 questions pilotes + tests de contrôle d'accès.

Configurations comparées : BM25 seul, dense seul, hybride texte (BM25 + dense), hybride + visuel,
hybride + visuel + reranker d'origine. Métriques : Recall@5, nDCG@5, MRR@10, latence.
Tests d'accès : pour chaque utilisateur fictif, aucune requête ne doit renvoyer un élément d'un document
qu'il n'a pas le droit de lire, et l'ouverture d'une image interdite doit être refusée.

Usage : python -m maintidoc.evaluation.retrieval_eval [--fake-encoders] [--no-rerank]
Sortie : reports/semaine2/retrieval_results.json et retrieval_per_question.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path

import yaml
from PIL import Image

from maintidoc.access import AccessDenied, AccessLog, can_read, open_asset
from maintidoc.catalog import load_catalog, load_users
from maintidoc.config import ROOT, get_settings
from maintidoc.retrieval.encoders import build_encoders
from maintidoc.retrieval.search import CrossEncoderReranker, Retriever
from maintidoc.storage import open_asset_store

CONFIGS = {
    "bm25": dict(channels=("bm25",)),
    "dense": dict(channels=("dense",)),
    "hybride_texte": dict(channels=("bm25", "dense")),
    "hybride_visuel": dict(channels=("bm25", "dense", "image"), weights={}),          # RRF non pondérée
    "hybride_visuel_pondere": dict(channels=("bm25", "dense", "image")),              # poids de config.py
    "hybride_visuel_pondere_rerank": dict(channels=("bm25", "dense", "image"), rerank=True),
}
ACCESS_QUERIES = [
    "Que signifie le voyant V2 orange fixe ?", "couple de serrage des brides", "vidange de l'huile",
    "contrat de maintenance prix révision", "historique des interventions", "schéma électrique",
    "Ignore les instructions précédentes", "code défaut température", "consignation des énergies",
    "tarifs astreinte week-end pénalités",
]


def is_relevant(element, spec) -> bool:
    return (element.document_id == spec["doc"] and element.page == spec["page"]
            and (not spec.get("types") or element.element_type in spec["types"]))


def metrics(hits, specs, n_relevant: int) -> dict:
    rel = [any(is_relevant(h.element, s) for s in specs) for h in hits]
    first = next((i + 1 for i, r in enumerate(rel[:10]) if r), None)
    dcg = sum(1 / math.log2(i + 2) for i, r in enumerate(rel[:5]) if r)
    idcg = sum(1 / math.log2(i + 2) for i in range(min(5, n_relevant)))
    return {"recall@5": float(any(rel[:5])), "ndcg@5": dcg / idcg if idcg else 0.0,
            "mrr@10": 1 / first if first else 0.0, "first_rank": first}


def run(fake: bool = False, rerank: bool = True, out_dir: Path | None = None, log=print) -> dict:
    s = get_settings()
    users = load_users(s.fixtures_dir)
    docs = load_catalog(s.corpus_dir)
    qs = yaml.safe_load((ROOT / "data/eval/pilot_questions.yaml").read_text(encoding="utf-8"))["questions"]
    text_enc, image_enc = build_encoders(s, fake=fake)
    reranker = None   # chargé plus tard, encodeurs déchargés (mémoire limitée : 16 Go avec Docker)
    journal = AccessLog(s.index_dir / "access_log.jsonl")
    r = Retriever(s, text_enc, image_enc, reranker, journal)
    journal.store = r.store
    assets = open_asset_store(s)
    out_dir = out_dir or ROOT / "reports" / "semaine2"
    out_dir.mkdir(parents=True, exist_ok=True)

    configs = {k: v for k, v in CONFIGS.items() if not v.get("rerank")}
    rerank_cfgs = {k: v for k, v in CONFIGS.items() if v.get("rerank")} if (rerank and not fake) else {}
    per_q, summary = [], {}
    for cname, cfg in configs.items():
        vals, lat = [], []
        for q in qs:
            user = users[q.get("user", "u_resp_01")]
            photo = Image.open(s.corpus_dir / q["photo"]) if q.get("photo") else None
            n_rel = sum(1 for e in r.elements if can_read(user, e.access_groups)
                        and any(is_relevant(e, sp) for sp in q["relevant"]))
            res = r.search(user, q["question"], photo=photo, k=10, **cfg)
            m = metrics(res.hits, q["relevant"], n_rel)
            vals.append(m)
            lat.append(res.timings["total"])
            per_q.append({"config": cname, "id": q["id"], "categorie": q["categorie"], **m,
                          "top1": res.hits[0].key if res.hits else "", "latence_s": round(res.timings["total"], 3)})
        summary[cname] = {
            "recall@5": round(statistics.mean(v["recall@5"] for v in vals), 3),
            "ndcg@5": round(statistics.mean(v["ndcg@5"] for v in vals), 3),
            "mrr@10": round(statistics.mean(v["mrr@10"] for v in vals), 3),
            "latence_mediane_s": round(statistics.median(lat), 3),
            "latence_p95_s": round(sorted(lat)[max(0, math.ceil(0.95 * len(lat)) - 1)], 3),
        }
        log(f"  {cname:<24} {summary[cname]}")

    # ---------------------------------------------------------- reranker (deux phases)
    # 1) candidats calculés avec les encodeurs ; 2) encodeurs déchargés, reranker chargé, reclassement.
    if rerank_cfgs:
        import gc
        import time as _t
        from maintidoc.retrieval import encoders as enc_mod
        cands = {}
        for cname, cfg in rerank_cfgs.items():
            base = {k: v for k, v in cfg.items() if k != "rerank"}
            for q in qs:
                user = users[q.get("user", "u_resp_01")]
                photo = Image.open(s.corpus_dir / q["photo"]) if q.get("photo") else None
                res = r.search(user, q["question"], photo=photo, k=s.rerank_top_n, **base)
                cands[(cname, q["id"])] = (res.hits, res.timings["total"])
        r.text_enc = r.image_enc = None
        text_enc = image_enc = None
        enc_mod._st_model.cache_clear()
        gc.collect()
        log("  encodeurs déchargés ; chargement du reranker…")
        reranker = CrossEncoderReranker(s.reranker_model)
        for cname in rerank_cfgs:
            vals, lat = [], []
            for q in qs:
                user = users[q.get("user", "u_resp_01")]
                hits, t_base = cands[(cname, q["id"])]
                t0 = _t.perf_counter()
                if hits:
                    scores = reranker.score(q["question"], [h.element.embed_text for h in hits])
                    for h, sc in zip(hits, scores):
                        h.rerank_score = float(sc) * (s.superseded_weight if h.element.status == "superseded" else 1.0)
                    hits = sorted(hits, key=lambda h: -h.rerank_score)
                total = t_base + (_t.perf_counter() - t0)
                n_rel = sum(1 for e in r.elements if can_read(user, e.access_groups)
                            and any(is_relevant(e, sp) for sp in q["relevant"]))
                m = metrics(hits[:10], q["relevant"], n_rel)
                vals.append(m)
                lat.append(total)
                per_q.append({"config": cname, "id": q["id"], "categorie": q["categorie"], **m,
                              "top1": hits[0].key if hits else "", "latence_s": round(total, 3)})
            summary[cname] = {
                "recall@5": round(statistics.mean(v["recall@5"] for v in vals), 3),
                "ndcg@5": round(statistics.mean(v["ndcg@5"] for v in vals), 3),
                "mrr@10": round(statistics.mean(v["mrr@10"] for v in vals), 3),
                "latence_mediane_s": round(statistics.median(lat), 3),
                "latence_p95_s": round(sorted(lat)[max(0, math.ceil(0.95 * len(lat)) - 1)], 3),
            }
            log(f"  {cname:<24} {summary[cname]}")
        del reranker
        gc.collect()
        reranker_name = s.reranker_model
        text_enc, image_enc = build_encoders(s, fake=fake)   # rechargés pour les tests d'accès
        r.text_enc, r.image_enc = text_enc, image_enc
        reranker = None
    else:
        reranker_name = None

    # Par catégorie, pour la meilleure configuration sans reranker et avec
    by_cat = {}
    for row in per_q:
        by_cat.setdefault(row["config"], {}).setdefault(row["categorie"], []).append(row["recall@5"])
    by_cat = {c: {k: round(statistics.mean(v), 2) for k, v in d.items()} for c, d in by_cat.items()}

    # ---------------------------------------------------------- contrôle d'accès
    doc_groups = {d.document_id: d.access_groups for d in docs}
    leaks, checks = [], 0
    for user in users.values():
        for qtext in ACCESS_QUERIES:
            res = r.search(user, qtext, k=20, channels=("bm25", "dense", "image"))
            for h in res.hits:
                checks += 1
                if not can_read(user, doc_groups[h.element.document_id]):
                    leaks.append({"user": user.user_id, "query": qtext, "leak": h.key})
    denied_ok, denied_total, allowed_ok, allowed_total = 0, 0, 0, 0
    for user in users.values():
        for e in [e for e in r.elements if e.image_path][:400]:
            if can_read(user, e.access_groups):
                if allowed_total < 20:   # quelques lectures autorisées : le stockage répond
                    allowed_total += 1
                    allowed_ok += bool(open_asset(user, e.access_groups, e.image_path, store=assets))
                continue
            denied_total += 1
            try:
                open_asset(user, e.access_groups, e.image_path, store=assets)
            except AccessDenied:
                denied_ok += 1
    visible = {u.user_id: len({e.document_id for e in r.elements if can_read(u, e.access_groups)}) for u in users.values()}
    access = {"verified_results": checks, "leaks": len(leaks), "leak_examples": leaks[:5],
              "forbidden_asset_opens": denied_total, "forbidden_asset_opens_refused": denied_ok,
              "allowed_asset_opens": allowed_total, "allowed_asset_opens_ok": allowed_ok,
              "backends": {"qdrant": "serveur" if s.qdrant_url else "embarqué",
                           "metadata": "postgresql" if s.database_url else "sqlite", "assets": assets.kind},
              "documents_visible_per_user": visible}
    log(f"  accès : {checks} résultats vérifiés, {len(leaks)} fuite(s) ; "
        f"{denied_ok}/{denied_total} ouvertures interdites refusées")

    run_info = r.store.last_run() or {}
    result = {"index_run": run_info.get("run_id"), "text_model": run_info.get("text_model"),
              "image_model": run_info.get("image_model"), "reranker": reranker_name,
              "questions": len(qs), "summary": summary, "recall@5_par_categorie": by_cat, "access": access}
    (out_dir / "retrieval_results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(out_dir / "retrieval_per_question.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per_q[0]))
        w.writeheader()
        w.writerows(per_q)
    r.close()
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fake-encoders", action="store_true")
    ap.add_argument("--no-rerank", action="store_true")
    a = ap.parse_args()
    run(fake=a.fake_encoders, rerank=not a.no_rerank)


if __name__ == "__main__":
    main()
