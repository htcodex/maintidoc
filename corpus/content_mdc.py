"""Contenu des documents de la famille MDC (compresseurs d'air à vis, fictifs)."""

import figures as F

GROUPS = ["grp_compresseurs", "grp_responsables"]
MODELS = ["MDC-55", "MDC-90"]
LEDS = [("V1", "vert", "EN CHARGE"), ("V2", "orange", "AVERTISS."), ("V3", "rouge", "ARRÊT DÉF.")]


def _doc(doc_id, title, doc_type, blocks, **kw):
    base = dict(id=doc_id, title=title, doc_type=doc_type, family="MDC", models=MODELS,
                groups=GROUPS, version="1.0", date="2025-04-15", confidentiality="interne",
                status="active", supersedes=None, superseded_by=None, test_flags=[], scanned=False)
    base.update(kw)
    base["blocks"] = blocks
    return base


DOCS = [
    _doc("MDC-MAN-UTIL", "Manuel d'utilisation — Compresseurs à vis MDC-55 / MDC-90", "manuel", [
        ("h1", "1. Présentation"),
        ("p", "Les compresseurs MDC-55 et MDC-90 sont des compresseurs d'air à vis lubrifiées, refroidis "
              "par air, pilotés par l'automate MDC-PLC. Le pupitre local comporte trois voyants, un "
              "afficheur de codes et un arrêt d'urgence."),
        ("table", [["Caractéristique", "MDC-55", "MDC-90"], ["Puissance moteur", "55 kW", "90 kW"],
                   ["Débit à 8 bar", "9,8 m³/min", "15,6 m³/min"], ["Pression maximale", "10 bar", "10 bar"],
                   ["Volume d'huile", "28 L", "42 L"], ["Huile", "MDC-Lube 46", "MDC-Lube 46"]]),
        ("h1", "2. Pupitre de commande"),
        ("fig", "Figure 1 — Pupitre de commande MDC (voyants V1 vert, V2 orange, V3 rouge)",
         F.control_panel("MDC-55 / MDC-90", LEDS)),
        ("h1", "3. Signification des voyants"),
        ("table", [["Voyant", "État", "Signification", "Action attendue"],
                   ["V1 vert", "Fixe", "Compresseur en charge", "Aucune"],
                   ["V1 vert", "Clignotant", "Marche à vide / veille", "Aucune"],
                   ["V2 orange", "Fixe", "Filtre à air colmaté (ΔP > 50 mbar, capteur PDS-201)",
                    "Remplacer le filtre à air ; voir MDC-PROC-FILTRE-AIR"],
                   ["V2 orange", "Clignotant", "Préalarme température d'huile ≥ 105 °C (sonde TT-202)",
                    "Contrôler niveau d'huile et refroidisseur"],
                   ["V3 rouge", "Fixe", "Arrêt sur défaut — code sur AF1", "Consulter MDC-FICHE-ALARMES"],
                   ["V3 rouge", "Clignotant", "Arrêt d'urgence enclenché", "Déverrouiller AU puis BP3"]]),
        ("warn", "Attention : sur les compresseurs MDC, le voyant V2 orange FIXE signale le colmatage du "
                 "filtre à air, et non une alarme de température. La préalarme de température d'huile est "
                 "signalée par V2 orange CLIGNOTANT. L'arrêt intervient à 115 °C (code C-21)."),
        ("h1", "4. Plaque signalétique"),
        ("p", "La plaque est fixée sur le capotage côté armoire. Elle indique le modèle, le numéro de série "
              "au format C5-xxxx ou C9-xxxx et le repère d'équipement du site (EQ-C-xxx)."),
    ]),
    _doc("MDC-MAN-MAINT", "Manuel de maintenance — Compresseurs MDC", "manuel", [
        ("h1", "1. Plan de maintenance préventive"),
        ("table", [["Opération", "Périodicité", "Procédure"],
                   ["Remplacement filtre à air", "2 000 h ou voyant V2 fixe", "MDC-PROC-FILTRE-AIR"],
                   ["Remplacement filtre à huile", "2 000 h", "MDC-PROC-FILTRE-HUILE"],
                   ["Vidange huile", "4 000 h", "MDC-PROC-VIDANGE"],
                   ["Remplacement séparateur", "4 000 h ou code C-35", "MDC-PROC-SEPARATEUR"],
                   ["Contrôle courroie", "1 000 h", "MDC-PROC-COURROIE"],
                   ["Révision bloc vis", "8 000 h", "MDC-PROC-REVISION-SCAN"]]),
        ("h1", "2. Températures d'huile"),
        ("fig", "Figure 1 — Seuils de température d'huile MDC (TT-202)",
         F.thresholds("Température huile TT-202", "°C",
                      [(60, 105, "vert", "Normal"), (105, 115, "orange", "Préalarme V2 clign."),
                       (115, 125, "rouge", "Arrêt C-21")])),
    ], test_flags=["contradiction"]),
    _doc("MDC-FICHE-ALARMES", "Fiche des codes défaut — Compresseurs MDC", "fiche_alarmes", [
        ("h1", "Codes affichés sur AF1 (voyant V3 rouge)"),
        ("table", [["Code", "Libellé", "Cause probable", "Première vérification"],
                   ["C-10", "Surintensité moteur", "Tension réseau, blocage", "Tension, rotation"],
                   ["C-21", "Température huile haute (≥ 115 °C)", "Niveau bas, refroidisseur encrassé",
                    "Niveau d'huile, ailettes refroidisseur"],
                   ["C-30", "Pression refoulement haute", "Vanne fermée en aval", "Réseau aval"],
                   ["C-35", "Séparateur colmaté (ΔP > 1 bar)", "Séparateur en fin de vie", "MDC-PROC-SEPARATEUR"],
                   ["C-50", "Sens de rotation incorrect", "Inversion de phases", "Ordre des phases"]]),
    ]),
    _doc("MDC-SCH-PNEU", "Schéma du circuit air / huile — Compresseurs MDC", "schema", [
        ("h1", "Circuit air / huile"),
        ("fig", "Figure 1 — Circuit air/huile MDC avec capteurs PDS-201 et TT-202",
         F.pneumatic_compressor("MDC")),
        ("p", "L'air aspiré traverse le filtre FA, est comprimé dans le bloc vis avec injection d'huile, puis "
              "séparé de l'huile dans le réservoir SEP. L'huile est refroidie et filtrée (FH) avant réinjection."),
    ]),
    _doc("MDC-SCH-ELEC", "Schéma électrique de l'armoire — Compresseurs MDC", "schema", [
        ("fig", "Figure 1 — Schéma électrique MDC-55 (55 kW)", F.electrical("MDC-55", 55, "MDC")),
        ("fig", "Figure 2 — Schéma électrique MDC-90 (90 kW)", F.electrical("MDC-90", 90, "MDC")),
        ("p", "Démarrage étoile-triangle. Toute intervention impose la consignation (TRANS-SEC-CONSIGNATION)."),
    ]),
    _doc("MDC-PROC-VIDANGE", "Procédure — Vidange d'huile des compresseurs MDC", "procedure", [
        ("h1", "Périodicité"),
        ("p", "La vidange complète de l'huile est réalisée toutes les 2 000 heures de fonctionnement, en même "
              "temps que le remplacement du filtre à huile."),
        ("h1", "Étapes"),
        ("list", ["Arrêter le compresseur, le consigner et attendre la décompression complète (0 bar).",
                  "Vidanger à chaud (40–60 °C) par le robinet de purge du réservoir SEP.",
                  "Remplacer le filtre à huile FH.",
                  "Remplir avec de l'huile MDC-Lube 46 : 28 L (MDC-55) ou 42 L (MDC-90).",
                  "Démarrer 5 min puis contrôler le niveau au voyant d'huile."]),
    ], test_flags=["contradiction"]),
    _doc("MDC-PROC-FILTRE-AIR", "Procédure — Remplacement du filtre à air MDC", "procedure", [
        ("h1", "Déclenchement"),
        ("p", "Remplacer le filtre à air toutes les 2 000 h ou lorsque le voyant V2 orange est allumé fixe "
              "(ΔP filtre > 50 mbar mesuré par PDS-201)."),
        ("h1", "Étapes"),
        ("list", ["Arrêter et consigner le compresseur.", "Déposer le couvercle du boîtier de filtre.",
                  "Remplacer la cartouche (FA-55B depuis le bulletin MDC-BT-2025-02).",
                  "Ne jamais souffler une cartouche pour la réutiliser.",
                  "Remettre en service puis acquitter avec BP3 : V2 doit s'éteindre."]),
    ]),
    _doc("MDC-PROC-FILTRE-HUILE", "Procédure — Remplacement du filtre à huile MDC", "procedure", [
        ("list", ["Compresseur arrêté, consigné et décomprimé.", "Dévisser le filtre FH avec une clé à sangle.",
                  "Huiler le joint du filtre neuf FH-55 et serrer à la main (3/4 de tour après contact).",
                  "Contrôler l'absence de fuite après redémarrage."]),
    ]),
    _doc("MDC-PROC-SEPARATEUR", "Procédure — Remplacement du séparateur d'huile MDC", "procedure", [
        ("p", "Le séparateur SEP-55 (MDC-55) ou SEP-90 (MDC-90) est remplacé toutes les 4 000 h ou sur code C-35."),
        ("list", ["Décomprimer totalement le réservoir.", "Déposer le couvercle du réservoir (8 vis M12, 70 N·m au remontage).",
                  "Remplacer l'élément et ses joints.", "Vérifier le tube de retour d'huile."]),
        ("warn", "Un réservoir sous pression peut provoquer des blessures graves : vérifier 0 bar au manomètre."),
    ]),
    _doc("MDC-PROC-COURROIE", "Procédure — Contrôle et tension de la courroie MDC", "procedure", [
        ("p", "Contrôler la tension toutes les 1 000 h : flèche de 6 mm sous 50 N au milieu du brin. "
              "Remplacer en cas de craquelures ou d'effilochage."),
    ]),
    _doc("MDC-PROC-PURGE-CONDENSATS", "Procédure — Purge des condensats MDC", "procedure", [
        ("p", "Vérifier quotidiennement le fonctionnement du purgeur automatique. Les condensats contiennent "
              "de l'huile : ils doivent être traités par le séparateur eau/huile du site, jamais rejetés à l'égout."),
    ]),
    _doc("MDC-GUIDE-DEPANNAGE", "Guide de dépannage — Compresseurs MDC", "guide_depannage", [
        ("table", [["Symptôme", "Causes possibles", "Vérifications"],
                   ["Voyant V2 orange fixe", "Filtre à air colmaté", "MDC-PROC-FILTRE-AIR"],
                   ["Voyant V2 orange clignotant", "Huile chaude : niveau bas, refroidisseur encrassé, local trop chaud",
                    "Niveau, refroidisseur, ventilation"],
                   ["Huile dans l'air comprimé", "Séparateur usé, niveau trop haut", "MDC-PROC-SEPARATEUR"],
                   ["Débit insuffisant", "Filtre colmaté, fuite réseau", "PDS-201, réseau"],
                   ["Soupape de sécurité qui fuit", "Pression trop haute, soupape défectueuse", "MDC-NOTE-SOUPAPE"]]),
    ]),
    _doc("MDC-PIECES", "Catalogue des pièces détachées — Compresseurs MDC", "fiche_pieces", [
        ("fig", "Figure 1 — Vue éclatée simplifiée compresseur MDC",
         F.exploded([(1, "Filtre\nair FA"), (2, "Bloc vis"), (3, "Séparat.\nSEP"), (4, "Filtre\nhuile FH"),
                     (5, "Refroid."), (6, "Courroie")])),
        ("table", [["Rep.", "Désignation", "Réf. MDC-55", "Réf. MDC-90"],
                   ["1", "Cartouche filtre à air", "FA-55B (ex FA-55)", "FA-90"],
                   ["3", "Séparateur", "SEP-55", "SEP-90"], ["4", "Filtre à huile", "FH-55", "FH-90"],
                   ["6", "Courroie", "CR-55", "CR-90"], ["—", "Huile 20 L", "MDC-Lube 46", "MDC-Lube 46"]]),
    ]),
    _doc("MDC-BT-2025-02", "Bulletin technique 2025-02 — Nouvelle cartouche de filtre à air MDC-55", "bulletin", [
        ("p", "La cartouche FA-55 est remplacée par la référence FA-55B (média renforcé). La FA-55 ne doit "
              "plus être montée. Le seuil d'alarme ΔP de 50 mbar est inchangé."),
    ], version="1.0", date="2025-05-20", models=["MDC-55"]),
    _doc("MDC-CHECKLIST-INSPECTION", "Check-list d'inspection mensuelle — Compresseurs MDC", "checklist", [
        ("table", [["#", "Point", "Critère"], ["1", "Voyants pupitre", "Seul V1 allumé"],
                   ["2", "Température huile TT-202", "< 105 °C"], ["3", "Niveau d'huile", "Entre min et max"],
                   ["4", "Purgeur de condensats", "Fonctionnel"], ["5", "Fuites d'huile", "Absentes"],
                   ["6", "Pression de service", "7,5 à 8 bar"]]),
    ]),
    _doc("MDC-PROC-REVISION-SCAN", "Procédure — Révision 8 000 h du bloc vis MDC (document scanné)", "procedure", [
        ("h1", "Révision 8 000 heures"),
        ("p", "La révision du bloc vis est réalisée toutes les 8 000 heures par un technicien habilité MDC "
              "niveau 2. Elle comprend le remplacement des roulements du bloc vis, des joints d'arbre et le "
              "contrôle du jeu des rotors."),
        ("table", [["Contrôle", "Valeur admissible"], ["Jeu axial rotor mâle", "0,02 à 0,05 mm"],
                   ["Jeu axial rotor femelle", "0,03 à 0,06 mm"], ["Couple vis de carter", "95 N·m"]]),
        ("p", "Le compte rendu de révision est joint au ticket de maintenance correspondant."),
    ], date="2023-11-02", scanned=True, test_flags=["ocr"]),
    _doc("MDC-NOTE-SOUPAPE", "Note technique — Soupape de sécurité des compresseurs MDC", "note", [
        ("p", "La soupape de sécurité SV est tarée à 11 bar. Elle est contrôlée annuellement par manœuvre "
              "manuelle, compresseur en charge. Il est interdit de modifier le tarage ou de neutraliser la soupape."),
    ]),
]
