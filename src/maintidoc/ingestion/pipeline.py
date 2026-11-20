"""Pipeline d'ingestion : inventaire -> éléments -> embeddings -> Qdrant + SQLite + manifeste d'index.

Usage : python -m maintidoc.ingestion.pipeline [--fake-encoders]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from datetime import datetime, timezone

from maintidoc.catalog import load_catalog, sha256_file
from maintidoc.config import get_settings
from maintidoc.ingestion.elements import Element
from maintidoc.ingestion.extract import extract_image, extract_pdf
from maintidoc.retrieval import index as idx
from maintidoc.retrieval.encoders import build_encoders
from maintidoc.storage import open_asset_store, open_metadata_store


def extract_all(settings, docs, log=print) -> tuple[list[Element], dict]:
    elements, stats = [], {}
    for meta in docs:
        if not meta.file.exists():
            raise FileNotFoundError(f"Fichier absent de l'inventaire : {meta.file}")
        if meta.sha256 and sha256_file(meta.file) != meta.sha256:
            raise ValueError(f"Empreinte SHA-256 différente du manifeste : {meta.document_id}")
        t0 = time.perf_counter()
        if meta.is_image:
            els = extract_image(meta, settings.assets_dir, meta.extra.get("elements_visuels", ""), settings.ocr_languages)
        else:
            els = extract_pdf(meta, settings.assets_dir, settings.page_dpi, settings.figure_dpi, settings.ocr_dpi,
                              settings.ocr_languages)
        stats[meta.document_id] = {"elements": len(els), "seconds": round(time.perf_counter() - t0, 2),
                                   "ocr": any(e.ocr for e in els)}
        log(f"  {meta.document_id:<36} {len(els):>3} éléments  {stats[meta.document_id]['seconds']:>5.1f} s"
            + ("  [OCR]" if stats[meta.document_id]["ocr"] else ""))
        elements.extend(els)
    return elements, stats


def build_index(fake_encoders: bool = False, log=print) -> dict:
    settings = get_settings()
    docs = load_catalog(settings.corpus_dir)
    if settings.assets_dir.exists():
        shutil.rmtree(settings.assets_dir)
    log(f"Extraction de {len(docs)} documents…")
    t0 = time.perf_counter()
    elements, stats = extract_all(settings, docs, log)
    t_extract = time.perf_counter() - t0

    log("Chargement des encodeurs…")
    text_enc, image_enc = build_encoders(settings, fake=fake_encoders)
    log(f"Embeddings texte ({text_enc.name}) de {len(elements)} éléments…")
    t1 = time.perf_counter()
    text_vecs = text_enc.encode([e.embed_text for e in elements])
    visual = [e for e in elements if idx.is_visual(e)]
    log(f"Embeddings image ({image_enc.name}) de {len(visual)} éléments visuels…")
    image_vecs = image_enc.encode_images([str(settings.assets_dir / e.image_path) for e in visual])
    t_embed = time.perf_counter() - t1

    client = idx.open_client(settings)
    idx.recreate_collections(client, text_vecs.shape[1], image_vecs.shape[1], server=bool(settings.qdrant_url))
    idx.upsert(client, idx.TEXT_COLLECTION, elements, text_vecs)
    idx.upsert(client, idx.IMAGE_COLLECTION, visual, image_vecs)
    client.close()

    assets = open_asset_store(settings)
    n_files = assets.put_dir(settings.assets_dir)
    log(f"Fichiers (pages, figures, photos) : {n_files} -> stockage {assets.kind}")
    store = open_metadata_store(settings)
    store.reset()
    by_doc = {}
    for e in elements:
        by_doc.setdefault(e.document_id, []).append(e)
    for meta in docs:
        store.add_document(meta, len(by_doc.get(meta.document_id, [])))
    store.add_elements(elements)

    counts = {}
    for e in elements:
        counts[e.element_type] = counts.get(e.element_type, 0) + 1
    corpus_hash = hashlib.sha256("".join(sorted((d.sha256 or "") for d in docs)).encode()).hexdigest()[:16]
    info = {
        "corpus_hash": corpus_hash, "documents": len(docs), "elements": len(elements), "visual_elements": len(visual),
        "by_type": counts, "text_model": text_enc.name, "image_model": image_enc.name,
        "text_dim": int(text_vecs.shape[1]), "image_dim": int(image_vecs.shape[1]),
        "extract_seconds": round(t_extract, 1), "embed_seconds": round(t_embed, 1),
        "qdrant": "serveur" if settings.qdrant_url else "embarqué",
        "metadata_store": "postgresql" if settings.database_url else "sqlite",
        "asset_store": assets.kind, "asset_files": n_files,
        "per_document": stats,
    }
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id = f"idx-{corpus_hash}-{'fake' if fake_encoders else 'real'}"
    store.add_run(run_id, created, info)
    store.commit()
    (settings.index_dir / "index_manifest.json").write_text(
        json.dumps({"run_id": run_id, "created_at": created, **info}, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Index {run_id} : {len(elements)} éléments ({counts}) — extraction {t_extract:.0f} s, embeddings {t_embed:.0f} s")
    return {"run_id": run_id, **info}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fake-encoders", action="store_true", help="encodeurs factices (tests sans modèle)")
    build_index(ap.parse_args().fake_encoders)


if __name__ == "__main__":
    main()
