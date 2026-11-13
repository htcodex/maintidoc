"""Contenu des documents de la famille MDP (pompes centrifuges, fictives)."""

import figures as F

GROUPS = ["grp_pompes", "grp_responsables"]
MODELS = ["MDP-200", "MDP-350"]
LEDS = [("V1", "vert", "MARCHE"), ("V2", "orange", "ALERTE"), ("V3", "rouge", "DÉFAUT")]


def _doc(doc_id, title, doc_type, blocks, **kw):
    base = dict(id=doc_id, title=title, doc_type=doc_type, family="MDP", models=MODELS,
                groups=GROUPS, version="1.0", date="2025-03-01", confidentiality="interne",
                status="active", supersedes=None, superseded_by=None, test_flags=[], scanned=False)
    base.update(kw)
    base["blocks"] = blocks
    return base


DOCS = [
    _doc("MDP-MAN-UTIL", "Manuel d'utilisation — Pompes centrifuges MDP-200 / MDP-350", "manuel", [
        ("h1", "1. Présentation"),
        ("p", "Les pompes MDP-200 et MDP-350 sont des pompes centrifuges monoétagées à axe horizontal "
              "destinées au transfert d'eau claire ou légèrement chargée. Elles sont pilotées par un "
              "automate MDP-PLC et un pupitre local comportant trois voyants, un afficheur de codes et "
              "un arrêt d'urgence."),
        ("table", [["Caractéristique", "MDP-200", "MDP-350"],
                   ["Puissance moteur", "11 kW", "22 kW"],
                   ["Débit nominal", "120 m³/h", "250 m³/h"],
                   ["Hauteur manométrique", "32 m", "40 m"],
                   ["Vitesse", "2 900 tr/min", "2 900 tr/min"],
                   ["Température max. du liquide", "60 °C", "60 °C"]]),
        ("h1", "2. Pupitre de commande"),
        ("p", "Le pupitre de commande regroupe les voyants V1 à V3, l'afficheur AF1 et les boutons BP1 à "
              "BP3. La figure 1 présente la disposition du pupitre."),
        ("fig", "Figure 1 — Pupitre de commande MDP (voyants V1 vert, V2 orange, V3 rouge)",
         F.control_panel("MDP-200 / MDP-350", LEDS)),
        ("h1", "3. Signification des voyants"),
        ("table", [["Voyant", "État", "Signification", "Action attendue"],
                   ["V1 vert", "Fixe", "Pompe en marche", "Aucune"],
                   ["V1 vert", "Clignotant", "Démarrage temporisé en cours", "Attendre 10 s"],
                   ["V2 orange", "Fixe", "Préalarme température palier ≥ 80 °C (sonde TT-101)",
                    "Contrôler graissage et vibrations ; voir procédure MDP-PROC-GRAISSAGE"],
                   ["V2 orange", "Clignotant", "Maintenance préventive due (compteur 4 000 h)",
                    "Planifier la visite préventive"],
                   ["V3 rouge", "Fixe", "Défaut avec arrêt — code sur AF1",
                    "Consulter la fiche MDP-FICHE-ALARMES"],
                   ["V3 rouge", "Clignotant", "Arrêt d'urgence enclenché", "Déverrouiller AU puis BP3"]]),
        ("warn", "Le voyant V2 orange fixe n'entraîne pas l'arrêt de la pompe. Si la température du palier "
                 "atteint 95 °C, l'automate arrête la pompe et affiche le code P-21 (voyant V3 rouge)."),
        ("h1", "4. Mise en service"),
        ("list", ["Vérifier que la vanne d'aspiration VA1 est ouverte et la vanne de refoulement VR1 fermée.",
                  "Amorcer la pompe (voir MDP-PROC-AMORCAGE) : la marche à sec est interdite.",
                  "Appuyer sur BP1 : le voyant V1 clignote puis devient fixe.",
                  "Ouvrir progressivement VR1 jusqu'au point de fonctionnement."]),
        ("h1", "5. Plaque signalétique"),
        ("p", "La plaque signalétique est rivetée sur le corps de pompe côté refoulement. Elle indique le "
              "modèle (MDP-200 ou MDP-350), le numéro de série au format P2-xxxx ou P3-xxxx et le repère "
              "d'équipement du site (EQ-P-xxx). Ces informations sont nécessaires pour toute demande "
              "d'intervention."),
    ]),
    _doc("MDP-MAN-MAINT", "Manuel de maintenance — Pompes MDP", "manuel", [
        ("h1", "1. Plan de maintenance préventive"),
        ("table", [["Opération", "Périodicité", "Procédure"],
                   ["Graissage des roulements", "2 000 h", "MDP-PROC-GRAISSAGE"],
                   ["Contrôle alignement accouplement", "4 000 h", "MDP-PROC-ALIGNEMENT"],
                   ["Remplacement garniture mécanique", "8 000 h ou fuite > 10 gouttes/min",
                    "MDP-PROC-GARNITURE"],
                   ["Remplacement roulements", "16 000 h", "MDP-PROC-DEMONTAGE-ROULEMENTS"],
                   ["Contrôle vibratoire", "Mensuel", "MDP-NOTE-VIBRATIONS"]]),
        ("h1", "2. Couples de serrage"),
        ("table", [["Assemblage", "Couple"],
                   ["Boulons de bride de refoulement (M16)", "45 N·m"],
                   ["Vis de corps de pompe (M12)", "35 N·m"],
                   ["Vis de fixation moteur (M16)", "80 N·m"]]),
        ("p", "Les couples sont donnés pour une visserie classe 8.8 légèrement huilée."),
        ("h1", "3. Surveillance de la température des paliers"),
        ("p", "La sonde PT100 TT-101 mesure la température du palier côté accouplement. Les seuils sont "
              "représentés en figure 1. Une élévation progressive indique généralement un défaut de "
              "graissage ; une élévation brutale peut indiquer un roulement endommagé ou un désalignement."),
        ("fig", "Figure 1 — Seuils de température palier MDP (TT-101)",
         F.thresholds("Température palier TT-101", "°C",
                      [(20, 80, "vert", "Normal"), (80, 95, "orange", "Préalarme V2"),
                       (95, 110, "rouge", "Arrêt P-21")])),
    ]),
    _doc("MDP-FICHE-ALARMES", "Fiche des codes défaut — Pompes MDP", "fiche_alarmes", [
        ("h1", "Codes affichés sur AF1 (voyant V3 rouge)"),
        ("table", [["Code", "Libellé", "Cause probable", "Première vérification"],
                   ["P-10", "Surintensité moteur", "Blocage roue, tension réseau", "Rotation libre de l'arbre"],
                   ["P-21", "Température palier haute (≥ 95 °C)", "Graissage insuffisant, roulement usé",
                    "Graissage, état roulements"],
                   ["P-30", "Manque d'eau / marche à sec", "Niveau bâche bas, vanne VA1 fermée",
                    "Pressostat PS-102, niveau bâche"],
                   ["P-40", "Fuite garniture détectée", "Garniture mécanique usée", "Détecteur LS-103"],
                   ["P-50", "Défaut sonde TT-101", "Câble coupé", "Continuité sonde"]]),
        ("p", "Après correction de la cause, acquitter le défaut avec BP3. Trois défauts identiques en "
              "24 h imposent une intervention et la déclaration d'un ticket."),
    ]),
    _doc("MDP-SCH-HYDR", "Schéma hydraulique d'installation — Pompes MDP", "schema", [
        ("h1", "Schéma de principe"),
        ("p", "Le schéma ci-dessous présente l'installation type d'une pompe MDP avec ses capteurs."),
        ("fig", "Figure 1 — Schéma hydraulique MDP avec capteurs PS-102, TT-101, LS-103, PI-104",
         F.hydraulic_pump("MDP")),
        ("table", [["Repère", "Fonction"], ["VA1", "Vanne d'aspiration"], ["CL1", "Clapet anti-retour"],
                   ["VR1", "Vanne de refoulement"], ["PS-102", "Pressostat manque d'eau"],
                   ["TT-101", "Sonde température palier"], ["LS-103", "Détecteur de fuite garniture"],
                   ["PI-104", "Manomètre de refoulement"]]),
    ]),
    _doc("MDP-SCH-ELEC", "Schéma électrique de l'armoire — Pompes MDP", "schema", [
        ("h1", "Circuit de puissance et de commande"),
        ("fig", "Figure 1 — Schéma électrique MDP-200 (11 kW)", F.electrical("MDP-200", 11, "MDP")),
        ("fig", "Figure 2 — Schéma électrique MDP-350 (22 kW)", F.electrical("MDP-350", 22, "MDP")),
        ("p", "Le relais thermique F1 est réglé à 21 A pour la MDP-200 et à 41 A pour la MDP-350. "
              "Toute intervention dans l'armoire impose la consignation électrique (TRANS-SEC-CONSIGNATION)."),
    ]),
    _doc("MDP-PROC-GRAISSAGE", "Procédure — Graissage des roulements MDP", "procedure", [
        ("h1", "Objet"),
        ("p", "Graissage périodique des roulements toutes les 2 000 heures ou en cas de préalarme de "
              "température palier (voyant V2 orange fixe)."),
        ("h1", "Matériel"),
        ("list", ["Graisse au lithium NLGI 2", "Pompe à graisse manuelle", "Chiffons non pelucheux"]),
        ("h1", "Mode opératoire"),
        ("list", ["Nettoyer les graisseurs avant injection.",
                  "Injecter 15 g côté accouplement et 10 g côté opposé, pompe en marche si l'accès est protégé.",
                  "Ne pas dépasser la quantité : un excès de graisse provoque aussi un échauffement.",
                  "Surveiller TT-101 pendant 2 h : la température doit redescendre sous 80 °C.",
                  "Si la préalarme persiste après 2 h, déclarer un ticket et planifier le contrôle des roulements."]),
    ]),
    _doc("MDP-PROC-GARNITURE", "Procédure — Remplacement de la garniture mécanique MDP", "procedure", [
        ("h1", "Conditions préalables"),
        ("list", ["Pompe consignée électriquement et hydrauliquement (MDP-PROC-CONSIGNATION).",
                  "Corps de pompe vidangé.", "Garniture de rechange GM-200 (MDP-200) ou GM-350 (MDP-350)."]),
        ("h1", "Étapes"),
        ("list", ["Déposer l'accouplement et le moteur.", "Déposer le couvercle de corps (vis M12).",
                  "Extraire la roue puis la garniture usagée.",
                  "Nettoyer les portées ; ne jamais toucher les faces de friction de la garniture neuve.",
                  "Remonter dans l'ordre inverse ; vis de corps à 35 N·m.",
                  "Contrôler l'alignement (MDP-PROC-ALIGNEMENT) avant remise en service."]),
        ("warn", "Une fuite de quelques gouttes pendant les 30 premières minutes est normale (rodage)."),
    ]),
    _doc("MDP-PROC-ALIGNEMENT", "Procédure — Contrôle de l'alignement de l'accouplement MDP", "procedure", [
        ("h1", "Tolérances"),
        ("table", [["Écart", "Tolérance"], ["Désalignement radial", "≤ 0,05 mm"],
                   ["Désalignement angulaire", "≤ 0,05 mm / 100 mm"], ["Jeu axial accouplement", "3 ± 0,5 mm"]]),
        ("h1", "Méthode"),
        ("p", "Utiliser un aligneur laser ou deux comparateurs. Corriger d'abord le plan vertical par cales "
              "sous le moteur, puis le plan horizontal. Resserrer les vis moteur à 80 N·m et refaire une mesure."),
    ]),
    _doc("MDP-PROC-DEMONTAGE-ROULEMENTS", "Procédure — Remplacement des roulements MDP", "procedure", [
        ("h1", "Références"),
        ("table", [["Position", "MDP-200", "MDP-350"], ["Côté accouplement", "RLT-6309", "RLT-6311"],
                   ["Côté opposé", "RLT-6308", "RLT-6310"]]),
        ("h1", "Étapes"),
        ("list", ["Consigner la pompe et déposer l'ensemble palier.",
                  "Extraire les roulements à l'arrache-moyeu ; ne pas frapper sur l'arbre.",
                  "Chauffer les roulements neufs à 110 °C maximum par induction.",
                  "Regarnir en graisse (30 % du volume libre).",
                  "Après remontage, rodage 2 h avec surveillance de TT-101."]),
    ]),
    _doc("MDP-PROC-AMORCAGE", "Procédure — Amorçage et prévention de la marche à sec MDP", "procedure", [
        ("h1", "Principe"),
        ("p", "La pompe MDP n'est pas auto-amorçante. Le corps et la conduite d'aspiration doivent être "
              "remplis avant tout démarrage. Le pressostat PS-102 arrête la pompe (code P-30) en cas de manque d'eau."),
        ("h1", "Étapes"),
        ("list", ["Ouvrir VA1 et le purgeur du corps.", "Remplir jusqu'à écoulement continu au purgeur.",
                  "Fermer le purgeur puis démarrer.", "En cas de P-30 répété, vérifier le niveau de la bâche et la crépine."]),
    ]),
    _doc("MDP-PROC-CONSIGNATION", "Procédure — Consignation d'une pompe MDP", "procedure", [
        ("h1", "Consignation"),
        ("list", ["Arrêter la pompe par BP2.", "Ouvrir et cadenasser le sectionneur Q1.",
                  "Vérifier l'absence de tension (VAT).", "Fermer et cadenasser VA1 et VR1.",
                  "Vidanger le corps de pompe et vérifier l'absence de pression sur PI-104."]),
        ("p", "Cette procédure complète la consigne générale TRANS-SEC-CONSIGNATION, qui prévaut en cas de doute."),
    ]),
    _doc("MDP-GUIDE-DEPANNAGE", "Guide de dépannage — Pompes MDP", "guide_depannage", [
        ("h1", "Symptômes et causes"),
        ("table", [["Symptôme", "Causes possibles", "Vérifications"],
                   ["Voyant V2 orange fixe", "Graissage insuffisant ou excessif, roulement usé, désalignement",
                    "Graissage, vibrations, alignement"],
                   ["Débit insuffisant", "Vanne partiellement fermée, roue usée, prise d'air",
                    "PI-104, état de la roue"],
                   ["Bruit de cavitation", "NPSH insuffisant, crépine colmatée", "Niveau bâche, crépine"],
                   ["Vibrations élevées", "Désalignement, balourd, roulement", "MDP-NOTE-VIBRATIONS"],
                   ["Fuite à l'arbre", "Garniture usée", "MDP-PROC-GARNITURE"]]),
        ("p", "Ce guide oriente les vérifications ; il ne remplace pas l'analyse d'un technicien habilité."),
    ]),
    _doc("MDP-PIECES", "Catalogue des pièces détachées — Pompes MDP", "fiche_pieces", [
        ("h1", "Vue éclatée"),
        ("fig", "Figure 1 — Vue éclatée simplifiée pompe MDP",
         F.exploded([(1, "Corps"), (2, "Roue"), (3, "Garniture\nGM"), (4, "Palier"), (5, "Roulements"),
                     (6, "Accoupl.")])),
        ("table", [["Rep.", "Désignation", "Réf. MDP-200", "Réf. MDP-350"],
                   ["2", "Roue", "RO-200", "RO-350"], ["3", "Garniture mécanique", "GM-200", "GM-350"],
                   ["5", "Roulement côté accouplement", "RLT-6309", "RLT-6311"],
                   ["—", "Joint de corps", "JT-200", "JT-350"], ["—", "Sonde PT100", "TT-101", "TT-101"]]),
    ]),
    _doc("MDP-BT-2024-03", "Bulletin technique 2024-03 — Couple de serrage des brides MDP", "bulletin", [
        ("h1", "Objet"),
        ("p", "Rappel du couple de serrage des boulons de bride de refoulement M16 : 45 N·m."),
        ("p", "Ce bulletin s'applique aux pompes MDP-200 et MDP-350 de toutes séries."),
    ], version="1.0", date="2024-06-12", status="superseded", superseded_by="MDP-BT-2025-01",
        scanned=True, test_flags=["superseded", "ocr"]),
    _doc("MDP-BT-2025-01", "Bulletin technique 2025-01 — Nouveau couple de serrage des brides MDP", "bulletin", [
        ("h1", "Objet"),
        ("p", "Suite à des fuites constatées sur les joints de bride, le couple de serrage des boulons de "
              "bride de refoulement M16 est porté à 60 N·m. Ce bulletin remplace le bulletin 2024-03 et "
              "prévaut sur la valeur indiquée dans le manuel de maintenance MDP-MAN-MAINT (45 N·m)."),
        ("p", "Serrer en croix en trois passes : 20 N·m, 40 N·m puis 60 N·m."),
    ], version="2.0", date="2025-02-03", supersedes="MDP-BT-2024-03", test_flags=["superseded"]),
    _doc("MDP-CHECKLIST-INSPECTION", "Check-list d'inspection mensuelle — Pompes MDP", "checklist", [
        ("h1", "Points de contrôle"),
        ("table", [["#", "Point", "Critère"], ["1", "Voyants pupitre", "Seul V1 allumé en marche"],
                   ["2", "Température palier TT-101", "< 80 °C"], ["3", "Fuite garniture", "< 10 gouttes/min"],
                   ["4", "Pression refoulement PI-104", "Conforme au point de fonctionnement"],
                   ["5", "Vibrations", "< 4,5 mm/s"], ["6", "Bruit anormal", "Absent"]]),
        ("p", "Tout écart doit être reporté dans un ticket de maintenance."),
    ]),
    _doc("MDP-NOTE-VIBRATIONS", "Note technique — Seuils vibratoires des pompes MDP", "note", [
        ("h1", "Seuils"),
        ("fig", "Figure 1 — Seuils de vitesse vibratoire efficace MDP",
         F.thresholds("Vitesse vibratoire efficace", "mm/s",
                      [(0, 2.8, "vert", "Bon"), (2.8, 4.5, "orange", "Acceptable"),
                       (4.5, 7.1, "rouge", "Intervention")])),
        ("p", "Mesurer sur les paliers dans les trois directions. Une augmentation de plus de 25 % entre "
              "deux mesures mensuelles justifie une analyse spectrale."),
    ]),
]
