"""Extraction PyMuPDF : découpe un document en éléments citables (paragraphes, tableaux, figures, pages).

- Texte : blocs PyMuPDF regroupés sous leur rubrique (titre de section), en excluant en-tête et pied de page.
- Tableaux : `find_tables()` pour la structure ; texte relu cellule par cellule (`get_textbox`), car
  `extract()` supprime les espaces sur les PDF du corpus.
- Figures : dessins vectoriels regroupés (`cluster_drawings`) et rattachés à la légende « Figure n — ».
- Pages scannées (pas de couche texte) : OCR de la page rendue en image.
- Chaque page est aussi un élément visuel (rendu PNG), conservé pour le canal image et le VLM.
"""

import re
from pathlib import Path

import pymupdf as fitz
from PIL import Image

from maintidoc.catalog import DocumentMeta
from maintidoc.ingestion.elements import Element
from maintidoc.ingestion.ocr import ocr_image

CAPTION_RE = re.compile(r"^Figure\s+\d+\s+—")
FOOTER_MARGIN = 50          # points : bande du pied de page ignorée
MAX_CHUNK_CHARS = 1000
MIN_TEXT_FOR_NATIVE = 20    # en dessous : page considérée comme scannée


def _inter(a, b) -> float:
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _area(r) -> float:
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _inside(block_bbox, region, ratio=0.6) -> bool:
    a = _area(block_bbox)
    return a > 0 and _inter(block_bbox, region) / a >= ratio


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _base(meta: DocumentMeta) -> dict:
    return dict(document_id=meta.document_id, version=meta.version, title=meta.title, family=meta.family,
                equipment_ids=meta.equipment_ids, doc_type=meta.doc_type, status=meta.status,
                superseded_by=meta.superseded_by, access_groups=meta.access_groups,
                confidentiality=meta.confidentiality, language=meta.language, sha256=meta.sha256)


def _save_png(pix_or_img, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(pix_or_img, Image.Image):
        pix_or_img.save(path, optimize=True)
    else:
        pix_or_img.save(str(path))


# ------------------------------------------------------------------ tableaux

def _tables(page) -> list[tuple[tuple, list[list[str]]]]:
    out = []
    for t in page.find_tables().tables:
        rows = []
        for row in t.rows:
            cells = [_clean(page.get_textbox(fitz.Rect(c))) if c else "" for c in row.cells]
            if any(cells):
                rows.append(cells)
        if rows:
            out.append((tuple(t.bbox), rows))
    return out


def _serialize_table(rows: list[list[str]]) -> str:
    header, body = rows[0], rows[1:]
    if not body:
        return " | ".join(header)
    lines = []
    for r in body:
        pairs = [f"{h}: {v}" if h else v for h, v in zip(header, r) if v]
        lines.append(" ; ".join(pairs))
    return "\n".join(lines)


# ------------------------------------------------------------------ figures

def _figures(page, text_blocks, table_boxes):
    """Associe chaque légende « Figure n — » au groupe de dessins situé juste au-dessus."""
    captions = [b for b in text_blocks if CAPTION_RE.match(b["text"])]
    clusters = [tuple(r) for r in page.cluster_drawings()]
    clusters = [c for c in clusters if _area(c) > 2000 and not any(_inter(c, t) > 0.5 * _area(c) for t in table_boxes)]
    figures, used = [], set()
    for cap in sorted(captions, key=lambda b: b["bbox"][1]):
        cy = cap["bbox"][1]
        best, best_gap = None, 1e9
        for i, c in enumerate(clusters):
            gap = cy - c[3]
            if i not in used and -5 <= gap <= 60 and gap < best_gap:
                best, best_gap = i, gap
        if best is not None:
            used.add(best)
            region = clusters[best]
        else:  # pas de dessin trouvé : zone de 220 pt au-dessus de la légende
            region = (cap["bbox"][0] - 40, max(0, cy - 220), cap["bbox"][2] + 40, cy)
        # Les libellés posés autour du dessin (axes, repères) appartiennent à la figure : on élargit la zone
        # à tout bloc de texte non-titre situé entre le haut du dessin (-25 pt) et la légende.
        top = region[1] - 40
        for b in text_blocks:
            bb = b["bbox"]
            if b is cap or (b["bold"] and b["size"] >= 11.5) or CAPTION_RE.match(b["text"]):
                continue
            if bb[1] >= top and bb[3] <= cy + 1 and not any(_inside(bb, t) for t in table_boxes):
                region = (min(region[0], bb[0]), min(region[1], bb[1]), max(region[2], bb[2]), max(region[3], bb[3]))
        region = (region[0] - 4, region[1] - 4, region[2] + 4, region[3] + 4)
        figures.append((region, cap))
    return figures


# ------------------------------------------------------------------ texte

def _text_blocks(page):
    blocks = []
    h = page.rect.height
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        spans = [s for line in b["lines"] for s in line["spans"]]
        text = _clean(" ".join(s["text"] for s in spans))
        if not text or b["bbox"][1] > h - FOOTER_MARGIN:
            continue
        size = max(s["size"] for s in spans)
        bold = all("Bold" in s["font"] for s in spans if s["text"].strip())
        blocks.append({"bbox": tuple(b["bbox"]), "text": text, "size": size, "bold": bold})
    return blocks


def _is_doc_header(block) -> bool:
    t = block["text"]
    return block["size"] >= 15 or t.startswith("Réf. ") or t.startswith("Modèles :") or \
        t.startswith("Extraction du service")


def _paragraphs(blocks, base, page_no, start_heading):
    chunks, cur, cur_box, heading = [], [], None, start_heading

    def flush():
        nonlocal cur, cur_box
        if cur:
            chunks.append((heading, " ".join(cur), cur_box))
        cur, cur_box = [], None

    for b in blocks:
        if b["bold"] and b["size"] >= 11.5:
            flush()
            heading = b["text"]
            continue
        if cur and sum(len(x) for x in cur) + len(b["text"]) > MAX_CHUNK_CHARS:
            flush()
        cur.append(b["text"])
        bb = b["bbox"]
        cur_box = bb if cur_box is None else (min(cur_box[0], bb[0]), min(cur_box[1], bb[1]),
                                              max(cur_box[2], bb[2]), max(cur_box[3], bb[3]))
    flush()
    els = [Element(element_id=f"paragraph_{page_no}_{i}", element_type="paragraph", page=page_no, text=t,
                   heading=hd, bbox=bx, **base) for i, (hd, t, bx) in enumerate(chunks, 1)]
    return els, heading


# ------------------------------------------------------------------ document

def extract_pdf(meta: DocumentMeta, assets_dir: Path, page_dpi=110, figure_dpi=150, ocr_dpi=300,
                ocr_languages=("fr", "en")) -> list[Element]:
    base = _base(meta)
    elements: list[Element] = []
    heading = ""
    with fitz.open(meta.file) as pdf:
        for pno, page in enumerate(pdf, 1):
            page_png = Path(meta.document_id) / f"page_{pno}.png"
            pix = page.get_pixmap(dpi=page_dpi)
            _save_png(pix, assets_dir / page_png)
            native = page.get_text().strip()

            if len(native) < MIN_TEXT_FOR_NATIVE:          # page scannée -> OCR
                scale = 72 / ocr_dpi
                img = Image.open(__import__("io").BytesIO(page.get_pixmap(dpi=ocr_dpi).tobytes("png")))
                blocks = ocr_image(img, ocr_languages)
                texts, n, cur, box = [], 0, [], None
                for blk in blocks:
                    bb = tuple(v * scale for v in blk.bbox)
                    cur.append(blk.text)
                    box = bb if box is None else (min(box[0], bb[0]), min(box[1], bb[1]),
                                                  max(box[2], bb[2]), max(box[3], bb[3]))
                    if sum(len(x) for x in cur) > MAX_CHUNK_CHARS / 2:
                        n += 1
                        texts.append((n, " ".join(cur), box))
                        cur, box = [], None
                if cur:
                    n += 1
                    texts.append((n, " ".join(cur), box))
                for i, t, bx in texts:
                    elements.append(Element(element_id=f"ocr_{pno}_{i}", element_type="ocr_text", page=pno,
                                            text=t, bbox=bx, ocr=True, **base))
                page_text = " ".join(t for _, t, _ in texts)
                elements.append(Element(element_id=f"page_{pno}", element_type="page", page=pno, text=page_text,
                                        bbox=tuple(page.rect), image_path=page_png.as_posix(), ocr=True, **base))
                continue

            blocks = _text_blocks(page)
            tables = _tables(page)
            table_boxes = [t[0] for t in tables]
            figures = _figures(page, blocks, table_boxes)

            for i, (bbox, rows) in enumerate(tables, 1):
                elements.append(Element(element_id=f"table_{pno}_{i}", element_type="table", page=pno,
                                        text=_serialize_table(rows), bbox=bbox, heading=heading, **base))
            fig_regions = []
            for i, (region, cap) in enumerate(figures, 1):
                clip = fitz.Rect(region) & page.rect
                labels = _clean(page.get_textbox(clip)).replace(cap["text"], "").strip()
                png = Path(meta.document_id) / f"figure_{pno}_{i}.png"
                _save_png(page.get_pixmap(dpi=figure_dpi, clip=clip), assets_dir / png)
                elements.append(Element(element_id=f"figure_{pno}_{i}", element_type="figure", page=pno,
                                        text=f"{cap['text']}\nLibellés : {labels}", bbox=tuple(clip),
                                        image_path=png.as_posix(), heading=heading, **base))
                fig_regions.append(region)
                fig_regions.append(cap["bbox"])

            body = [b for b in blocks if not _is_doc_header(b)
                    and not any(_inside(b["bbox"], t) for t in table_boxes)
                    and not any(_inside(b["bbox"], r) for r in fig_regions)]
            paras, heading = _paragraphs(body, base, pno, heading)
            elements.extend(paras)
            for e in elements:  # rubrique des tableaux/figures : celle en cours au-dessus d'eux
                if e.page == pno and e.element_type in ("table", "figure") and e.bbox:
                    above = [b for b in blocks if b["bold"] and b["size"] >= 11.5 and b["bbox"][3] <= e.bbox[1] + 2]
                    if above:
                        e.heading = max(above, key=lambda b: b["bbox"][3])["text"]

            page_text = _clean(" ".join(b["text"] for b in blocks if not _is_doc_header(b)))
            elements.append(Element(element_id=f"page_{pno}", element_type="page", page=pno, text=page_text,
                                    bbox=tuple(page.rect), image_path=page_png.as_posix(), **base))
    return elements


def extract_image(meta: DocumentMeta, assets_dir: Path, visual_desc: str, ocr_languages=("fr", "en")) -> list[Element]:
    """Photo du corpus : un élément visuel ; texte = titre + éléments visuels déclarés + texte lu par OCR."""
    img = Image.open(meta.file)
    png = Path(meta.document_id) / "photo_1.png"
    _save_png(img.convert("RGB"), assets_dir / png)
    ocr_text = " ".join(b.text for b in ocr_image(img, ocr_languages))
    text = f"{meta.title}. Éléments visuels : {visual_desc}."
    if ocr_text:
        text += f"\nTexte lu sur la photo (OCR) : {ocr_text}"
    return [Element(element_id="photo_1", element_type="photo", page=1, text=text, image_path=png.as_posix(),
                    ocr=bool(ocr_text), **_base(meta))]
