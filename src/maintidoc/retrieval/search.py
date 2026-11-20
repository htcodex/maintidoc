"""Recherche hybride filtrée par droits d'accès.

Canaux (tous restreints aux éléments que l'utilisateur peut lire, AVANT récupération) :
  - lexical : BM25 sur le texte des éléments autorisés ;
  - dense   : BGE-M3 dans Qdrant, filtre `access_groups` dans la requête ;
  - visuel  : requête texte -> CLIP multilingue, et photo -> CLIP image, filtre identique.
Fusion : Reciprocal Rank Fusion (k = 60), documents remplacés pénalisés mais conservés et signalés.
Reranking optionnel : cross-encoder (bge-reranker-v2-m3) sur les meilleurs candidats.
Contrôle final : chaque résultat est re-vérifié contre les groupes de l'utilisateur (défense en profondeur).
"""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass, field

from rank_bm25 import BM25Okapi

from maintidoc.access import AccessLog, can_read
from maintidoc.catalog import User
from maintidoc.ingestion.elements import Element
from maintidoc.retrieval import index as idx
from maintidoc.storage import open_metadata_store

CHANNELS = ("bm25", "dense", "image")
_TOKEN = re.compile(r"[a-z0-9]+(?:[-.,][a-z0-9]+)*")
STOPWORDS = set("""a au aux avec ce ces dans de des du en est et il la le les leur l d un une ou par pas pour
qu que qui sa se ses sur ne y son sont à quel quelle quels quelles comment faut faire doit on""".split())


def tokenize(text: str) -> list[str]:
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c)).replace("'", " ").replace("’", " ")
    return [w for w in _TOKEN.findall(t) if w not in STOPWORDS]


@dataclass
class Hit:
    element: Element
    score: float
    ranks: dict = field(default_factory=dict)       # rang par canal (1 = meilleur)
    rerank_score: float | None = None

    @property
    def key(self):
        return self.element.key

    def citation(self) -> dict:
        e = self.element
        return {"document_id": e.document_id, "version": e.version, "page": e.page, "element_id": e.element_id,
                "element_type": e.element_type, "status": e.status, "superseded_by": e.superseded_by}


@dataclass
class SearchResult:
    hits: list[Hit]
    timings: dict
    channels: tuple


class Retriever:
    def __init__(self, settings, text_encoder, image_encoder, reranker=None, journal: AccessLog | None = None):
        self.s = settings
        self.text_enc, self.image_enc, self.reranker = text_encoder, image_encoder, reranker
        self.client = idx.open_client(settings)
        self.store = open_metadata_store(settings)
        self.elements = self.store.all_elements()
        self.by_key = {e.key: e for e in self.elements}
        self.tokens = {e.key: tokenize(e.embed_text) for e in self.elements}
        self.journal = journal

    def close(self):
        self.client.close()

    # -------------------------------------------------------------- canaux

    def _bm25(self, query: str, allowed: list[Element], k: int) -> list[str]:
        if not allowed:
            return []
        bm = BM25Okapi([self.tokens[e.key] for e in allowed])
        scores = bm.get_scores(tokenize(query))
        order = sorted(range(len(allowed)), key=lambda i: -scores[i])
        return [allowed[i].key for i in order[:k] if scores[i] > 0]

    def _qdrant(self, collection: str, vector, groups, k: int) -> list[str]:
        res = self.client.query_points(collection, query=vector.tolist(), query_filter=idx.access_filter(groups),
                                       limit=k, with_payload=["key", "access_groups"]).points
        return [p.payload["key"] for p in res]

    # -------------------------------------------------------------- recherche

    def search(self, user: User, query: str, photo=None, k: int = 10,
               channels: tuple = CHANNELS, rerank: bool = False, weights: dict | None = None) -> SearchResult:
        t = {}
        t0 = time.perf_counter()
        groups = list(user.groups)
        allowed = [e for e in self.elements if can_read(user, e.access_groups)]     # filtre AVANT récupération
        n = self.s.candidates_per_channel
        ranked: dict[str, list[str]] = {}
        if "bm25" in channels:
            ranked["bm25"] = self._bm25(query, allowed, n)
        t["bm25"] = time.perf_counter() - t0
        if "dense" in channels:
            t1 = time.perf_counter()
            ranked["dense"] = self._qdrant(idx.TEXT_COLLECTION, self.text_enc.encode([query], is_query=True)[0], groups, n)
            t["dense"] = time.perf_counter() - t1
        if "image" in channels:
            t1 = time.perf_counter()
            ranked["image"] = self._qdrant(idx.IMAGE_COLLECTION, self.image_enc.encode_queries([query])[0], groups, n)
            if photo is not None:
                ranked["photo"] = self._qdrant(idx.IMAGE_COLLECTION, self.image_enc.encode_query_images([photo])[0],
                                               groups, n)
            t["image"] = time.perf_counter() - t1

        # Fusion RRF pondérée : score = Σ poids_canal / (k + rang)
        w = self.s.channel_weights if weights is None else weights
        fused: dict[str, Hit] = {}
        for ch, keys in ranked.items():
            for r, key in enumerate(keys, 1):
                h = fused.setdefault(key, Hit(self.by_key[key], 0.0))
                h.ranks[ch] = r
                h.score += w.get(ch, 1.0) / (self.s.rrf_k + r)
        for h in fused.values():
            if h.element.status == "superseded":
                h.score *= self.s.superseded_weight
        hits = sorted(fused.values(), key=lambda h: -h.score)

        if rerank and self.reranker is not None and hits:
            t1 = time.perf_counter()
            top = hits[: self.s.rerank_top_n]
            scores = self.reranker.score(query, [h.element.embed_text for h in top])
            for h, sc in zip(top, scores):
                h.rerank_score = float(sc) * (self.s.superseded_weight if h.element.status == "superseded" else 1.0)
            hits = sorted(top, key=lambda h: -h.rerank_score) + hits[self.s.rerank_top_n:]
            t["rerank"] = time.perf_counter() - t1

        # Défense en profondeur : aucun résultat non autorisé ne sort, même si un canal était mal filtré.
        safe = [h for h in hits if can_read(user, h.element.access_groups)]
        if self.journal and len(safe) != len(hits):
            self.journal.record(user.user_id, "search_filtered_late", query[:0], False)
        t["total"] = time.perf_counter() - t0
        if self.journal:
            self.journal.record(user.user_id, "search", f"{len(safe[:k])} résultats", True)
        return SearchResult(safe[:k], t, tuple(ranked))


class CrossEncoderReranker:
    def __init__(self, model_name: str, max_length: int = 512):
        from sentence_transformers import CrossEncoder
        self.name = model_name
        self.model = CrossEncoder(model_name, device="cpu", max_length=max_length)

    def score(self, query: str, passages: list[str]):
        import torch
        with torch.inference_mode():   # lots de 2 : mémoire limitée sur le poste (16 Go, Docker inclus)
            return self.model.predict([(query, p) for p in passages], batch_size=2, show_progress_bar=False)
