"""OCR local (EasyOCR, CPU) pour les pages scannées et les photos.

Le texte OCR est une donnée non fiable : il est indexé et cité comme n'importe quel texte de document,
jamais interprété comme une instruction.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image


@dataclass
class OcrBlock:
    text: str
    bbox: tuple[float, float, float, float]   # pixels de l'image d'entrée
    confidence: float | None = None


@lru_cache(maxsize=1)
def _reader(languages: tuple[str, ...]):
    import easyocr  # import tardif : lourd, inutile si aucune page scannée
    return easyocr.Reader(list(languages), gpu=False, verbose=False)


def ocr_image(image: Image.Image, languages: tuple[str, ...] = ("fr", "en"), paragraph: bool = True) -> list[OcrBlock]:
    """Retourne les blocs de texte dans l'ordre de lecture (haut -> bas, gauche -> droite)."""
    arr = np.asarray(image.convert("RGB"))
    results = _reader(tuple(languages)).readtext(arr, paragraph=paragraph)
    blocks = []
    for res in results:
        box, text = res[0], res[1]
        conf = float(res[2]) if len(res) > 2 else None
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        blocks.append(OcrBlock(text=str(text).strip(), bbox=(min(xs), min(ys), max(xs), max(ys)), confidence=conf))
    blocks = [b for b in blocks if b.text]
    blocks.sort(key=lambda b: (round(b.bbox[1] / 15), b.bbox[0]))
    return blocks
