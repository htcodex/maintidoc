"""Rapport PDF du livrable 2 MaintiDoc (semaine 2). Appelé par build_livrable2.py."""

import csv
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

import pymupdf as fitz
import yaml
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (CondPageBreak, Image as RLImage, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from rapport_l1 import P, arrow, box, bullets, cp, table

ROOT = Path(__file__).resolve().parents[1]
CFG_LABEL = {"bm25": "BM25 seul", "dense": "Dense BGE-M3 seul", "hybride_texte": "Hybride texte (BM25 + dense)",
             "hybride_visuel": "Hybride + visuel CLIP (RRF non pondérée)",
             "hybride_visuel_pondere": "Hybride + visuel CLIP (RRF pondérée)",
             "hybride_visuel_pondere_rerank": "Hybride + visuel pondéré + reranker d'origine"}
TOC_TITLES = ["1. Objectifs et état de la semaine 2", "2. Environnement reproductible", "3. Ingestion",
              "4. Recherche texte et image", "5. Gestion des accès", "6. Évaluation de la recherche",
              "7. Tests automatisés", "8. Limites, écarts et suite", "Annexe — Questions pilotes"]
TOC = {}


def diagram_search():
    W, H = 482, 200
    d = Drawing(W, H)
    box(d, 2, 150, 92, 40, "Utilisateur\nquestion (+ photo)", fill=colors.HexColor("#dbe7f5"))
    box(d, 120, 150, 120, 40, "Droits\ngroupes de l'utilisateur", fill=colors.HexColor("#fde7e7"))
    box(d, 2, 82, 110, 44, "BM25\nsur les seuls éléments\nautorisés")
    box(d, 124, 82, 110, 44, "Dense BGE-M3\nQdrant + filtre\naccess_groups")
    box(d, 246, 82, 110, 44, "Visuel CLIP\nrequête FR + photo\nQdrant + filtre")
    box(d, 368, 82, 112, 44, "Index\nelements_text (1024)\nelements_image (512)", fill=colors.HexColor("#fff8e1"))
    box(d, 60, 14, 120, 44, "RRF pondérée (k = 60)\ndocuments remplacés\n× 0,5 et signalés")
    box(d, 200, 14, 110, 44, "Reranker (option)\nbge-reranker-v2-m3\n20 premiers")
    box(d, 330, 14, 150, 44, "Re-contrôle d'accès\npuis top k avec citations\n(document, page, élément)",
        fill=colors.HexColor("#e8f5e9"))
    arrow(d, [94, 170, 120, 170])
    arrow(d, [180, 150, 57, 126], "groupes", at=(110, 140))
    arrow(d, [180, 150, 179, 126])
    arrow(d, [180, 150, 301, 126])
    arrow(d, [356, 104, 368, 104], both=True)
    arrow(d, [234, 104, 246, 104])
    for x in (57, 179, 301):
        arrow(d, [x, 82, 120, 58])
    arrow(d, [180, 36, 200, 36])
    arrow(d, [310, 36, 330, 36])
    cp(d, 236, 186, 2)
    cp(d, 474, 54, 2)
    return d


def diagram_ingestion_l2():
    """Flux d'ingestion tel qu'implémenté en semaine 2 (outils réels)."""
    from rapport_l1 import diamond
    W, H = 482, 165
    d = Drawing(W, H)
    y1, y2, h = 100, 22, 42
    box(d, 2, 61, 64, h, "Corpus\nPDF + photos\n+ inventaire", fill=colors.HexColor("#dbe7f5"))
    diamond(d, 102, 82, 58, 46, "Couche\ntexte ?")
    box(d, 150, y1, 72, h, "PyMuPDF\ntexte, tableaux,\nfigures (bbox)")
    box(d, 150, y2, 72, h, "OCR EasyOCR\n(fr, en) CPU\n300 dpi")
    box(d, 240, y1, 72, h, "Découpage\nparagraph, table,\nfigure, page")
    box(d, 330, y1, 62, h, "Embeddings\nBGE-M3 (texte)\nCLIP (image)")
    box(d, 408, y1, 72, h, "Qdrant serveur\ntexte + image\npayload = méta.", fill=colors.HexColor("#fff8e1"))
    box(d, 240, y2, 72, h, "Métadonnées\ndoc, version, page,\nélément, groupes")
    box(d, 330, y2, 62, h, "PostgreSQL\nmétadonnées\njournal d'accès", fill=colors.HexColor("#fff8e1"))
    box(d, 408, y2, 72, h, "Stockage S3\nSeaweedFS : pages,\nfigures, photos", fill=colors.HexColor("#fff8e1"))
    arrow(d, [66, 82, 73, 82])
    arrow(d, [131, 82, 140, 82, 140, y1 + 21, 150, y1 + 21], "oui", at=(140, y1 + 26))
    arrow(d, [102, 59, 102, y2 + 21, 150, y2 + 21], "non", at=(118, y2 + 25))
    arrow(d, [186, y2 + h, 186, y1], "texte + position", at=(190, 76), anchor="start")
    arrow(d, [222, y1 + 21, 240, y1 + 21])
    arrow(d, [312, y1 + 21, 330, y1 + 21])
    arrow(d, [392, y1 + 21, 408, y1 + 21])
    arrow(d, [276, y1, 276, y2 + h])
    arrow(d, [312, y2 + 21, 330, y2 + 21])
    arrow(d, [34, 61, 34, 8, 444, 8, 444, y2], "SHA-256 vérifié ; rendus PNG conservés", at=(240, 11))
    return d


def img_from_pdf(path, page, dpi, clip=None, width_cm=8.0):
    with fitz.open(path) as pdf:
        pg = pdf[page - 1]
        pix = pg.get_pixmap(dpi=dpi, clip=fitz.Rect(clip) if clip else None)
    return RLImage(io.BytesIO(pix.tobytes("png")), width=width_cm * cm, height=width_cm * cm * pix.height / pix.width)


def build(cfg, results, index, git, out_path, _second=False):
    team = cfg["nom_equipe"]
    members = cfg["membres"]
    s = results["summary"]
    acc = results["access"]
    by_type = index["by_type"]
    per_q = list(csv.DictReader(open(ROOT / "reports/semaine2/retrieval_per_question.csv", encoding="utf-8")))
    qs = yaml.safe_load((ROOT / "data/eval/pilot_questions.yaml").read_text(encoding="utf-8"))["questions"]
    best_name, best = max(((k, v) for k, v in s.items() if "rerank" not in k), key=lambda kv: kv[1]["ndcg@5"])
    rr = s.get("hybride_visuel_pondere_rerank")

    def footer(c, doc):
        c.saveState()
        c.setFont("H", 7.5)
        c.setFillColor(colors.HexColor("#666666"))
        c.drawString(2 * cm, 1.1 * cm, f"L2 MaintiDoc — équipe {team} — ingestion, recherche et accès")
        c.drawRightString(19 * cm, 1.1 * cm, f"Page {doc.page}")
        c.restoreState()

    st = []
    # ------------------------------------------------ garde
    st += [Spacer(1, 3 * cm), P("MaintiDoc", "title"), Spacer(1, 0.3 * cm),
           P("Assistant documentaire multimodal et agentique pour la maintenance", "sub"), Spacer(1, 0.9 * cm),
           P("<b>Livrable 2 — Ingestion, recherche textuelle et visuelle, gestion des accès</b>", "sub"),
           P("Module IA générative multimodale — EMSI 2026 — Semaine 2", "sub"), Spacer(1, 1.4 * cm)]
    st.append(table([["Équipe", team]] + [[f"Membre {i + 1}", f"{m['prenom']} {m['nom']}" + (f" — {m['role']}" if m.get('role') else "")]
                                         for i, m in enumerate(members)]
                    + [["Enseignante", "Pr. Mariam CHERRABI"], ["Dépôt", cfg["github_url"]],
                       ["Version du code", f"branche {git['branch']}, commit {git['commit'] or 'à venir'}"],
                       ["Index évalué", results["index_run"]]], [4, 13], head=False, zebra=False, font=9))
    st += [Spacer(1, 1 * cm), P("<b>Sommaire</b>", "h2"),
           table([[t, str(TOC.get(t, "-"))] for t in TOC_TITLES], [14.5, 2.5], head=False, font=9), PageBreak()]

    # ------------------------------------------------ 1
    st += [P(TOC_TITLES[0], "h1"), P(
        "Le plan de la semaine 2 (cahier des charges, section 12) porte sur l'<b>ingestion</b>, la <b>recherche "
        "textuelle et visuelle</b> et la <b>gestion des accès</b>. Le critère de sortie fixé au livrable 1 était : "
        "« Recall@5 mesuré sur 30 questions pilotes ; 0 fuite inter-groupes ». Le tableau ci-dessous fait le point.")]
    st.append(table([
        ["Objectif (livrable 1)", "État", "Preuve"],
        ["Extraction PyMuPDF : texte, tableaux, figures, pages", "Fait", f"{index['elements']} éléments indexés ; "
         f"{by_type.get('figure', 0)} figures dont les identifiants correspondent au manifeste (test)"],
        ["OCR local des pages scannées", "Fait", f"2 documents scannés + 5 photos ; {by_type.get('ocr_text', 0)} "
         "éléments OCR ; EasyOCR (fr, en) sur CPU"],
        ["Métadonnées sur chaque élément", "Fait", "document, version, page, element_id, type, famille, équipements, "
         "statut, remplacement, groupes, SHA-256"],
        ["Index vectoriel Qdrant texte + image", "Fait", f"{index['text_model']} ({index['text_dim']}) ; "
         f"{index['image_model'].split('+')[0]} ({index['image_dim']})"],
        ["Recherche hybride + RRF + reranker d'origine", "Fait", "5 configurations comparées (section 6)"],
        ["Filtrage par groupe dans la requête, re-contrôle à l'affichage", "Fait",
         f"{acc['leaks']} fuite sur {acc['verified_results']} résultats ; {acc['forbidden_asset_opens_refused']}/"
         f"{acc['forbidden_asset_opens']} ouvertures d'images interdites refusées"],
        ["30 questions pilotes, Recall@5 / nDCG@5 / MRR@10", "Fait", f"meilleure config. sans reranker : Recall@5 "
         f"{best['recall@5']:.2f}, nDCG@5 {best['ndcg@5']:.2f}, MRR@10 {best['mrr@10']:.2f}"],
        ["Stockage PostgreSQL + fichiers objet", "Fait", "PostgreSQL 16 (métadonnées, journal d'accès) ; stockage S3 SeaweedFS à la place de MinIO (section 2) ; Qdrant serveur"],
    ], [5.6, 1.6, 9.8]))

    # ------------------------------------------------ 2
    st += [P(TOC_TITLES[1], "h1"), P(
        "Tout le code tourne sur un portable sans GPU (Intel i5-8265U, 4 cœurs / 8 fils, 16 Go de mémoire) : "
        "c'est la contrainte réelle de l'équipe à ce stade ; les modèles s'exécutent sur CPU. Les services de "
        "données tournent dans <b>Docker Compose</b> : Qdrant (vecteurs), PostgreSQL (métadonnées et journal "
        "d'accès) et un stockage objet S3 (pages, figures, photos). Les secrets sont générés localement dans "
        "<i>.env</i>, exclu de Git ; <i>.env.example</i> ne contient aucune valeur. Sans ces variables, le même code "
        "bascule en mode autonome (Qdrant embarqué, SQLite, dossier local) : c'est ce mode qu'utilisent les tests "
        "rapides et l'intégration continue."),
        table([["Service", "Image figée", "Rôle"],
               ["Qdrant", "qdrant/qdrant:v1.12.4", "Collections elements_text (1024) et elements_image (512), "
                "index de payload sur access_groups"],
               ["PostgreSQL", "postgres:16.4", "Tables documents, elements (access_groups en TEXT[] + index GIN), "
                "index_runs, access_events"],
               ["Stockage S3", "chrislusf/seaweedfs:3.97", "Bucket privé maintidoc-assets : pages, figures, photos"]],
              [3.0, 4.6, 9.4], font=7.6),
        P("<b>Écart au cahier des charges : MinIO remplacé par SeaweedFS.</b> Le téléchargement de l'image MinIO "
          "prévue (Docker Hub, puis quay.io) a été refusé : MinIO ne distribue plus d'images librement accessibles. "
          "SeaweedFS expose la même API S3 (le code client boto3 est identique) et est sous licence Apache 2.0, ce "
          "qui supprime au passage le risque de licence AGPL de MinIO noté au livrable 1 (S9).", "note"),
        table([["Étape", "Commande"],
               ["Installation", "pip install torch --index-url https://download.pytorch.org/whl/cpu ; "
                "pip install -e \".[corpus,retrieval,dev]\""],
               ["Corpus et inventaire", "python corpus/generate_corpus.py ; python livrable/build_livrable1.py"],
               ["Index", "python -m maintidoc.ingestion.pipeline"],
               ["Recherche (démo)", "python -m maintidoc.retrieval.cli --user u_tech_p01 \"Que signifie le voyant "
                "V2 orange fixe ?\""],
               ["Évaluation", "python -m maintidoc.evaluation.retrieval_eval"],
               ["Services", "copy .env.example .env (mots de passe locaux) ; docker compose up -d postgres qdrant s3"],
               ["Tests", "pytest (rapides, encodeurs factices) ; pytest -m services (Docker) ; pytest -m slow (OCR)"]], [3.6, 13.4], font=7.6),
        P("Versions figées : <i>requirements.lock</i> (pip freeze) et <i>config/models.lock.yaml</i> (révision exacte "
          "de chaque modèle Hugging Face). Un <i>index_manifest.json</i> relie chaque index à l'empreinte du corpus et "
          "aux modèles utilisés ; l'évaluation enregistre l'identifiant de l'index évalué.")]

    # ------------------------------------------------ 3
    st += [CondPageBreak(8 * cm), P(TOC_TITLES[2], "h1"),
           KeepTogether([diagram_ingestion_l2(), P("Figure 1 — Flux d'ingestion implémenté (outils réels)", "cap")]),
           P("3.1 Découpage en éléments citables", "h2"), table([
               ["Type", "Nombre", "Construction", "Identifiant"],
               ["paragraph", str(by_type.get("paragraph", 0)), "Blocs de texte regroupés sous leur rubrique ; en-tête et "
                "pied de page exclus ; 1 000 caractères max.", "paragraph_&lt;page&gt;_&lt;n&gt;"],
               ["table", str(by_type.get("table", 0)), "find_tables() pour la structure, texte relu par cellule ; une "
                "ligne = « en-tête : valeur ; … »", "table_&lt;page&gt;_&lt;n&gt;"],
               ["figure", str(by_type.get("figure", 0)), "Légende « Figure n — » + dessins vectoriels au-dessus + "
                "libellés ; image découpée à 150 dpi", "figure_&lt;page&gt;_&lt;n&gt; (= manifeste)"],
               ["page", str(by_type.get("page", 0)), "Rendu PNG 110 dpi de chaque page ; texte complet", "page_&lt;page&gt;"],
               ["ocr_text", str(by_type.get("ocr_text", 0)), "Pages sans couche texte rendues à 300 dpi, OCR EasyOCR",
                "ocr_&lt;page&gt;_&lt;n&gt;"],
               ["photo", str(by_type.get("photo", 0)), "Photo + éléments visuels de l'inventaire + texte lu par OCR",
                "photo_1"],
               ["Total", str(index["elements"]), f"dont {index['visual_elements']} éléments visuels (pages, figures, "
                "photos) indexés aussi dans le canal image", ""],
           ], [2.0, 1.5, 9.7, 3.8], font=7.6)]
    st += [P("3.2 Deux corrections nécessaires découvertes en cours de route", "h2"), bullets([
        "<b>Tableaux sans espaces.</b> <i>Table.extract()</i> de PyMuPDF renvoyait « Pompeenmarche » au lieu de « Pompe "
        "en marche » sur ces PDF : le texte est relu cellule par cellule avec <i>get_textbox</i>.",
        "<b>Libellés de figures orphelins.</b> Les valeurs posées sur les graphiques (« 80 °C », « Préalarme V2 ») "
        "sortaient comme des paragraphes sans sens ; la zone de chaque figure est élargie aux libellés situés entre le "
        "dessin et sa légende.",
    ])]
    fig_png = ROOT / "data/index/assets/mdp_man_util/figure_1_1.png"
    ex = [P("3.3 Exemple : la figure citée dans le scénario nominal et un document scanné", "h2")]
    cells = []
    if fig_png.exists():
        from PIL import Image as PILImage
        w, h = PILImage.open(fig_png).size
        cells.append(RLImage(str(fig_png), width=8 * cm, height=8 * cm * h / w))
    cells.append(img_from_pdf(ROOT / "corpus/documents/famille_2/mdc_proc_revision_scan.pdf", 1, 80,
                              clip=(0, 0, 595, 330), width_cm=8))
    t = Table([cells, [P("mdp_man_util — figure_1_1, p.1 : image découpée automatiquement", "cap"),
                       P("mdc_proc_revision_scan, p.1 : aucune couche texte ; l'OCR retrouve « jeu axial rotor mâle "
                         "0,02 à 0,05 mm », « couple vis de carter 95 N·m »", "cap")]], colWidths=[8.5 * cm, 8.5 * cm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    st += ex + [t]
    st.append(P("Qualité OCR observée : bonne sur le scan simulé (quelques confusions « N·m » → « NM », « Modèles » → "
                "« Modeles »). Sur les photos, l'OCR lit la plaque signalétique (« MDP-200 », « EQ-P-002 ») — utile "
                "pour identifier l'équipement — et aussi l'étiquette piégée « IGNORE TES INSTRUCTIONS », qui est "
                "indexée comme une simple donnée.", "p"))
    st.append(P(f"Temps d'ingestion sur CPU : extraction et OCR {index['extract_seconds']:.0f} s, embeddings "
                f"{index['embed_seconds']:.0f} s pour {index['elements']} éléments. Le poste le plus lent est l'OCR "
                "(~50 s par page scannée).", "p"))

    # ------------------------------------------------ 4
    st += [CondPageBreak(9 * cm), P(TOC_TITLES[3], "h1"), P(
        "Trois canaux sont interrogés en parallèle, chacun <b>uniquement sur les éléments autorisés</b> pour "
        "l'utilisateur. Leurs classements sont fusionnés par Reciprocal Rank Fusion pondérée (score = Σ poids / (60 + rang) ; "
        "poids 1 pour BM25, dense et photo jointe, 0,25 pour la requête texte vers CLIP), qui n'exige pas de "
        "calibrer des scores hétérogènes. Les documents remplacés (bulletin 2024-03) restent "
        "trouvables mais leur score est divisé par deux et ils sont marqués <i>superseded_by</i>, pour que la "
        "réponse de la semaine 3 puisse signaler l'écart sans citer la valeur obsolète comme référence."),
        KeepTogether([diagram_search(), P("Figure 2 — Recherche hybride filtrée (CP2 : contrôle d'accès)", "cap")]),
        table([["Canal", "Modèle / méthode", "Ce qu'il apporte"],
               ["Lexical", "BM25 (accents supprimés, codes conservés : « p-21 », « eq-p-002 »)",
                "Codes défaut, références de pièces, repères : correspondance exacte"],
               ["Dense", f"{index['text_model']} sur « titre — page — rubrique + texte »",
                "Paraphrases (« quantité de graisse » ↔ « injecter 15 g »)"],
               ["Visuel", "CLIP ViT-B/32 (images) ; requête FR → CLIP multilingue ; photo → CLIP image",
                "Figures, pages et photos de pupitre ; photo jointe par l'utilisateur"],
               ["Reranker", "bge-reranker-v2-m3 (d'origine, non adapté)", "Reclasse les 20 premiers ; point de départ "
                "de l'adaptation de la semaine 5"]], [2.0, 7.5, 7.5], font=7.6)]

    # ------------------------------------------------ 5
    st += [CondPageBreak(7 * cm), P(TOC_TITLES[4], "h1"), P(
        "Règle unique : un utilisateur voit un élément si l'un de ses groupes figure dans les <i>access_groups</i> de "
        "l'élément (hérités de l'inventaire). Elle est appliquée à trois endroits, de sorte qu'une erreur à l'un d'eux "
        "ne suffise pas à provoquer une fuite."), table([
            ["Où", "Mécanisme", "Ce qui est garanti"],
            ["Avant récupération", "BM25 calculé sur les éléments autorisés ; filtre MatchAny(access_groups) dans chaque "
             "requête Qdrant (texte et image)", "Un document interdit n'est jamais candidat : il ne peut ni être cité, ni "
             "influencer le classement"],
            ["Après fusion", "Chaque résultat est re-vérifié ; un écart serait journalisé comme anomalie",
             "Défense en profondeur si un canal était mal filtré"],
            ["Ouverture d'une image", "open_asset() vérifie le droit avant de lire le fichier ; AccessDenied générique",
             "Une URL ou un chemin connu ne suffit pas ; le refus ne révèle pas le titre"],
            ["Journal", "Table PostgreSQL access_events (+ fichier access_log.jsonl) : horodatage, utilisateur, action, cible, décision",
             "Traçabilité sans stocker les questions ni le contenu"],
        ], [3.0, 7.5, 6.5], font=7.6)]
    vis = acc["documents_visible_per_user"]
    st += [P("Résultats", "h2"), table([
        ["Utilisateur", "Groupes", "Documents visibles (sur 47)"],
        ["u_tech_p01 / u_tech_p02", "grp_pompes", str(vis.get("u_tech_p01"))],
        ["u_tech_c01", "grp_compresseurs", str(vis.get("u_tech_c01"))],
        ["u_resp_01", "grp_responsables + deux familles", str(vis.get("u_resp_01"))],
        ["u_presta_01", "grp_prestataires", str(vis.get("u_presta_01"))],
    ], [5, 6, 6]), P(
        f"Sur 10 requêtes × 5 utilisateurs (dont « contrat de maintenance prix », « tarifs astreinte » et la phrase "
        f"d'injection), <b>{acc['verified_results']} résultats</b> ont été vérifiés : <b>{acc['leaks']} fuite</b>. "
        f"<b>{acc['forbidden_asset_opens_refused']} / {acc['forbidden_asset_opens']}</b> tentatives d'ouverture d'une "
        "image interdite ont été refusées. Ce résultat porte sur ce jeu de tests ; il ne constitue pas une garantie "
        "générale.")]

    # ------------------------------------------------ 6
    st += [CondPageBreak(9 * cm), P(TOC_TITLES[5], "h1"), P(
        "30 questions pilotes annotées à la main (<i>data/eval/pilot_questions.yaml</i>) : 8 sur des tableaux, 7 sur "
        "des figures ou schémas, 9 de texte, 2 sur le document scanné, 3 avec photo jointe, 4 pièges (voyants "
        "similaires, versions contradictoires). Un élément est pertinent s'il est sur le bon document et la bonne page "
        "(et, si précisé, du bon type). La recherche est faite au nom de <i>u_resp_01</i>, qui voit les deux familles "
        "— le cas le plus exposé aux confusions pompe / compresseur — sauf pour les questions avec photo, posées par "
        "le technicien de la famille.")]
    rows = [["Configuration", "Recall@5", "nDCG@5", "MRR@10", "Latence méd.", "p95"]]
    for k, v in s.items():
        rows.append([CFG_LABEL.get(k, k), f"{v['recall@5']:.3f}", f"{v['ndcg@5']:.3f}", f"{v['mrr@10']:.3f}",
                     f"{v['latence_mediane_s']:.2f} s", f"{v['latence_p95_s']:.2f} s"])
    st.append(table(rows, [6.4, 2.0, 2.0, 2.0, 2.4, 2.2]))
    cats = defaultdict(lambda: defaultdict(list))
    for r in per_q:
        cats[r["config"]][r["categorie"]].append(float(r["ndcg@5"]))
    cats = {c: {k: sum(v) / len(v) for k, v in d.items()} for c, d in cats.items()}
    cat_names = sorted({c for d in cats.values() for c in d})
    st += [P("nDCG@5 par catégorie (le Recall@5 vaut 1,00 dans toutes les catégories sauf BM25 / texte)", "h2"), table(
        [["Configuration"] + cat_names] + [[CFG_LABEL.get(k, k)] + [f"{cats[k].get(c, 0):.2f}" for c in cat_names]
                                          for k in s], [6.4] + [10.6 / len(cat_names)] * len(cat_names), font=7.6)]

    misses = defaultdict(list)
    for r in per_q:
        if float(r["recall@5"]) == 0:
            misses[r["id"]].append(r["config"])
    q_by_id = {q["id"]: q for q in qs}
    best_rows = {r["id"]: r for r in per_q if r["config"] == best_name}
    analysis = [
        f"<b>Meilleure configuration sans reranker : {CFG_LABEL.get(best_name, best_name)}</b> (nDCG@5 {best['ndcg@5']:.3f}).",
    ]
    if "bm25" in s and "dense" in s:
        analysis.append(f"BM25 seul obtient déjà Recall@5 {s['bm25']['recall@5']:.2f} : le vocabulaire des questions "
                        "reprend celui des documents (codes, repères). Le dense seul est à "
                        f"{s['dense']['recall@5']:.2f} ; la fusion des deux est la plus robuste.")
    if "hybride_visuel" in s and "hybride_texte" in s:
        delta = s["hybride_visuel"]["ndcg@5"] - s["hybride_texte"]["ndcg@5"]
        pw = s.get("hybride_visuel_pondere", {}).get("ndcg@5", 0)
        analysis.append(f"<b>Le canal visuel CLIP dégrade le classement</b> : nDCG@5 {delta:+.3f} en RRF non pondérée. "
                        "Une requête texte comme « couple de serrage » ramène par CLIP des pages entières sans rapport, "
                        "qui prennent des places dans le top 5. Avec un poids de 0,25 sur ce canal (photo jointe à 1), "
                        "nDCG@5 remonte à " + f"{pw:.3f}" + ", toujours sous le texte seul. Sur les questions avec photo : "
                        f"{cats.get('hybride_visuel_pondere', {}).get('photo', 0):.2f} avec visuel pondéré contre "
                        f"{cats.get('hybride_texte', {}).get('photo', 0):.2f} en texte seul. Conclusion honnête : à ce "
                        "stade, CLIP ViT-B/32 n'apporte pas de gain mesurable sur ce corpus ; la photo sera surtout "
                        "exploitée par le VLM (semaine 3), et un encodeur de pages de documents sera testé.")
    if rr:
        analysis.append(f"Le <b>reranker d'origine</b> donne nDCG@5 {rr['ndcg@5']:.3f} (contre {best['ndcg@5']:.3f}) pour "
                        f"une latence médiane de {rr['latence_mediane_s']:.1f} s sur CPU. C'est la référence « avec "
                        "reranker d'origine » que l'adaptation de la semaine 5 devra battre.")
    if misses:
        ex = ", ".join(f"{i} ({q_by_id[i]['categorie']})" for i in list(misses)[:6])
        analysis.append(f"Questions manquées par au moins une configuration : {ex}. Elles alimentent l'analyse "
                        "d'erreurs et le jeu de négatifs difficiles du reranker.")
    st += [P("Analyse", "h2"), bullets(analysis), P(
        "Ces scores sont élevés parce que le corpus est petit et synthétique (risque D1 du livrable 1) : ils servent de "
        "point de comparaison interne, pas de promesse de performance sur de vrais manuels.", "note")]

    # ------------------------------------------------ 7
    st += [CondPageBreak(6 * cm), P(TOC_TITLES[6], "h1"), P(
        "30 tests rapides (pytest, ~1 min) dont 14 nouveaux, avec des encodeurs factices : ils vérifient la logique "
        "sans télécharger de modèle et peuvent tourner en intégration continue. 3 tests d'intégration "
        "(<i>pytest -m services</i>) s'exécutent contre les services Docker."), table([
            ["Test", "Ce qui est vérifié"],
            ["test_catalog_matches_inventory", "47 entrées, fichiers présents, statut et remplacement du bulletin 2024-03"],
            ["test_extraction_finds_tables_and_cited_figure", "Figure du pupitre et tableau des voyants (p.2) extraits"],
            ["test_figure_ids_match_manifest", "Les 13 figures extraites ont l'element_id et la page du manifeste"],
            ["test_footer_and_doc_header_not_in_paragraphs", "Pieds de page et en-têtes exclus des paragraphes"],
            ["test_search_never_returns_forbidden_documents", "Aucun résultat interdit, 5 utilisateurs × 4 requêtes"],
            ["test_prestataire_sees_only_safety", "Le prestataire ne voit que sécurité et glossaire"],
            ["test_contract_hidden_from_technicians", "Contrat invisible aux techniciens, trouvé par le responsable"],
            ["test_open_asset_refused_without_rights", "Ouverture d'une figure pompe refusée au technicien compresseurs"],
            ["test_unknown_user_without_groups_gets_nothing", "Utilisateur sans groupe : aucun résultat"],
            ["test_family_filter_hard_negative", "Le technicien pompes ne reçoit jamais le manuel compresseur"],
            ["test_superseded_document_ranked_after_active", "Le bulletin actif 2025-01 sort dans les 3 premiers"],
            ["test_metrics, test_tokenize…", "Calcul de Recall@5, nDCG@5, MRR@10 ; normalisation des requêtes"],
            ["test_ocr_scanned_document (slow)", "L'OCR retrouve le texte de la procédure scannée"],
            ["test_sql_access_filter_matches_python_rule (services)", "Le filtre SQL PostgreSQL (TEXT[] &amp;&amp;) donne "
             "exactement les mêmes éléments que la règle Python, pour les 5 utilisateurs"],
            ["test_s3_assets_readable_only_with_rights (services)", "Figure lue dans S3 par le technicien pompes, "
             "refusée au technicien compresseurs"],
            ["test_qdrant_server_filter (services)", "Filtre du serveur Qdrant : le prestataire ne voit que la sécurité"],
        ], [7.2, 9.8], font=7.4)]

    # ------------------------------------------------ 8
    st += [CondPageBreak(7 * cm), P(TOC_TITLES[7], "h1"), table([
        ["Point", "Décision / constat", "Suite"],
        ["MinIO", "Image non téléchargeable : remplacé par SeaweedFS (API S3, Apache 2.0)", "Mettre à jour l'architecture du livrable 1 ; services applicatifs (API, UI) dans Compose en semaine 6"],
        ["Pas de GPU", "Modèles d'embedding et reranker sur CPU : index ~10 min, recherche < 1 s sans reranker",
         "VLM 7B impossible en local : repli 3B quantifié ou GPU distant à décider en début de semaine 3 (risque R7)"],
        ["CLIP et schémas", "CLIP ViT-B/32 reconnaît mal le texte des schémas", "Tester un encodeur de pages de "
         "documents (type ColPali) si le temps le permet"],
        ["Corpus court", "Scores élevés par construction", "Ajout de manuels publics réels pour un test de "
         "généralisation (semaine 5)"],
        ["Photos ambiguës", "L'OCR lit la plaque quand elle est nette ; la photo floue ne donne rien",
         "Règle de clarification dans le workflow (semaines 3–4)"],
    ], [3.2, 7.6, 6.2], font=7.6), P("Semaine 3", "h2"), bullets([
        "Brancher le VLM sur les éléments récupérés (texte + images de pages et figures).",
        "Prompts versionnés <i>answer_v1</i>, <i>visual_analysis_v1</i>, <i>evidence_check_v1</i> ; schéma Pydantic de réponse.",
        "Vérificateur de citations : la citation doit être un élément récupéré <b>et</b> soutenir l'affirmation.",
    ])]

    # ------------------------------------------------ annexe
    st += [PageBreak(), P(TOC_TITLES[8], "h1"), P(
        f"Rang du premier élément pertinent pour la configuration « {CFG_LABEL.get(best_name, best_name)} » "
        "(— : absent des 10 premiers).")]
    arows = [["ID", "Cat.", "Question", "Rang", "Premier résultat"]]
    for q in qs:
        r = best_rows.get(q["id"], {})
        arows.append([q["id"], q["categorie"], q["question"] + (" [photo]" if q.get("photo") else ""),
                      r.get("first_rank") or "—", (r.get("top1") or "").replace("#", " # ")])
    st.append(table(arows, [1.0, 1.5, 7.3, 1.1, 6.1], font=6.9))

    SimpleDocTemplate(str(out_path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                      bottomMargin=1.8 * cm, title=f"L2 MaintiDoc — {team} — Rapport",
                      author=", ".join(f"{m['prenom']} {m['nom']}" for m in members)).build(
        st, onFirstPage=lambda c, d: None, onLaterPages=footer)
    if not _second:
        with fitz.open(out_path) as pdf:
            for t in TOC_TITLES:
                TOC[t] = next((i + 1 for i, pg in enumerate(pdf) if i > 0 and t in pg.get_text()), "-")
        build(cfg, results, index, git, out_path, _second=True)
