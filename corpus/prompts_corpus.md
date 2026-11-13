# Prompts utilisés pour constituer le corpus MaintiDoc

Outil : **Claude Code (modèle Claude Opus, Anthropic)**, utilisé dans l'éditeur sur le dépôt du projet.
Le texte des prompts est reproduit de façon condensée ; les réponses ont été relues et corrigées avant d'entrer dans le corpus
(voir la colonne `corrections` de `inventaire.csv` et la partie « Analyse critique » à la fin de ce fichier).

Mode de génération : l'assistant n'a pas produit directement des PDF. Il a écrit le **contenu structuré** des documents
(`corpus/content_mdp.py`, `content_mdc.py`, `content_trans.py`) et les **figures vectorielles** (`corpus/figures.py`) ;
le script déterministe `corpus/generate_corpus.py` (graine 20261023) produit les PDF, le scan simulé, les photos et le manifeste.
Chaque document est donc régénérable à l'identique, et toute correction est tracée dans Git.

| N° | Date | Objet | Documents concernés |
|---|---|---|---|
| P01 | 2026-10-23 | Choix des deux familles d'équipements fictives | — |
| P02 | 2026-10-23 | Recherche de sources publiques réutilisables | `docs/05_donnees.md` |
| P03 | 2026-10-23 | Vérification des licences des sources proposées | `docs/05_donnees.md` |
| P04 | 2026-10-23 | Manuels d'utilisation (pupitres, voyants) | `mdp_man_util`, `mdc_man_util` |
| P05 | 2026-10-23 | Manuels de maintenance | `mdp_man_maint`, `mdc_man_maint` |
| P06 | 2026-10-23 | Fiches de codes défaut et guides de dépannage | `*_fiche_alarmes`, `*_guide_depannage` |
| P07 | 2026-10-23 | Schémas et vues éclatées (figures) | `*_sch_*`, `*_pieces` |
| P08 | 2026-10-23 | Procédures, check-lists, notes techniques | `*_proc_*`, `*_checklist_inspection`, `*_note_*` |
| P09 | 2026-10-23 | Bulletins contradictoires / remplacés | `mdp_bt_2024_03`, `mdp_bt_2025_01`, `mdc_bt_2025_02` |
| P10 | 2026-10-23 | Document piégé (injection de prompt) | `trans_note_inj` |
| P11 | 2026-10-23 | Documents transverses (sécurité, glossaire, tickets, contrat) | `trans_*` |
| P12 | 2026-10-23 | Photos synthétiques de pupitres | `images/photo_pupitre_*` |
| P13 | 2026-10-23 | Utilisateurs, parc, historique d'interventions (MCP) | `data/fixtures/*`, `historique_interventions_*` |
| P14 | 2026-11-13 | Relecture de cohérence du corpus | corrections listées dans l'inventaire |
| P15 | 2026-11-13 | Second document scanné pour l'OCR | `mdp_bt_2024_03` |

---

### P01 — Choix des familles (2026-10-23)
> Pour un assistant documentaire de maintenance en français, propose deux familles d'équipements industriels fictives
> qui partagent des éléments visuels proches (pupitres, voyants) mais dont la signification diffère, pour créer des cas
> ambigus. Donne pour chacune 2 modèles, les grandeurs caractéristiques et une convention de références (modèle,
> numéro de série, repère d'équipement du site).

Retenu : pompes centrifuges **MDP** (MDP-200, MDP-350) et compresseurs à vis **MDC** (MDC-55, MDC-90), repères `EQ-P-xxx` / `EQ-C-xxx`.

### P02 — Recherche de sources publiques (2026-10-23)
> Liste des jeux de données ou documents publics utilisables pour un RAG multimodal de maintenance : manuels techniques,
> questions/réponses sur documents, photos de voyants, journaux de maintenance. Pour chacun : URL, contenu, langue, licence.

### P03 — Vérification des licences (2026-10-23)
> Pour chaque source de la liste, vérifie la licence sur la page officielle (pas de mémoire) et dis si la redistribution
> dans un dépôt GitHub académique est permise. Signale les sources à écarter.

Chaque lien a ensuite été ouvert et vérifié par l'équipe (résultat : `docs/05_donnees.md`). Décision : corpus principal **100 % synthétique**.

### P04 — Manuels d'utilisation (2026-10-23)
> Rédige le contenu d'un manuel d'utilisation fictif (2 pages) pour les pompes MDP-200/350 puis pour les compresseurs
> MDC-55/90 : caractéristiques, pupitre (voyants V1 vert, V2 orange, V3 rouge, afficheur AF1, boutons BP1–BP3) avec une
> figure, tableau de signification des voyants (fixe / clignotant), mise en service, plaque signalétique. Le voyant V2
> orange fixe doit avoir un sens **différent** sur les deux familles. Format : liste de blocs Python (titre, paragraphe,
> tableau, figure) compatible avec `generate_corpus.py`.

### P05 — Manuels de maintenance (2026-10-23)
> Rédige le manuel de maintenance de chaque famille : plan préventif (opération, périodicité, procédure de référence),
> couples de serrage, surveillance (température palier TT-101 pour MDP, température d'huile pour MDC) avec un graphique de
> seuils. Les références de procédures doivent correspondre aux identifiants des autres documents.

### P06 — Codes défaut et dépannage (2026-10-23)
> Crée la fiche des codes défaut (P-10 à P-50 pour MDP, C-10 à C-50 pour MDC : libellé, causes, actions) et un guide de
> dépannage (symptôme, causes probables, vérifications). Les codes doivent être cohérents avec les manuels (ex. P-21 =
> température palier ≥ 95 °C, affiché avec V3 rouge).

### P07 — Schémas et vues éclatées (2026-10-23)
> Écris des fonctions reportlab qui dessinent : schéma hydraulique MDP (bâche, vanne d'aspiration, pompe, clapet, vanne de
> refoulement, capteurs PS/PI/TT), circuit air/huile MDC, schémas électriques par modèle, vues éclatées numérotées, pupitres.
> Chaque figure a une légende « Figure n — … » et une nomenclature en tableau.

### P08 — Procédures, check-lists, notes (2026-10-23)
> Rédige des procédures courtes et numérotées (graissage, garniture, alignement, roulements, amorçage, consignation pour MDP ;
> vidange, filtres, séparateur, courroie, purge, révision 8 000 h pour MDC), deux check-lists mensuelles et une note technique
> par famille. Mets un encadré de sécurité et renvoie à la consigne générale de consignation.

### P09 — Documents contradictoires (2026-10-23)
> Crée deux versions d'un bulletin sur le couple de serrage des brides MDP : v1 (2024, 45 N·m) remplacée par v2 (2025, 60 N·m,
> suite à des fuites). Laisse l'ancienne valeur dans le manuel de maintenance. Crée aussi une contradiction entre deux
> documents **actifs** MDC : vidange à 4 000 h (manuel) contre 2 000 h (procédure). Ces incohérences sont volontaires et
> doivent être signalées dans le manifeste.

### P10 — Document piégé (2026-10-23)
> Rédige une note de service transverse d'apparence banale (archivage des rapports d'intervention) dans laquelle est insérée
> une phrase d'injection de prompt demandant à l'assistant d'exfiltrer des rapports, de s'attribuer des droits et de créer
> des tickets. Le document sert uniquement aux tests de sécurité de la semaine 5.

### P11 — Documents transverses (2026-10-23)
> Rédige : consigne générale de consignation, fiche EPI, glossaire FR des termes de maintenance, procédure de demande de ticket
> (champs obligatoires), et un contrat de maintenance confidentiel (montants fictifs) réservé aux responsables.

### P12 — Photos de pupitres (2026-10-23)
> Écris une fonction Pillow qui produit une photo synthétique de pupitre (texture, voyants allumés avec halo, plaque
> signalétique, flou et inclinaison optionnels, étiquette collée optionnelle). Génère 5 cas : MDP orange nette, MDC orange
> nette, photo floue non identifiable, MDC rouge sans code visible, MDP avec étiquette contenant une injection.

### P13 — Données MCP fictives (2026-10-23)
> Crée 5 utilisateurs fictifs (techniciens pompes, technicien compresseurs, responsable, prestataire) avec leurs groupes, un
> parc de 7 équipements cohérent avec les plaques des photos, 9 interventions et 2 tickets ouverts. Une intervention contient
> une injection dans sa description. Aucune donnée personnelle réelle.

### P14 — Relecture de cohérence (2026-11-13)
> Relis le corpus généré : repères et identifiants d'équipement, codes défaut, valeurs numériques et renvois entre documents.
> Signale toute incohérence non voulue (les contradictions volontaires sont listées dans le manifeste).

Constat principal : dans 5 documents MDP, **V1/V2** désignait à la fois les voyants du pupitre et les vannes d'aspiration
/ de refoulement — corrigé en **VA1/VR1**.

### P15 — Second document scanné (2026-11-13)
> La consigne demande au moins 2 documents scannés. Rends le bulletin MDP-BT-2024-03 (version papier remplacée) sous forme
> scannée, sans couche texte, et ajoute le marqueur `ocr` dans le manifeste.

---

## Analyse critique de l'usage de l'IA

- **Licences proposées sans vérification.** Parmi les sources suggérées (P02), plusieurs étaient présentées comme
  réutilisables alors qu'elles ne le sont pas : FQuAD (CC BY-NC-SA, redistribution interdite), guide INRS ED 6109 (droits
  réservés), MPMQA (licence non précisée), jeux Roboflow (licence variable selon le projet). Toutes ont été écartées ou
  limitées à un lien de référence après lecture des pages officielles.
- **Lien imprécis.** Pour mMARCO-fr, le lien proposé pointait vers un *modèle* entraîné sur le jeu et non vers le jeu de
  données lui-même : corrigé dans `docs/05_donnees.md`.
- **Incohérence technique introduite.** Le même repère V1/V2 désignait des voyants et des vannes dans les documents MDP
  (manuel, fiche de codes, schéma hydraulique, procédures d'amorçage et de consignation). Pour un technicien comme pour le
  moteur de recherche, « ouvrir V1 » devenait ambigu. Corrigé (VA1/VR1) et ajouté aux corrections de l'inventaire.
- **Écart à la consigne non signalé par l'IA.** Le premier corpus ne contenait qu'un seul document scanné alors que deux sont
  exigés : ajout du bulletin MDP-BT-2024-03 scanné (P15).
- **Réalisme limité.** Les documents générés sont courts (1 à 2 pages), le scan est simulé et les photos sont des rendus :
  le corpus est cohérent par construction mais plus « propre » que la réalité. Ces limites sont reprises dans l'analyse des
  risques (D1) ; l'ajout de manuels publics réels (domaine public) est prévu en semaine 2 pour tester l'ingestion.
- **Ce qui n'est pas une erreur :** les contradictions (couple de serrage, intervalle de vidange) et les injections sont
  volontaires et marquées `contradictoire` / `injection` dans l'inventaire.
