"""Recherche en ligne de commande, avec contrôle d'accès.

Exemples :
  python -m maintidoc.retrieval.cli --user u_tech_p01 "Que signifie le voyant V2 orange fixe ?"
  python -m maintidoc.retrieval.cli --user u_tech_p01 --photo corpus/images/photo_pupitre_mdp_orange_nette.png "Que signifie ce voyant ?"
  python -m maintidoc.retrieval.cli --user u_presta_01 "contrat de maintenance"      # aucun résultat confidentiel
"""

import argparse
import sys

from PIL import Image

from maintidoc.access import AccessLog
from maintidoc.catalog import load_users
from maintidoc.config import get_settings
from maintidoc.retrieval.encoders import build_encoders
from maintidoc.retrieval.search import CHANNELS, CrossEncoderReranker, Retriever


def main(argv=None):
    ap = argparse.ArgumentParser(description="Recherche MaintiDoc filtrée par les droits de l'utilisateur")
    ap.add_argument("question")
    ap.add_argument("--user", default="u_tech_p01")
    ap.add_argument("--photo")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--rerank", action="store_true")
    ap.add_argument("--channels", default=",".join(CHANNELS))
    a = ap.parse_args(argv)
    s = get_settings()
    users = load_users(s.fixtures_dir)
    if a.user not in users:
        sys.exit("Utilisateur inconnu.")
    text_enc, image_enc = build_encoders(s)
    reranker = CrossEncoderReranker(s.reranker_model) if a.rerank else None
    journal = AccessLog(s.index_dir / "access_log.jsonl")
    r = Retriever(s, text_enc, image_enc, reranker, journal)
    journal.store = r.store
    photo = Image.open(a.photo) if a.photo else None
    res = r.search(users[a.user], a.question, photo=photo, k=a.k, channels=tuple(a.channels.split(",")),
                   rerank=a.rerank)
    print(f"Utilisateur {a.user} {users[a.user].groups} — {len(res.hits)} résultat(s) "
          f"en {res.timings['total']:.2f} s (canaux : {', '.join(res.channels)})")
    if not res.hits:
        print("Aucune source accessible ne correspond à la question.")
    for i, h in enumerate(res.hits, 1):
        e = h.element
        flag = f"  [REMPLACÉ par {e.superseded_by}]" if e.status == "superseded" else ""
        print(f"\n{i}. {e.document_id} v{e.version} — p.{e.page} — {e.element_id} ({e.element_type}){flag}")
        print(f"   rangs {h.ranks}  score RRF {h.score:.4f}"
              + (f"  rerank {h.rerank_score:.3f}" if h.rerank_score is not None else ""))
        print("   " + e.text[:240].replace("\n", " | "))
    r.close()


if __name__ == "__main__":
    main()
