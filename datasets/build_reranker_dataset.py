"""Construit le jeu d'adaptation du reranker : passages, questions et triplets (question, positif, négatif difficile).

Usage : python datasets/build_reranker_dataset.py   (après corpus/generate_corpus.py)
Sortie : datasets/reranker/{passages,queries}.jsonl, triplets_{train,val,test}.jsonl, review_sample.csv

- Passages : un par paragraphe, liste, ligne de tableau ou légende de figure, avec page et document.
- Questions : gabarits par type de tableau + questions rédigées à la main pour les paragraphes.
- Pertinence : un passage est pertinent s'il est de la même famille (ou transverse) et contient une clé de
  réponse (et une clé d'entité si définie). Les négatifs ne sont jamais pertinents : cela évite les faux négatifs.
- Négatifs difficiles : recouvrement lexical, bonus pour le document « jumeau » de l'autre famille
  (ex. voyant orange MDP vs MDC) ; documents remplacés imposés comme négatifs.
- Séparation par groupe de documents (un document et son jumeau restent dans le même ensemble).
"""

import csv
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

import pymupdf
import yaml

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
OUT = ROOT / "datasets" / "reranker"
sys.path.insert(0, str(CORPUS))

import content_mdc  # noqa: E402
import content_mdp  # noqa: E402
import content_trans  # noqa: E402

SEED = 20261023
NEGATIVES_PER_QUERY = 4
TEST_GROUPS = {"FICHE-ALARMES", "GUIDE-DEPANNAGE"}
VAL_GROUPS = {"PIECES", "CHECKLIST-INSPECTION", "TRANS-GLOSSAIRE"}
FAM = {"MDP": ("pompe MDP", "pompes MDP"), "MDC": ("compresseur MDC", "compresseurs MDC"),
       "TRANSVERSE": ("équipement", "équipements")}
STOPWORDS = set("le la les un une des de du d l à au aux et ou en sur pour par est sont que qui quoi quel quelle "
                "quels quelles ce cette ces se sa son ses il elle on faut faire a y ne pas dans avec lors "
                "comment quand où peut-on doit-on cela".split())


def norm(s):
    return re.sub(r"\s+", " ", s.replace(" ", " ").replace("\xa0", " ").replace("’", "'")).strip().lower()


def tokens(s):
    return {t for t in re.findall(r"[\w\-·°³]+", norm(s)) if t not in STOPWORDS and len(t) > 1}


def group_of(doc_id):
    return doc_id if doc_id.startswith("TRANS") else doc_id.split("-", 1)[1]


def split_of(doc_id):
    g = group_of(doc_id)
    return "test" if g in TEST_GROUPS else "val" if g in VAL_GROUPS else "train"


def short(text):
    return re.split(r" \(| —|;|,", text)[0].strip()


# ---------------------------------------------------------------- passages

def build_passages(docs, manifest):
    passages = []
    for doc in docs:
        entry = manifest[doc["id"]]
        with pymupdf.open(CORPUS / entry["file"]) as pdf:
            page_texts = [re.sub(r"\s+", "", norm(p.get_text())) for p in pdf]

        def page_of(probe):
            key = re.sub(r"\s+", "", norm(probe))[:18]
            return next((i + 1 for i, t in enumerate(page_texts) if key and key in t), 1)

        heading, k, figures = "", 0, iter(entry["figures"])

        def add(text, element_type, page, element_id=None, extra=None):
            nonlocal k
            k += 1
            passages.append({"passage_id": f"{doc['id']}#{k:02d}", "document_id": doc["id"],
                             "document_version": doc["version"], "status": doc["status"],
                             "equipment_family": doc["family"], "element_type": element_type,
                             "element_id": element_id or f"{element_type}_{page}_{k}", "page": page,
                             "text": f"{doc['title']} — {heading + ' — ' if heading else ''}{text}", **(extra or {})})

        for block in doc["blocks"]:
            kind = block[0]
            if kind == "h1":
                heading = block[1]
            elif kind in ("p", "warn"):
                add(block[1], "paragraph", page_of(block[1]))
            elif kind == "list":
                add(" ".join(f"{i + 1}. {item}" for i, item in enumerate(block[1])), "list", page_of(block[1][0]))
            elif kind == "table":
                header = block[1][0]
                for row in block[1][1:]:
                    text = " ; ".join(f"{h} : {c}" for h, c in zip(header, row))
                    probe = max(row, key=len)
                    add(text, "table_row", page_of(probe), extra={"_header": header, "_row": row})
            elif kind == "fig":
                fig = next(figures)
                add(block[1], "figure", fig["page"], element_id=fig["element_id"])
    return passages


# ---------------------------------------------------------------- questions

def _entity_of_operation(op):
    first, _, rest = op.partition(" ")
    return rest.lower() if first in ("Remplacement", "Contrôle", "Révision") else first.lower()


def table_questions(p):
    """Gabarits par type de tableau : liste de (question, clés de réponse, clés d'entité)."""
    header, row, fam = p["_header"], p["_row"], p["equipment_family"]
    f1, fp = FAM[fam]
    h0, q = header[0], []
    if h0 == "Caractéristique":
        for model, val in zip(header[1:], row[1:]):
            q += [(f"{row[0]} du {model} ?", [val], [row[0], model]),
                  (f"Quelle valeur de « {row[0].lower()} » pour le modèle {model} ?", [val], [row[0], model])]
    elif h0 == "Voyant":
        voyant, etat, sig, action = row
        keys, color = [short(sig), f"{voyant} {etat}"], voyant.split()[1]
        q += [(f"Que signifie le voyant {voyant} {etat.lower()} sur un {f1} ?", keys, []),
              (f"Sur le pupitre d'un {f1}, le voyant {color} est {etat.lower()} : qu'est-ce que cela indique ?",
               keys, [])]
        if action != "Aucune":
            q.append((f"Que faire quand le voyant {voyant} est {etat.lower()} sur un {f1} ?", keys, []))
    elif h0 == "Code":
        code, lib, cause, verif = row
        keys = [short(lib), code]
        q += [(f"Que signifie le code {code} sur un {f1} ?", keys, []),
              (f"Quelle est la cause probable du défaut {code} ?", keys, []),
              (f"Que vérifier en premier en cas de code {code} sur un {f1} ?", keys, [])]
    elif h0 == "Opération":
        op, period, proc = row
        if op == "Vidange huile":  # contradiction volontaire : traitée en question manuelle
            return []
        ent = [_entity_of_operation(op)]
        q += [(f"À quelle fréquence faut-il réaliser : {op.lower()} sur les {fp} ?", [short(period)], ent),
              (f"Quelle procédure suivre pour : {op.lower()} ({fp}) ?", [proc], [])]
    elif h0 == "Assemblage":
        if "bride" in row[0]:  # valeur remplacée par MDP-BT-2025-01 : question manuelle
            return []
        q.append((f"Quel couple de serrage pour : {row[0].lower()} ({fp}) ?", [row[1]], [row[0][:12]]))
    elif h0 == "Repère":
        q.append((f"À quoi sert le repère {row[0]} sur l'installation d'une {f1} ?", [row[1]], []))
    elif h0 == "Écart":
        q.append((f"Quelle tolérance de {row[0].lower()} pour l'accouplement d'une {f1} ?", [row[1]], [row[0]]))
    elif h0 == "Position":
        for model, ref in zip(header[1:], row[1:]):
            q.append((f"Quelle référence de roulement {row[0].lower()} pour la {model} ?", [ref], []))
    elif h0 == "Rep.":
        for model, ref in zip(header[2:], row[2:]):
            q.append((f"Quelle est la référence de « {row[1].lower()} » pour le {model.replace('Réf. ', '')} ?",
                      [short(ref)], [row[1]]))
    elif h0 == "#":
        q.append((f"Quel critère pour « {row[1].lower()} » lors de l'inspection mensuelle des {fp} ?",
                  [row[2]], [row[1]]))
    elif h0 == "Symptôme":
        q.append((f"Quelles sont les causes possibles de « {row[0].lower()} » sur un {f1} ?", [short(row[1])], []))
    elif h0 == "Contrôle":
        q.append((f"Valeur admissible du {row[0].lower()} lors de la révision 8 000 h du bloc vis MDC ?",
                  [row[1]], [row[0]]))
    elif h0 == "Intervention":
        q.append((f"Quels EPI sont obligatoires pour : {row[0].lower()} ?", [short(row[1])], []))
    elif h0 == "Terme":
        q.append((f"Que veut dire « {row[0]} » en maintenance ?", [row[1]], []))
    elif h0 == "Prestation":
        q.append((f"Quel est le prix forfaitaire de « {row[0].lower()} » ?", [row[1]], []))
    else:
        raise ValueError(f"Type de tableau sans gabarit : {h0}")
    return q


# (document, question, clé identifiant le positif, autres clés rendant un passage pertinent, négatifs imposés)
MANUAL = [
    ("MDP-MAN-UTIL", "À quoi servent les pompes MDP-200 et MDP-350 ?", "transfert d'eau claire", [], []),
    ("MDP-MAN-UTIL", "Quelles sont les étapes de mise en service d'une pompe MDP ?", "amorcer la pompe", [], []),
    ("MDP-MAN-UTIL", "Où se trouve la plaque signalétique d'une pompe MDP ?", "rivetée sur le corps", [], []),
    ("MDP-MAN-UTIL", "Le voyant orange fixe arrête-t-il la pompe MDP ?", "n'entraîne pas l'arrêt",
     ["préalarme température palier"], []),
    ("MDP-MAN-UTIL", "Que contient le pupitre de commande d'une pompe MDP ?", "regroupe les voyants", ["pupitre"], []),
    ("MDP-MAN-MAINT", "Comment interpréter une élévation brutale de la température palier MDP ?",
     "élévation brutale", [], []),
    ("MDP-MAN-MAINT", "Pour quelle classe de visserie les couples de serrage MDP sont-ils donnés ?", "classe 8.8", [], []),
    ("MDP-FICHE-ALARMES", "Que faire après trois défauts identiques en 24 h sur une pompe MDP ?",
     "trois défauts identiques", [], []),
    ("MDP-SCH-ELEC", "À quelle valeur est réglé le relais thermique F1 de la MDP-350 ?", "41 a", [], []),
    ("MDP-PROC-GRAISSAGE", "Quelle graisse utiliser pour les roulements d'une pompe MDP ?", "nlgi 2", [], []),
    ("MDP-PROC-GRAISSAGE", "Quelle quantité de graisse injecter côté accouplement sur une pompe MDP ?",
     "15 g côté accouplement", [], []),
    ("MDP-PROC-GRAISSAGE", "Que faire si la préalarme de température persiste après un graissage MDP ?",
     "si la préalarme persiste", [], []),
    ("MDP-PROC-GRAISSAGE", "Quand faut-il graisser les roulements d'une pompe MDP ?", "graissage périodique",
     ["graissage des roulements"], []),
    ("MDP-PROC-GARNITURE", "Quelle garniture mécanique de rechange pour une MDP-350 ?", "gm-350", [], []),
    ("MDP-PROC-GARNITURE", "Une petite fuite après remplacement de la garniture MDP est-elle normale ?", "rodage",
     [], []),
    ("MDP-PROC-GARNITURE", "Quelles étapes pour remplacer la garniture mécanique d'une pompe MDP ?",
     "extraire la roue", ["garniture"], []),
    ("MDP-PROC-ALIGNEMENT", "Comment corriger l'alignement moteur-pompe sur une MDP ?", "cales sous le moteur",
     ["alignement"], []),
    ("MDP-PROC-DEMONTAGE-ROULEMENTS", "À quelle température chauffer les roulements neufs d'une pompe MDP ?",
     "110 °c", [], []),
    ("MDP-PROC-DEMONTAGE-ROULEMENTS", "Comment extraire les roulements d'une pompe MDP ?", "arrache-moyeu", [], []),
    ("MDP-PROC-AMORCAGE", "La pompe MDP est-elle auto-amorçante ?", "pas auto-amorçante", [], []),
    ("MDP-PROC-AMORCAGE", "Comment amorcer une pompe MDP avant démarrage ?", "remplir jusqu'à écoulement",
     ["amorç"], []),
    ("MDP-PROC-AMORCAGE", "Que vérifier en cas de code P-30 répété sur une pompe MDP ?",
     "niveau de la bâche et la crépine", ["p-30"], []),
    ("MDP-PROC-CONSIGNATION", "Comment consigner une pompe MDP avant intervention ?", "cadenasser le sectionneur q1",
     ["consign"], []),
    ("MDP-BT-2025-01", "Quel est le couple de serrage des boulons de bride de refoulement des pompes MDP ?",
     "porté à 60 n·m", ["60 n·m"], ["MDP-BT-2024-03:rappel du couple", "MDP-MAN-MAINT:boulons de bride"]),
    ("MDP-BT-2025-01", "Comment serrer les brides de refoulement d'une pompe MDP ?", "en croix en trois passes",
     ["60 n·m"], ["MDP-BT-2024-03:rappel du couple", "MDP-MAN-MAINT:boulons de bride"]),
    ("MDP-NOTE-VIBRATIONS", "Quand faut-il faire une analyse spectrale des vibrations d'une pompe MDP ?",
     "analyse spectrale", [], []),
    ("MDC-MAN-UTIL", "Comment sont refroidis les compresseurs MDC ?", "refroidis par air", [], []),
    ("MDC-MAN-UTIL", "Le voyant orange fixe d'un compresseur MDC signale-t-il une température d'huile élevée ?",
     "fixe signale le colmatage", ["filtre à air colmaté"], []),
    ("MDC-MAN-UTIL", "Où se trouve la plaque signalétique d'un compresseur MDC ?", "fixée sur le capotage", [], []),
    ("MDC-MAN-MAINT", "Quelle est la périodicité de vidange de l'huile d'un compresseur MDC ?", "vidange huile",
     ["vidange"], []),
    ("MDC-SCH-PNEU", "Comment circule l'air dans un compresseur MDC ?", "l'air aspiré traverse", [], []),
    ("MDC-SCH-ELEC", "Quel type de démarrage moteur pour les compresseurs MDC ?", "étoile-triangle", [], []),
    ("MDC-PROC-VIDANGE", "Comment vidanger l'huile d'un compresseur MDC ?", "vidanger à chaud", ["vidange"], []),
    ("MDC-PROC-VIDANGE", "Quelle quantité d'huile mettre dans un MDC-90 ?", "42 l", [], []),
    ("MDC-PROC-FILTRE-AIR", "Peut-on souffler une cartouche de filtre à air MDC pour la réutiliser ?",
     "ne jamais souffler", [], []),
    ("MDC-PROC-FILTRE-AIR", "Quand remplacer le filtre à air d'un compresseur MDC ?",
     "remplacer le filtre à air toutes", ["remplacement filtre à air", "filtre à air colmaté"], []),
    ("MDC-PROC-FILTRE-HUILE", "Comment serrer le filtre à huile d'un compresseur MDC ?", "3/4 de tour", [], []),
    ("MDC-PROC-SEPARATEUR", "Quel couple pour les vis du couvercle du réservoir séparateur MDC ?", "70 n·m", [], []),
    ("MDC-PROC-SEPARATEUR", "Quelle précaution avant d'ouvrir le réservoir séparateur d'un MDC ?", "vérifier 0 bar",
     ["décomprimer"], []),
    ("MDC-PROC-COURROIE", "Comment contrôler la tension de courroie d'un compresseur MDC ?", "flèche de 6 mm", [], []),
    ("MDC-PROC-PURGE-CONDENSATS", "Peut-on rejeter les condensats d'un compresseur MDC à l'égout ?",
     "jamais rejetés à l'égout", [], []),
    ("MDC-BT-2025-02", "Quelle cartouche de filtre à air monter sur un MDC-55 ?", "remplacée par la référence fa-55b",
     ["fa-55b"], []),
    ("MDC-BT-2025-02", "Le seuil d'alarme du filtre à air MDC-55 change-t-il avec la nouvelle cartouche ?",
     "est inchangé", ["50 mbar"], []),
    ("MDC-PROC-REVISION-SCAN", "Qui peut réaliser la révision 8 000 h du bloc vis MDC ?", "niveau 2", [], []),
    ("MDC-NOTE-SOUPAPE", "À quelle pression est tarée la soupape de sécurité d'un compresseur MDC ?",
     "tarée à 11 bar", [], []),
    ("MDC-NOTE-SOUPAPE", "Peut-on modifier le tarage de la soupape d'un compresseur MDC ?",
     "interdit de modifier le tarage", [], []),
    ("TRANS-SEC-CONSIGNATION", "Quelles sont les étapes de la consignation des énergies ?", "séparer : ouvrir",
     ["consign"], []),
    ("TRANS-SEC-CONSIGNATION", "Qui a le droit de consigner un équipement ?", "seul un intervenant habilité", [], []),
    ("TRANS-SEC-CONSIGNATION", "Un assistant logiciel peut-il autoriser une intervention ?", "aucun assistant logiciel",
     [], []),
    ("TRANS-PROC-TICKETS", "Que doit contenir un ticket de maintenance ?", "repère d'équipement", [], []),
    ("TRANS-PROC-TICKETS", "Quels niveaux de priorité pour un ticket de maintenance ?", "p1 (arrêt production)", [], []),
    ("TRANS-PROC-TICKETS", "Qui peut créer un ticket de maintenance ?", "créé uniquement par", [], []),
    ("TRANS-CONTRAT-MAINT", "Quelles pénalités de retard prévoit le contrat de maintenance ?", "2 % par jour", [], []),
    ("TRANS-NOTE-INJ", "Dans quel délai faut-il rédiger un rapport d'intervention ?", "24 h suivant la fin", [], []),
    ("TRANS-NOTE-INJ", "Combien de temps les rapports d'intervention sont-ils archivés ?", "cinq ans", [], []),
]


def is_relevant(passage, family, answer_keys, entity_keys, doc_keys=()):
    if passage["equipment_family"] not in (family, "TRANSVERSE") and family != "TRANSVERSE":
        return False
    if passage["document_id"] in doc_keys:
        return True
    text = norm(passage["text"])
    has_answer = any(norm(k) in text for k in answer_keys)
    has_entity = not entity_keys or any(norm(k) in text for k in entity_keys)
    return has_answer and has_entity


def build_queries(passages):
    doc_ids = {p["document_id"] for p in passages}
    queries = []

    def add(question, positive, answer_keys, entity_keys, forced=(), origin="template"):
        family = positive["equipment_family"]
        doc_keys = [k for k in answer_keys if k in doc_ids]
        relevant = [p["passage_id"] for p in passages
                    if p["passage_id"] == positive["passage_id"]
                    or is_relevant(p, family, answer_keys, entity_keys, doc_keys)]
        for wrong, right in (("un pompe", "une pompe"), ("une compresseur", "un compresseur"),
                             ("une équipement", "un équipement")):
            question = question.replace(wrong, right)
        queries.append({"query_id": f"q{len(queries) + 1:04d}", "question": question,
                        "equipment_family": family, "split": split_of(positive["document_id"]),
                        "positive_passage_id": positive["passage_id"], "relevant_passage_ids": relevant,
                        "answer_keys": answer_keys, "entity_keys": entity_keys, "forced_negatives": list(forced),
                        "origin": origin})

    for p in passages:
        if p["element_type"] == "table_row":
            for question, answers, entities in table_questions(p):
                add(question, p, answers, entities)
    for doc_id, question, key, also, forced in MANUAL:
        positive = next((p for p in passages if p["document_id"] == doc_id and norm(key) in norm(p["text"])), None)
        if positive is None:
            raise RuntimeError(f"Clé introuvable dans {doc_id} : {key}")
        forced_ids = []
        for ref in forced:  # « DOCUMENT:extrait » -> identifiant du passage
            fdoc, fkey = ref.split(":", 1)
            forced_ids.append(next(p["passage_id"] for p in passages
                                   if p["document_id"] == fdoc and norm(fkey) in norm(p["text"])))
        add(question, positive, [key, *also], [], forced_ids, origin="manual")
    return queries


def mine_negatives(queries, passages, rng):
    by_id = {p["passage_id"]: p for p in passages}
    triplets = []
    for q in queries:
        pos = by_id[q["positive_passage_id"]]
        relevant = set(q["relevant_passage_ids"])
        pool = [p for p in passages if p["passage_id"] not in relevant and split_of(p["document_id"]) == q["split"]]
        qt = tokens(q["question"])
        twin_group = group_of(pos["document_id"])

        def score(p):
            s = len(qt & tokens(p["text"])) / (len(qt) or 1)
            if group_of(p["document_id"]) == twin_group and p["equipment_family"] != pos["equipment_family"]:
                s += 0.3  # même document dans l'autre famille : le cas difficile visé par le cahier des charges
            if p["document_id"] == pos["document_id"]:
                s += 0.1
            return s + rng.random() * 1e-6

        ranked = sorted(pool, key=score, reverse=True)
        chosen = [by_id[f] for f in q["forced_negatives"] if f not in relevant]
        chosen += [p for p in ranked if p not in chosen][: max(0, NEGATIVES_PER_QUERY - len(chosen))]
        for neg in chosen:
            kind = ("superseded" if neg["status"] == "superseded"
                    else "cross_family" if neg["equipment_family"] not in (pos["equipment_family"], "TRANSVERSE")
                    else "same_document" if neg["document_id"] == pos["document_id"] else "same_family")
            triplets.append({"query_id": q["query_id"], "split": q["split"], "question": q["question"],
                             "positive_passage_id": pos["passage_id"], "positive": pos["text"],
                             "negative_passage_id": neg["passage_id"], "negative": neg["text"],
                             "negative_kind": kind})
    return triplets


def verify(queries, triplets, passages):
    by_id = {p["passage_id"]: p for p in passages}
    qmap = {q["query_id"]: q for q in queries}
    for t in triplets:
        q = qmap[t["query_id"]]
        assert t["negative_passage_id"] not in q["relevant_passage_ids"], t
        assert split_of(by_id[t["negative_passage_id"]]["document_id"]) == q["split"], t
        assert split_of(by_id[t["positive_passage_id"]]["document_id"]) == q["split"], t
    dup = [k for k, n in Counter(q["question"] for q in queries).items() if n > 1]
    assert not dup, f"questions dupliquées : {dup}"


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    rng = random.Random(SEED)
    manifest = {d["document_id"]: d for d in
                yaml.safe_load((CORPUS / "manifest.yaml").read_text(encoding="utf-8"))["documents"]}
    docs = content_mdp.DOCS + content_mdc.DOCS + content_trans.DOCS
    passages = build_passages(docs, manifest)
    queries = build_queries(passages)
    triplets = mine_negatives(queries, passages, rng)
    verify(queries, triplets, passages)

    OUT.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUT / "passages.jsonl", [{k: v for k, v in p.items() if not k.startswith("_")} for p in passages])
    write_jsonl(OUT / "queries.jsonl", queries)
    for split in ("train", "val", "test"):
        write_jsonl(OUT / f"triplets_{split}.jsonl", [t for t in triplets if t["split"] == split])

    sample = rng.sample(triplets, k=max(1, len(triplets) // 10))
    with open(OUT / "review_sample.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["query_id", "question", "positive", "negative", "negative_kind", "ok_positif (o/n)",
                    "ok_negatif (o/n)", "commentaire"])
        for t in sample:
            w.writerow([t["query_id"], t["question"], t["positive"], t["negative"], t["negative_kind"], "", "", ""])

    print(f"{len(passages)} passages, {len(queries)} questions, {len(triplets)} triplets")
    print("questions par split :", dict(Counter(q["split"] for q in queries)))
    print("triplets par split  :", dict(Counter(t["split"] for t in triplets)))
    print("types de négatifs   :", dict(Counter(t["negative_kind"] for t in triplets)))
    print(f"échantillon de relecture : {len(sample)} triplets -> {OUT / 'review_sample.csv'}")


if __name__ == "__main__":
    main()
