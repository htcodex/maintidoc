"""Encodeurs : texte (BGE-M3), image (CLIP) et requête texte -> espace CLIP (CLIP multilingue).

Les modèles sont chargés une seule fois et exécutés sur CPU si aucun GPU n'est disponible.
Un encodeur factice (`HashingEncoder`) permet de tester toute la chaîne sans télécharger de modèle.
"""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from typing import Protocol, Sequence

import numpy as np


class TextEncoder(Protocol):
    name: str
    dim: int

    def encode(self, texts: Sequence[str], is_query: bool = False) -> np.ndarray: ...


class ImageEncoder(Protocol):
    name: str
    dim: int

    def encode_images(self, paths: Sequence[str]) -> np.ndarray: ...

    def encode_queries(self, texts: Sequence[str]) -> np.ndarray: ...


def _normalize(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.clip(n, 1e-12, None)


@lru_cache(maxsize=4)
def _st_model(name: str):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(name, device="cpu")


class SentenceTransformerText:
    def __init__(self, model_name: str, batch_size: int = 8, max_seq_length: int = 512):
        self.name = model_name
        self.model = _st_model(model_name)
        self.model.max_seq_length = max_seq_length
        self.dim = self.model.get_sentence_embedding_dimension()
        self.batch_size = batch_size

    def encode(self, texts, is_query=False):
        return self.model.encode(list(texts), batch_size=self.batch_size, normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=False).astype(np.float32)


class ClipImage:
    """Images avec CLIP ViT-B/32 ; requêtes (français) avec l'encodeur texte multilingue aligné sur CLIP."""

    def __init__(self, image_model: str, text_model: str):
        self.name = f"{image_model}+{text_model}"
        self.image_model = _st_model(image_model)
        self.text_model = _st_model(text_model)
        self.dim = self.image_model.get_sentence_embedding_dimension() or 512

    def encode_images(self, paths):
        from PIL import Image
        imgs = [Image.open(p).convert("RGB") for p in paths]
        return self.image_model.encode(imgs, batch_size=8, normalize_embeddings=True, convert_to_numpy=True,
                                       show_progress_bar=False).astype(np.float32)

    def encode_query_images(self, images):
        return self.image_model.encode([i.convert("RGB") for i in images], normalize_embeddings=True,
                                       convert_to_numpy=True, show_progress_bar=False).astype(np.float32)

    def encode_queries(self, texts):
        return self.text_model.encode(list(texts), normalize_embeddings=True, convert_to_numpy=True,
                                      show_progress_bar=False).astype(np.float32)


# ------------------------------------------------------------------ factices (tests, CI)

_TOKEN = re.compile(r"[\w\-]+", re.UNICODE)


class HashingEncoder:
    """Sac de mots haché (déterministe) : remplace les modèles dans les tests unitaires."""

    def __init__(self, dim: int = 256, name: str = "hashing-test"):
        self.dim, self.name = dim, name

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        for tok in _TOKEN.findall(text.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0
        return v

    def encode(self, texts, is_query=False):
        return _normalize(np.stack([self._vec(t) for t in texts]))

    # interface ImageEncoder : l'« image » est représentée par le nom de fichier (suffisant pour les tests)
    def encode_images(self, paths):
        return _normalize(np.stack([self._vec(str(p).replace("_", " ")) for p in paths]))

    def encode_query_images(self, images):
        return _normalize(np.stack([self._vec("photo") for _ in images]))

    def encode_queries(self, texts):
        return self.encode(texts)


def build_encoders(settings, fake: bool = False):
    if fake:
        return HashingEncoder(256, "hashing-text"), HashingEncoder(128, "hashing-image")
    return (SentenceTransformerText(settings.text_model),
            ClipImage(settings.image_model, settings.image_text_model))
