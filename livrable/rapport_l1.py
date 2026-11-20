"""Rapport PDF du livrable 1 MaintiDoc (parties 2.1 à 2.6 de la consigne). Appelé par build_livrable1.py."""

from collections import Counter
from pathlib import Path

from reportlab import rl_config
from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

rl_config.invariant = 1
for name, f in [("H", "arial"), ("H-B", "arialbd"), ("H-I", "ariali")]:
    if name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(name, f"C:/Windows/Fonts/{f}.ttf"))
from reportlab.lib.fonts import addMapping  # noqa: E402
pdfmetrics.registerFontFamily("H", normal="H", bold="H-B", italic="H-I", boldItalic="H-B")
for _b, _i, _n in [(0, 0, "H"), (1, 0, "H-B"), (0, 1, "H-I"), (1, 1, "H-B")]:
    addMapping("H", _b, _i, _n)

NAVY = colors.HexColor("#1f3a5f")
BLUE = colors.HexColor("#dbe7f5")
GREY = colors.HexColor("#9aa7b5")
RED = colors.HexColor("#c62828")
AMBER = colors.HexColor("#fff3d6")

S = {
    "title": ParagraphStyle("title", fontName="H-B", fontSize=24, leading=30, textColor=NAVY, alignment=TA_CENTER),
    "sub": ParagraphStyle("sub", fontName="H", fontSize=13, leading=18, alignment=TA_CENTER),
    "h1": ParagraphStyle("h1", fontName="H-B", fontSize=15, leading=19, textColor=NAVY, spaceBefore=6, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="H-B", fontSize=11.5, leading=15, textColor=NAVY, spaceBefore=8, spaceAfter=3),
    "p": ParagraphStyle("p", fontName="H", fontSize=9.6, leading=13.2, spaceAfter=4),
    "cell": ParagraphStyle("cell", fontName="H", fontSize=8, leading=10),
    "cellb": ParagraphStyle("cellb", fontName="H-B", fontSize=8, leading=10),
    "cap": ParagraphStyle("cap", fontName="H-I", fontSize=8.3, leading=11, alignment=TA_CENTER,
                          textColor=colors.HexColor("#333333"), spaceAfter=6),
    "note": ParagraphStyle("note", fontName="H", fontSize=8.8, leading=12, backColor=AMBER, borderPadding=5,
                           borderColor=colors.HexColor("#f0a000"), borderWidth=0.6, spaceBefore=4, spaceAfter=8),
}


def P(t, s="p"):
    return Paragraph(t, S[s])


def bullets(items, s="p"):
    return ListFlowable([ListItem(P(i, s), leftIndent=12) for i in items], bulletType="bullet", start="•",
                        leftIndent=12, bulletFontName="H")


def table(rows, widths, head=True, zebra=True, font=8):
    st = S["cell"] if font == 8 else ParagraphStyle("c2", parent=S["cell"], fontSize=font, leading=font + 2)
    data = []
    for i, r in enumerate(rows):
        data.append([c if not isinstance(c, str) else Paragraph(c, S["cellb"] if (head and i == 0) else st)
                     for c in r])
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if head else 0, hAlign="LEFT")
    style = [("GRID", (0, 0), (-1, -1), 0.4, GREY), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    if head:
        style.append(("BACKGROUND", (0, 0), (-1, 0), BLUE))
    if zebra:
        for i in range(2 if head else 1, len(rows), 2):
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f6f8fb")))
    t.setStyle(TableStyle(style))
    return t


# ------------------------------------------------------------------ primitives de dessin

def box(d, x, y, w, h, text, fill=colors.white, bold_first=True, size=7.2, stroke=NAVY):
    d.add(Rect(x, y, w, h, rx=4, ry=4, fillColor=fill, strokeColor=stroke, strokeWidth=0.9))
    lines = text.split("\n")
    lh = size + 2
    y0 = y + h / 2 + (len(lines) - 1) * lh / 2 - size / 3
    for i, ln in enumerate(lines):
        d.add(String(x + w / 2, y0 - i * lh, ln, fontName="H-B" if (bold_first and i == 0) else "H",
                     fontSize=size, textAnchor="middle"))


def diamond(d, cx, cy, w, h, text, size=7):
    d.add(Polygon([cx - w / 2, cy, cx, cy + h / 2, cx + w / 2, cy, cx, cy - h / 2],
                  fillColor=colors.HexColor("#ede7f6"), strokeColor=NAVY, strokeWidth=0.9))
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        d.add(String(cx, cy + (len(lines) - 1) * 4.5 - i * 9 - 2.5, ln, fontName="H", fontSize=size,
                     textAnchor="middle"))


def _head(d, x1, y1, x2, y2, color):
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    L, W = 6, 3
    bx, by = x2 - L * math.cos(a), y2 - L * math.sin(a)
    d.add(Polygon([x2, y2, bx + W * math.sin(a), by - W * math.cos(a), bx - W * math.sin(a), by + W * math.cos(a)],
                  fillColor=color, strokeColor=color, strokeWidth=0.5))


def label(d, x, y, text, size=6.3, anchor="middle", color=colors.HexColor("#333333")):
    w = pdfmetrics.stringWidth(text, "H-I", size)
    x0 = {"middle": x - w / 2, "start": x, "end": x - w}[anchor]
    d.add(Rect(x0 - 1.5, y - 2, w + 3, size + 2.5, fillColor=colors.white, strokeColor=None))
    d.add(String(x, y, text, fontName="H-I", fontSize=size, textAnchor=anchor, fillColor=color))


def arrow(d, pts, text=None, at=None, color=colors.HexColor("#37474f"), both=False, anchor="middle", dash=None):
    d.add(PolyLine(pts, strokeColor=color, strokeWidth=0.9, strokeDashArray=dash))
    _head(d, pts[-4], pts[-3], pts[-2], pts[-1], color)
    if both:
        _head(d, pts[2], pts[3], pts[0], pts[1], color)
    if text:
        lx, ly = at if at else ((pts[0] + pts[-2]) / 2, (pts[1] + pts[-1]) / 2 + 2)
        label(d, lx, ly, text, anchor=anchor)


def cp(d, x, y, n):
    d.add(Circle(x, y, 8, fillColor=RED, strokeColor=colors.white, strokeWidth=1))
    d.add(String(x, y - 3, f"CP{n}", fontName="H-B", fontSize=5.6, textAnchor="middle", fillColor=colors.white))


# ------------------------------------------------------------------ diagrammes

def diagram_architecture():
    W, H = 482, 405
    d = Drawing(W, H)
    c0, c1, c2, bw, bh = 4, 171, 338, 140, 56
    r0, r1, r2, r3 = 335, 228, 118, 12
    hum = colors.HexColor("#fde7e7")
    box(d, c0, r0, bw, bh, "Interface web (Streamlit)\nquestion + photo\naffichage réponse et sources", fill=BLUE)
    box(d, c1, r0, bw, bh, "API (FastAPI)\nauthentification, session\ncontrôle des droits")
    box(d, c2, r0, bw, bh, "Validation humaine\nécran d'approbation\ndu brouillon de ticket", fill=hum)
    box(d, c0, r1, bw, bh, "Modèle vision-langage\n(Qwen2.5-VL-7B, à préciser)\nanalyse photo, rédaction JSON")
    box(d, c1, r1, bw, bh, "Orchestration (LangGraph)\nenchaîne les étapes\nbudgets 3 MCP · 6 modèle · 60 s",
        fill=colors.HexColor("#e8f5e9"))
    box(d, c2, r1, bw, bh, "Vérification des citations\nla source existe et\nsoutient l'affirmation")
    box(d, c0, r2, bw, bh, "Ingestion (hors ligne)\nPyMuPDF, OCR, découpage\nembeddings, métadonnées",
        fill=colors.HexColor("#f5f5f5"))
    box(d, c1, r2, bw, bh, "Recherche documentaire\nhybride texte + image (RRF)\nreranker, filtre d'accès")
    box(d, c2, r2, bw, bh, "Outil MCP maintenance\nget_equipment_history\nget_open_tickets · create_ticket")
    box(d, c0, r3, c1 + bw - c0, bh, "Stockage\nQdrant (vecteurs + métadonnées de filtrage) · PostgreSQL (métadonnées,\n"
        "journaux, approbations) · MinIO (PDF, pages, figures, photos)", fill=colors.HexColor("#fff8e1"))
    box(d, c2, r3, bw, bh, "Service de maintenance\nde démonstration (fictif)\nhistorique, tickets", fill=colors.HexColor("#fff8e1"))
    # Interface <-> API
    arrow(d, [c0 + bw, r0 + 38, c1, r0 + 38], "question, photo", at=((c0 + bw + c1) / 2, r0 + 42))
    arrow(d, [c1, r0 + 16, c0 + bw, r0 + 16], "réponse, sources", at=((c0 + bw + c1) / 2, r0 + 4))
    # API <-> validation humaine
    arrow(d, [c1 + bw, r0 + 38, c2, r0 + 38], "brouillon", at=((c1 + bw + c2) / 2, r0 + 42))
    arrow(d, [c2, r0 + 16, c1 + bw, r0 + 16], "approbation", at=((c1 + bw + c2) / 2, r0 + 4))
    # API <-> orchestration
    arrow(d, [c1 + 45, r0, c1 + 45, r1 + bh], "requête + groupes", at=(c1 + 44, r1 + bh + 22), anchor="end")
    arrow(d, [c1 + 95, r1 + bh, c1 + 95, r0], "résultat", at=(c1 + 98, r1 + bh + 22), anchor="start")
    # orchestration <-> VLM
    arrow(d, [c1, r1 + 38, c0 + bw, r1 + 38], "photo, passages", at=((c0 + bw + c1) / 2, r1 + 42))
    arrow(d, [c0 + bw, r1 + 16, c1, r1 + 16], "observations, JSON", at=((c0 + bw + c1) / 2, r1 + 4))
    # orchestration <-> vérification
    arrow(d, [c1 + bw, r1 + 38, c2, r1 + 38], "réponse + citations", at=((c1 + bw + c2) / 2, r1 + 42))
    arrow(d, [c2, r1 + 16, c1 + bw, r1 + 16], "validée / rejetée", at=((c1 + bw + c2) / 2, r1 + 4))
    # orchestration <-> recherche
    arrow(d, [c1 + 45, r1, c1 + 45, r2 + bh], "requête filtrée", at=(c1 + 42, r2 + bh + 20), anchor="end")
    arrow(d, [c1 + 95, r2 + bh, c1 + 95, r1], "passages, figures", at=(c1 + 98, r2 + bh + 20), anchor="start")
    # orchestration -> MCP (lecture)
    arrow(d, [c1 + bw, r1 + 4, c2 + 30, r2 + bh], "historique", at=(c2 + 2, r2 + bh + 14), anchor="start")
    # validation humaine -> MCP (création) : par la marge droite
    arrow(d, [c2 + bw, r0 + 28, W - 2, r0 + 28, W - 2, r2 + 28, c2 + bw, r2 + 28], color=RED)
    label(d, W - 4, r1 - 18, "jeton signé", anchor="end", color=RED)
    # ingestion / recherche -> stockage ; MCP -> service
    arrow(d, [c0 + 70, r2, c0 + 70, r3 + bh], "index, fichiers", at=(c0 + 73, r3 + bh + 22), anchor="start")
    arrow(d, [c1 + 70, r2, c1 + 70, r3 + bh], both=True)
    label(d, c1 + 73, r3 + bh + 22, "vecteurs, méta.", anchor="start")
    arrow(d, [c2 + 70, r2, c2 + 70, r3 + bh], both=True)
    label(d, c2 + 73, r3 + bh + 22, "lecture / écriture", anchor="start")
    # points de contrôle
    cp(d, c1 + bw - 4, r0 + bh - 2, 1)
    cp(d, c1 + bw - 4, r2 + bh - 2, 2)
    cp(d, c2 + bw - 4, r1 + bh - 2, 3)
    cp(d, c2 + bw - 4, r0 + bh - 2, 4)
    cp(d, c2 + bw - 4, r2 + bh - 2, 5)
    return d


def diagram_ingestion():
    W, H = 482, 165
    d = Drawing(W, H)
    y1, y2, h = 100, 22, 42
    box(d, 2, 61, 64, h, "Corpus\nPDF + photos\n+ inventaire", fill=BLUE)
    diamond(d, 102, 82, 58, 46, "PDF\nscanné ?")
    box(d, 150, y1, 72, h, "Extraction\ntexte, tableaux,\nfigures (PyMuPDF)")
    box(d, 150, y2, 72, h, "OCR local\n(Tesseract fra,\nà préciser)")
    box(d, 240, y1, 72, h, "Découpage\nparagraphes, lignes\nde tableau, figures")
    box(d, 330, y1, 62, h, "Embeddings\ntexte (bge-m3)\nimage (à préciser)")
    box(d, 408, y1, 72, h, "Index vectoriel\nQdrant\n(payload = méta.)", fill=colors.HexColor("#fff8e1"))
    box(d, 240, y2, 72, h, "Métadonnées\ndoc, version, page,\nélément, groupes")
    box(d, 330, y2, 62, h, "PostgreSQL\nmétadonnées\net journaux", fill=colors.HexColor("#fff8e1"))
    box(d, 408, y2, 72, h, "MinIO\noriginaux, pages,\nfigures", fill=colors.HexColor("#fff8e1"))
    arrow(d, [66, 82, 73, 82])
    arrow(d, [131, 82, 140, 82, 140, y1 + 21, 150, y1 + 21], "non", at=(140, y1 + 26))
    arrow(d, [102, 59, 102, y2 + 21, 150, y2 + 21], "oui", at=(118, y2 + 25))
    arrow(d, [186, y2 + h, 186, y1], "texte + position", at=(190, 76), anchor="start")
    arrow(d, [222, y1 + 21, 240, y1 + 21])
    arrow(d, [312, y1 + 21, 330, y1 + 21])
    arrow(d, [392, y1 + 21, 408, y1 + 21])
    arrow(d, [276, y1, 276, y2 + h])
    arrow(d, [312, y2 + 21, 330, y2 + 21])
    arrow(d, [34, 61, 34, 8, 444, 8, 444, y2], "originaux conservés (empreinte SHA-256)", at=(240, 11))
    return d


def diagram_ticket():
    W, H = 482, 175
    d = Drawing(W, H)
    y, h = 105, 50
    box(d, 2, y, 74, h, "Brouillon\npréparé par l'agent\n(équipement, titre,\nsymptôme, sources)", size=6.8)
    box(d, 88, y, 74, h, "Affichage\ndu contenu exact\nà l'utilisateur", size=6.8)
    diamond(d, 205, y + h / 2, 66, 54, "Approbation\nhumaine ?")
    box(d, 252, y, 80, h, "Jeton signé (HMAC)\nutilisateur + hash\ndu contenu + clé\nd'idempotence", size=6.8)
    box(d, 345, y, 52, h, "Appel MCP\ncreate_ticket", size=6.8)
    box(d, 408, y - 5, 72, h + 10, "Serveur MCP\nvérifie : droit sur\nl'équipement, jeton,\nhash, clé déjà vue ?",
        size=6.8, fill=colors.HexColor("#fde7e7"))
    box(d, 168, 8, 74, 38, "Aucun ticket créé\n(refus ou modification\n→ nouveau brouillon)", size=6.5)
    box(d, 255, 8, 70, 38, "Refus journalisé\n(jeton invalide,\ndroit absent)", size=6.5)
    box(d, 333, 8, 72, 38, "Clé déjà connue :\nticket existant\nrenvoyé\n(pas de doublon)", size=6.5)
    box(d, 413, 8, 67, 38, "Ticket créé\nn° renvoyé\net journalisé", size=6.5, fill=colors.HexColor("#e8f5e9"))
    arrow(d, [76, y + 25, 88, y + 25])
    arrow(d, [162, y + 25, 172, y + 25])
    arrow(d, [238, y + 25, 252, y + 25], "oui", at=(244, y + 30))
    arrow(d, [205, y - 2, 205, 46], "non", at=(212, 70), anchor="start")
    arrow(d, [332, y + 25, 345, y + 25])
    arrow(d, [397, y + 25, 408, y + 25])
    d.add(Line(444, y - 5, 444, 70, strokeColor=colors.HexColor("#37474f"), strokeWidth=0.9))
    d.add(Line(290, 70, 446, 70, strokeColor=colors.HexColor("#37474f"), strokeWidth=0.9))
    for x in (290, 369, 446):
        arrow(d, [x, 70, x, 46])
    cp(d, 205, y + h / 2 + 33, 4)
    cp(d, 474, y + h, 5)
    return d


# ------------------------------------------------------------------ contenu

TOC_TITLES = ["1. Cadrage du projet", "2. Constitution du corpus documentaire", "3. Architecture cible",
              "4. Flux de données et contrôle d'accès", "5. Analyse des risques",
              "6. Planning et organisation de l'équipe", "Annexe A — Inventaire du corpus (résumé)"]
TOC = {}


def build(cfg, rows, out_path, _second_pass=False):
    team = cfg["nom_equipe"]
    membres = cfg["membres"]
    names = [m["prenom"] for m in membres]

    def who(i):
        return names[min(i, len(names) - 1)]

    def whos(*idx):
        return ", ".join(dict.fromkeys(who(i) for i in idx))

    noms = ", ".join(f"{m['prenom']} {m['nom']}" for m in membres)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("H", 7.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(2 * cm, 1.1 * cm, f"L1 MaintiDoc — {noms} — cadrage, corpus et architecture")
        canvas.drawRightString(19 * cm, 1.1 * cm, f"Page {doc.page}")
        canvas.restoreState()

    docs = [r for r in rows if r["type_document"] != "photo"]
    photos = [r for r in rows if r["type_document"] == "photo"]
    fam = Counter(r["famille_equipement"] for r in rows)
    types = Counter(r["type_document"] for r in rows)
    pages = sum(int(r["nb_pages"]) for r in rows)
    scans = [r["document_id"] for r in rows if r["format"] == "pdf_scanne"]
    visual = [r for r in rows if r["elements_visuels"] != "aucun"]
    figs = sum(r["elements_visuels"].count("fig ") for r in rows)
    usage = Counter(r["usage_test"] for r in rows)
    corrected = [r for r in rows if r["corrections"] != "aucune"]

    st = []
    # ---------------- page de garde
    st += [Spacer(1, 3.2 * cm), P("MaintiDoc", "title"), Spacer(1, 0.3 * cm),
           P("Assistant documentaire multimodal et agentique pour la maintenance", "sub"), Spacer(1, 0.9 * cm),
           P("<b>Livrable 1 — Cadrage, corpus et architecture</b>", "sub"),
           P("Module IA générative multimodale — EMSI 2026 — Semaine 1", "sub"), Spacer(1, 1.6 * cm)]
    st.append(table([["Équipe", team]] + [[f"Membre {i + 1}", f"{m['prenom']} {m['nom']}"]
                                         for i, m in enumerate(membres)]
                    + [["Enseignante", "Pr. Mariam CHERRABI"], ["Date de rendu", cfg["date_rendu"]],
                       ["Dépôt", cfg["github_url"]]], [4, 13], head=False, zebra=False, font=9))
    st += [Spacer(1, 1.2 * cm), P("<b>Sommaire</b>", "h2")]
    st.append(table([[t, str(TOC.get(t, "-"))] for t in TOC_TITLES], [14.5, 2.5], head=False, font=9))
    st += [Spacer(1, 0.8 * cm), P(
        "Toutes les données du projet (équipements, documents, utilisateurs, interventions, tickets) sont <b>fictives</b>. "
        "MaintiDoc est une aide documentaire : il ne pilote aucun équipement, ne garantit aucun diagnostic et ne "
        "remplace ni les procédures de sécurité ni un technicien habilité.", "note"), PageBreak()]

    # ---------------- 1. cadrage
    st += [P("1. Cadrage du projet", "h1"), P("1.1 Contexte et utilisateurs", "h2"), P(
        "Un site industriel fictif exploite deux familles d'équipements : des <b>pompes centrifuges MDP</b> (MDP-200 de "
        "11 kW, MDP-350 de 22 kW) et des <b>compresseurs d'air à vis MDC</b> (MDC-55, MDC-90). La documentation est "
        "dispersée entre manuels, procédures, schémas, bulletins et fiches de codes défaut ; l'historique des "
        "interventions est tenu dans un service de maintenance séparé. Face à un voyant allumé, un technicien perd du "
        "temps à retrouver la bonne page, la bonne version du document et les interventions passées. Les deux pupitres "
        "se ressemblent (voyants vert / orange / rouge) mais le voyant orange n'y a <b>pas le même sens</b> : c'est le "
        "cœur de la difficulté que l'assistant doit gérer.")]
    st.append(table([
        ["Profil", "Besoins", "Droits"],
        ["Technicien pompes (u_tech_p01, u_tech_p02)", "Comprendre un voyant ou un code défaut sur le terrain, photo à "
         "l'appui ; retrouver la procédure ; connaître les dernières interventions ; déclarer un ticket", "Documents MDP "
         "+ transverses ; historique et tickets MDP"],
        ["Technicien compresseurs (u_tech_c01)", "Idem pour les compresseurs MDC", "Documents MDC + transverses ; "
         "historique et tickets MDC"],
        ["Responsable maintenance (u_resp_01)", "Vue d'ensemble, contradictions entre documents, validation des "
         "tickets, contrat de maintenance", "Tous les documents, y compris confidentiels ; toutes les familles"],
        ["Prestataire externe (u_presta_01)", "Consignes de sécurité avant intervention", "Documents de sécurité et "
         "glossaire uniquement ; aucun outil MCP"],
    ], [4.3, 8.2, 4.5]))
    st += [P("1.2 Cas d'usage", "h2"), table([
        ["#", "Cas d'usage", "Comportement attendu"],
        ["CU1", "Un technicien pompes photographie le pupitre de EQ-P-002 (V2 orange fixe) : « Que signifie ce voyant ? "
         "Consulte les dernières interventions et prépare un ticket si nécessaire. »", "Préalarme température palier "
         "citée (manuel MDP p.1, tableau des voyants), historique de EQ-P-002 (2 préalarmes récentes), brouillon de ticket "
         "en attente d'approbation"],
        ["CU2", "Photo floue, plaque illisible, voyant orange visible", "Demande de clarification (photographier la plaque "
         "signalétique) au lieu de deviner la famille"],
        ["CU3", "« Quel couple de serrage pour la bride de refoulement MDP ? »", "60 N·m (bulletin 2025-01 actif) ; "
         "signale que le manuel et le bulletin 2024-03 remplacé indiquent 45 N·m"],
        ["CU4", "« À quelle fréquence vidanger le compresseur MDC ? »", "Expose la contradiction 4 000 h (manuel) / "
         "2 000 h (procédure) sans trancher arbitrairement ; propose d'en référer au responsable"],
        ["CU5", "Le prestataire demande le contrat de maintenance, ou un technicien compresseurs l'historique d'une pompe",
         "Refus sans divulguer l'existence ni le contenu du document"],
    ], [1.0, 8.0, 8.0])]
    st += [P("1.3 Objectifs vérifiables en semaine 6", "h2"), P(
        "Chaque objectif est formulé pour être testé par un scénario du jeu d'évaluation. Les indicateurs chiffrés "
        "(seuils, taux) seront fixés en semaine 5."), bullets([
        "<b>O1</b> — Répondre à une question sur un voyant en citant le <b>document, la page et, si elle existe, la "
        "figure</b> ; chaque citation renvoie à un élément réellement récupéré.",
        "<b>O2</b> — À partir d'une photo de pupitre, distinguer pompe et compresseur grâce à la plaque signalétique, ou "
        "<b>demander une clarification</b> si elle est illisible.",
        "<b>O3</b> — <b>Refuser l'accès</b> à un document d'un autre groupe : aucun passage d'un document non autorisé "
        "dans le contexte du modèle ni dans la réponse.",
        "<b>O4</b> — <b>Ne créer aucun ticket sans approbation</b> explicite de l'utilisateur, et créer exactement le "
        "contenu approuvé, une seule fois (idempotence).",
        "<b>O5</b> — Consulter l'historique d'un équipement via l'outil MCP et l'intégrer à la réponse.",
        "<b>O6</b> — Signaler une contradiction entre documents actifs et préférer la version active d'un document remplacé.",
        "<b>O7</b> — Ignorer une instruction contenue dans un document, une photo (OCR) ou une réponse d'outil "
        "(injection) : aucun appel d'outil non prévu.",
        "<b>O8</b> — S'abstenir (« preuves insuffisantes ») lorsqu'aucune source autorisée ne répond à la question.",
    ])]
    st += [P("1.4 Périmètre", "h2"), table([
        ["Élément", "Dans le périmètre", "Hors périmètre"],
        ["Entrées", "Question en français ; photo JPEG/PNG d'un pupitre ou d'une plaque ; identité de l'utilisateur",
         "Vidéo, audio, flux capteurs temps réel"],
        ["Sorties", "Réponse sourcée (document, page, figure), demande de clarification, abstention, refus, brouillon "
         "de ticket", "Ordre de pilotage, diagnostic certifié"],
        ["Outil MCP", "Service de maintenance de démonstration : historique d'un équipement, tickets ouverts, "
         "création de ticket", "Intégration à une GMAO réelle"],
        ["Action sensible", "Création de ticket, uniquement après approbation humaine liée à l'utilisateur et au "
         "contenu exact", "Toute action autonome"],
        ["Hors périmètre explicite", "—", "Pilotage ou arrêt de machines ; diagnostic garanti ; intervention autonome ; "
         "modification de consignes de sécurité ; données personnelles réelles"],
    ], [3.0, 8.0, 6.0])]
    st += [P("1.5 Hypothèses et contraintes", "h2"), bullets([
        f"<b>Matériel</b> : {cfg['materiel']['gpu']} ; mémoire vive {cfg['materiel']['ram']} ; "
        f"stockage {cfg['materiel']['disque']}. Le modèle vision-langage tient-il en mémoire ? À mesurer en semaine 3.",
        "<b>Modèles</b> à poids ouverts, inférence locale ; aucun envoi de document vers une API externe.",
        "<b>Budgets</b> par demande, appliqués par le code : 3 appels MCP, 6 appels au modèle, 60 s de traitement "
        "automatique (hors attente humaine), image ≤ 8 Mpx, réponse ≤ 1 024 jetons.",
        "<b>Temps</b> : 6 semaines ; un livrable par semaine. Le corpus est généré par script pour pouvoir être "
        "corrigé et régénéré à l'identique.",
        "<b>Équipe</b> : " + " ; ".join(f"{m['prenom']} {m['nom']}" for m in membres) + ".",
    ])]

    # ---------------- 2. corpus
    st += [CondPageBreak(6 * cm), P("2. Constitution du corpus documentaire", "h1"), P("2.1 Démarche", "h2"), P(
        "Les deux voies proposées ont été combinées. <b>Voie 1 (sources publiques)</b> : l'assistant a proposé des "
        "jeux de données et documents publics ; chaque lien et chaque licence ont été vérifiés sur la page officielle. "
        "Aucune source ne couvrait à la fois le français, deux familles d'équipements, des figures citables et un "
        "historique d'interventions ; plusieurs avaient une licence incompatible (voir 2.5). <b>Voie 2 (génération "
        "synthétique)</b> : retenue pour le corpus principal. L'assistant (Claude Code) a rédigé le contenu structuré "
        "des documents et le code des figures ; un script déterministe produit les PDF, le scan simulé, les photos et "
        "un manifeste avec empreintes SHA-256. Chaque document a été relu par un membre de l'équipe et les corrections "
        "sont tracées dans l'inventaire.")]
    st += [P("2.2 Composition", "h2"), table([
        ["Indicateur", "Valeur", "Exigence"],
        ["Éléments du corpus", f"{len(rows)} ({len(docs)} PDF + {len(photos)} photos)", "30 à 50"],
        ["Familles", f"pompes : {fam['pompes']} ; compresseurs : {fam['compresseurs']} ; transverses : "
         f"{fam['transverse']} (sécurité, glossaire, tickets, contrat, note piégée)", "2 familles"],
        ["Types", " ; ".join(f"{k} : {v}" for k, v in sorted(types.items())), "types variés"],
        ["Éléments visuels exploitables", f"{len(visual)} éléments (dont {figs} figures numérotées, tableaux, "
         f"{len(photos)} photos)", "≥ 10"],
        ["Documents scannés (OCR)", f"{len(scans)} : " + ", ".join(scans), "≥ 2"],
        ["Pages", f"{pages} pages au total", "—"],
        ["Langue", "100 % français", "français de préférence"],
        ["Provenance / licence", "100 % synthétique, généré par l'équipe ; aucune donnée personnelle", "public ou synthétique"],
        ["Cas de test", " ; ".join(f"{k} : {v}" for k, v in sorted(usage.items())), "≥ 2 contradictoires, ≥ 1 injection"],
    ], [4.0, 9.5, 3.5])]
    st += [P("2.3 Documents prévus pour l'évaluation (semaine 5)", "h2"), table([
        ["Piège", "Documents (document_id)", "Comportement attendu"],
        ["Voyants similaires, sens différents", "mdp_man_util ↔ mdc_man_util ; photos orange MDP / MDC",
         "Identifier l'équipement avant de conclure"],
        ["Versions contradictoires (remplacement)", "mdp_bt_2024_03 (45 N·m, remplacé, scanné) → mdp_bt_2025_01 "
         "(60 N·m) ; mdp_man_maint (45 N·m)", "Citer la version active, signaler l'écart"],
        ["Contradiction entre documents actifs", "mdc_man_maint (vidange 4 000 h) ↔ mdc_proc_vidange (2 000 h)",
         "Exposer la contradiction, ne pas trancher"],
        ["Injection dans un document", "trans_note_inj", "Aucune action, aucune élévation de droits"],
        ["Injection dans une photo (OCR)", "photo_pupitre_injection_etiquette", "Étiquette traitée comme donnée"],
        ["Injection dans l'historique MCP", "historique_interventions_mdp (INT-0009)", "Description traitée comme donnée"],
        ["Accès restreint", "trans_contrat_maint (responsables seulement)", "Invisible pour techniciens et prestataire"],
        ["Photo ambiguë / incomplète", "photo_pupitre_ambigu_floue ; photo_pupitre_mdc_rouge", "Demande de clarification"],
    ], [4.2, 7.3, 5.5])]
    from reportlab.platypus import Image as RLImage
    import pymupdf as _fz
    import io as _io
    _corpus = Path(__file__).resolve().parents[1] / "corpus"
    _cells, _caps = [], []
    for _f, _c in [("images/photo_pupitre_mdp_orange_nette.png", "Pompe MDP-200 : V2 orange fixe = préalarme température palier"),
                   ("images/photo_pupitre_mdc_orange_nette.png", "Compresseur MDC-55 : même aspect, V2 orange fixe = filtre à air colmaté"),
                   ("images/photo_pupitre_ambigu_floue.png", "Photo floue : plaque illisible, clarification attendue")]:
        _cells.append(RLImage(str(_corpus / _f), width=5.4 * cm, height=4.05 * cm))
        _caps.append(P(_c, "cap"))
    with _fz.open(_corpus / "documents/famille_1/mdp_sch_hydr.pdf") as _pdf:
        _pix = _pdf[0].get_pixmap(dpi=110, clip=_pdf[0].rect * _fz.Matrix(1, 0.62))
    _sch = RLImage(_io.BytesIO(_pix.tobytes("png")), width=8.2 * cm, height=8.2 * cm * _pix.height / _pix.width)
    with _fz.open(_corpus / "documents/famille_2/mdc_proc_revision_scan.pdf") as _pdf:
        _pix2 = _pdf[0].get_pixmap(dpi=90, clip=_pdf[0].rect * _fz.Matrix(1, 0.5))
    _scan = RLImage(_io.BytesIO(_pix2.tobytes("png")), width=8.2 * cm, height=8.2 * cm * _pix2.height / _pix2.width)
    _t1 = Table([_cells, _caps], colWidths=[5.67 * cm] * 3)
    _t2 = Table([[_sch, _scan], [P("Schéma hydraulique MDP (mdp_sch_hydr, figure 1 p.1), après correction VA1/VR1", "cap"),
                                 P("Procédure scannée MDC (mdc_proc_revision_scan, p.1) : aucune couche texte, OCR requis", "cap")]],
                colWidths=[8.5 * cm] * 2)
    for _t in (_t1, _t2):
        _t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    st += [P("Exemples d'éléments visuels du corpus", "h2"), _t1, Spacer(1, 4), _t2,
           P("Figure A — Le cas ambigu central : deux pupitres presque identiques dont le voyant orange n'a pas le même "
             "sens ; un schéma citable ; un document scanné.", "cap")]
    st += [P("2.4 Inventaire et traçabilité de l'IA", "h2"), P(
        "<b>corpus/inventaire.csv</b> (UTF-8, virgule) contient une ligne par fichier avec les 20 colonnes demandées ; "
        "un contrôle automatique vérifie que chaque fichier de <i>documents/</i> et <i>images/</i> y figure et "
        "inversement, et que chaque fichier est nommé <i>&lt;document_id&gt;.&lt;extension&gt;</i>. Les documents "
        "transverses sont rangés dans <i>documents/transverse/</i> car ils concernent les deux familles. "
        "<b>corpus/prompts_corpus.md</b> recense les 15 prompts (P01 à P15) avec l'outil et la date ; la colonne "
        "<i>outil_ia</i> de l'inventaire y renvoie. Le type précis (bulletin, guide de dépannage, check-list…) est "
        "conservé dans la colonne <i>remarques</i> lorsque la valeur imposée de <i>type_document</i> est plus générale. "
        f"{len(corrected)} documents ont fait l'objet d'une correction après relecture. Extrait :")]
    ex = [r for r in rows if r["document_id"] in ("mdp_man_util", "mdp_bt_2024_03", "trans_note_inj",
                                                    "photo_pupitre_mdc_orange_nette")]
    st.append(table([["document_id", "type", "p.", "format", "éléments visuels", "corrections", "usage"]] +
                    [[r["document_id"], r["type_document"], str(r["nb_pages"]), r["format"],
                      r["elements_visuels"][:70], r["corrections"][:70], r["usage_test"]] for r in ex],
                    [3.3, 1.6, 0.6, 1.7, 4.5, 3.7, 1.6], font=7))
    st += [P("2.5 Analyse critique de l'usage de l'IA", "h2"), bullets([
        "<b>Licences affirmées sans vérification.</b> Plusieurs sources proposées comme « réutilisables » ne l'étaient "
        "pas : FQuAD (CC BY-NC-SA, redistribution interdite), guide INRS ED 6109 (droits réservés), MPMQA (licence non "
        "précisée), jeux Roboflow (licence variable selon le projet). Écartées ou réduites à un lien de référence.",
        "<b>Lien imprécis.</b> Le lien donné pour mMARCO-fr pointait vers un modèle entraîné sur le jeu, pas vers le "
        "jeu de données lui-même ; corrigé dans docs/05_donnees.md.",
        "<b>Incohérence technique introduite par l'IA.</b> Dans cinq documents MDP, le repère <b>V1/V2</b> désignait à "
        "la fois les voyants du pupitre et les vannes d'aspiration / de refoulement (« ouvrir V1 », « cadenasser V1 et "
        "V2 »). Ambigu pour un technicien comme pour la recherche : vannes renommées <b>VA1/VR1</b> dans le manuel, la "
        "fiche de codes, le schéma hydraulique (figure et nomenclature) et deux procédures.",
        "<b>Écart à la consigne non détecté par l'IA.</b> La première version ne comportait qu'un document scanné ; "
        "le bulletin papier MDP-BT-2024-03 a été ajouté sous forme scannée.",
        "<b>Réalisme.</b> Documents courts (1 à 2 pages), scan simulé, photos de synthèse : le corpus est cohérent par "
        "construction mais plus propre que la réalité (risque D1). Les contradictions et injections, elles, sont "
        "volontaires et signalées dans l'inventaire.",
    ])]

    # ---------------- 3. architecture
    arch_start = len(st) + 3
    st += [CondPageBreak(8 * cm), P("3. Architecture cible", "h1"), P(
        "MaintiDoc reçoit une question, éventuellement accompagnée d'une photo. Il vérifie d'abord qui pose la "
        "question, cherche les passages et figures pertinents <b>uniquement</b> dans les documents autorisés, consulte "
        "si besoin l'historique de l'équipement, puis rédige une réponse dont chaque citation est contrôlée. Une action "
        "(création de ticket) n'est jamais exécutée sans validation humaine. Les cercles rouges indiquent les points "
        "de contrôle (CP)."),
        KeepTogether([diagram_architecture(), P("Figure 1 — Schéma par blocs fonctionnels et points de contrôle "
                                                "(source : docs/diagrammes/architecture_blocs.mmd)", "cap")])]
    fig_arch = st.pop()
    st += [P("3.2 Fiche par bloc", "h2"), table([
        ["Bloc", "Rôle", "Entrées", "Sorties", "Outil envisagé"],
        ["Interface", "Permettre de poser une question avec photo et d'approuver un ticket", "Texte, photo, clic "
         "d'approbation", "Réponse, sources cliquables, brouillon", "Streamlit"],
        ["API", "Authentifier l'utilisateur et faire respecter ses droits", "Requête HTTP + session", "Requête "
         "enrichie des groupes ; réponse JSON", "FastAPI"],
        ["Orchestration", "Enchaîner les étapes dans l'ordre et appliquer les budgets", "Requête autorisée",
         "Réponse structurée, brouillon, appels d'outils", "LangGraph"],
        ["Recherche documentaire", "Trouver passages, tableaux et figures parmi les documents autorisés", "Question, "
         "description de la photo, groupes", "Éléments classés avec document, page, élément", "Qdrant, bge-m3, "
         "reranker (à préciser)"],
        ["Modèle vision-langage", "Décrire la photo, identifier l'équipement, rédiger la réponse", "Photo, passages "
         "récupérés (comme données)", "Observations, réponse JSON avec citations", "Qwen2.5-VL-7B (repli 3B)"],
        ["Vérification des citations", "S'assurer que chaque citation existe et soutient l'affirmation", "Réponse + "
         "éléments récupérés", "Réponse validée, ou clarification / abstention", "Règles + second appel modèle"],
        ["Outil MCP", "Exposer historique, tickets ouverts et création de ticket", "Appel d'outil + identité + jeton",
         "Interventions, tickets, n° de ticket", "SDK MCP Python"],
        ["Validation humaine", "Faire approuver le contenu exact du ticket", "Brouillon", "Jeton d'approbation signé",
         "Écran Streamlit + HMAC"],
        ["Ingestion", "Rendre le corpus recherchable", "PDF, photos, inventaire", "Éléments indexés + métadonnées",
         "PyMuPDF, OCR Tesseract (à préciser)"],
        ["Stockage", "Conserver vecteurs, métadonnées, fichiers et journaux", "Éléments, fichiers", "Résultats "
         "filtrés, URL de fichiers", "Qdrant, PostgreSQL, MinIO"],
    ], [2.6, 4.4, 3.4, 3.6, 3.0], font=7.5)]
    cp_block = [P("3.1 Points de contrôle", "h2"), table([
        ["CP", "Où", "Ce qui est vérifié"],
        ["CP1", "API", "Identité de l'utilisateur et liste de ses groupes ; refus immédiat si aucun droit"],
        ["CP2", "Recherche documentaire", "Filtre sur les groupes d'accès <b>dans la requête</b> à l'index (avant "
         "récupération) ; nouveau contrôle à l'ouverture d'un fichier ou d'une image"],
        ["CP3", "Vérification des citations", "Chaque citation correspond à un élément récupéré et autorisé, et le "
         "passage soutient l'affirmation ; sinon correction, clarification ou abstention"],
        ["CP4", "Validation humaine", "L'utilisateur approuve le contenu exact du brouillon ; toute modification "
         "impose une nouvelle approbation"],
        ["CP5", "Serveur MCP", "À chaque appel : droit de l'utilisateur sur l'équipement ; pour la création : jeton "
         "signé valide, hash du contenu identique, clé d'idempotence non encore utilisée"],
    ], [1.2, 3.6, 12.2])]
    st[arch_start:arch_start] = cp_block + [fig_arch]
    st += [P("3.3 Parcours d'une requête", "h2"), P(
        "Exemple : le technicien pompes u_tech_p01 envoie la photo du pupitre de EQ-P-002 et demande « Que signifie ce "
        "voyant orange ? »."), bullets([
        "<b>1. Qui demande ?</b> L'API identifie u_tech_p01 et ses groupes (grp_pompes) — CP1.",
        "<b>2. Que montre la photo ?</b> Le modèle vision-langage décrit le pupitre (V1 vert et V2 orange allumés) et "
        "lit la plaque (MDP-200, repère EQ-P-002). Si la plaque est illisible, l'agent s'arrête et demande une photo "
        "de la plaque.",
        "<b>3. Que disent les documents ?</b> La recherche interroge l'index avec un filtre sur grp_pompes — CP2 — et "
        "remonte le tableau des voyants du manuel MDP (page 1) et la figure du pupitre ; les documents compresseurs ne "
        "sont même pas candidats.",
        "<b>4. Que s'est-il passé avant ?</b> L'agent appelle get_equipment_history(EQ-P-002) — CP5 — : deux "
        "préalarmes de température palier en juillet et septembre 2026.",
        "<b>5. Rédaction.</b> Le modèle rédige la réponse ; les passages et l'historique lui sont fournis comme "
        "<b>données</b>, jamais comme instructions.",
        "<b>6. Vérification.</b> Chaque citation est contrôlée — CP3. La réponse indique les sources, les observations "
        "sur la photo et ce qui reste incertain.",
        "<b>7. Action.</b> Si un ticket est utile (préalarme récurrente), un brouillon est affiché ; il n'est créé "
        "qu'après approbation — CP4 puis CP5.",
    ])]
    _mono = ParagraphStyle("mono", fontName="Courier", fontSize=6.5, leading=8.4)
    _json = """{
  "status": "awaiting_approval",
  "equipment": {"equipment_id": "EQ-P-002", "model": "MDP-200", "identified_by": "plaque (photo)"},
  "answer": "Le voyant V2 orange fixe signale une préalarme de température du palier (≥ 80 °C, sonde TT-101).
             La pompe n'est pas arrêtée. Contrôler le graissage et les vibrations (MDP-PROC-GRAISSAGE).",
  "citations": [
    {"document_id": "mdp_man_util", "version": "1.0", "page": 1, "element_id": "table_1_2"},
    {"document_id": "mdp_man_util", "version": "1.0", "page": 1, "element_id": "figure_1_1"}],
  "history": ["INT-0002 (2026-07-02) préalarme, 84 °C", "INT-0003 (2026-09-28) préalarme récurrente, 86 °C"],
  "observations": ["V1 vert et V2 orange allumés fixes", "plaque lisible : MDP-200, P2-0457, EQ-P-002"],
  "uncertainties": ["température actuelle non connue : relever TT-101 sur l'afficheur"],
  "proposed_action": {"type": "ticket_draft", "requires_approval": true, "existing_ticket": "TCK-0102"}
}"""
    _jt = Table([[Paragraph(_json.replace(" ", "&nbsp;").replace("\n", "<br/>"), _mono)]], colWidths=[17 * cm])
    _jt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f6f8")),
                             ("BOX", (0, 0), (-1, -1), 0.4, GREY)]))
    st += [P("Exemple de sortie structurée attendue (CU1)", "h2"), P(
        "La réponse n'est pas un texte libre : c'est un objet validé par schéma, ce qui permet de vérifier les "
        "citations (CP3) et de bloquer toute action non approuvée. Les identifiants d'éléments sont indicatifs ; ils "
        "seront produits par l'ingestion en semaine 2."), _jt]
    st += [P("3.4 Questions ouvertes et hypothèses à vérifier", "h2"), table([
        ["Question", "Comment / quand"],
        ["Le modèle 7B tiendra-t-il sur notre GPU avec les embeddings et le reranker ?", "Mesure mémoire et latence en "
         "semaine 3 ; repli quantification 4 bits ou modèle 3B"],
        ["Faut-il un OCR pour tous les documents, ou seulement pour les pages sans couche texte ?", "Détection "
         "automatique en semaine 2 ; comparer avec la lecture directe de l'image par le VLM"],
        ["Faut-il des embeddings d'images (pages, figures) en plus du texte ?", "Comparer recall@5 avec / sans en "
         "semaine 2"],
        ["Le VLM lit-il assez bien la plaque signalétique pour identifier l'équipement ?", "Tests sur les 5 photos "
         "+ photos réelles autorisées en semaine 3"],
        ["Le corpus synthétique est-il assez difficile pour mesurer un gain du reranker ?", "Rapport honnête en "
         "semaine 5, ajout de manuels publics réels si les métriques saturent"],
        ["Comment détecter une citation qui existe mais ne soutient pas l'affirmation ?", "Règles + second appel "
         "modèle, évalués manuellement en semaine 3"],
    ], [9.0, 8.0])]

    # ---------------- 4. flux de données
    st += [CondPageBreak(9 * cm), P("4. Flux de données et contrôle d'accès", "h1"), P("4.1 Flux d'ingestion", "h2"), P(
        "Hors ligne, chaque fichier de l'inventaire est lu. Les PDF avec couche texte sont découpés directement ; les "
        "pages scannées passent d'abord par l'OCR, en conservant la position du texte sur la page. Chaque document est "
        "découpé en éléments (paragraphe, ligne de tableau, figure avec sa légende et sa zone) ; chaque élément reçoit "
        "un embedding et l'ensemble des métadonnées de l'inventaire, dont les groupes d'accès. Les originaux sont "
        "conservés avec leur empreinte pour pouvoir afficher la page citée."),
        KeepTogether([diagram_ingestion(), P("Figure 2 — Flux d'ingestion (source : docs/diagrammes/flux_ingestion.mmd)",
                                             "cap")])]
    st += [P("4.2 Flux d'une requête", "h2"), table([
        ["Étape", "Données qui circulent", "Contrôle"],
        ["Interface → API", "Question, photo, jeton de session", "CP1 : identité, groupes, taille de l'image"],
        ["API → orchestration", "Question, photo, user_id, groupes", "Budgets initialisés"],
        ["Orchestration ↔ VLM", "Photo → observations (équipement, voyants, texte lu)", "Texte lu sur la photo = "
         "donnée non fiable"],
        ["Orchestration ↔ recherche", "Requête + filtre de groupes → éléments (document_id, version, page, "
         "element_id, score)", "CP2 : filtre dans la requête ; documents remplacés signalés"],
        ["Orchestration ↔ MCP", "equipment_id → interventions, tickets ouverts", "CP5 : droit sur la famille"],
        ["Orchestration ↔ VLM", "Éléments + historique (balisés comme données) → réponse JSON", "Liste blanche "
         "d'outils, budgets"],
        ["Vérification → API → interface", "Réponse, citations, incertitudes, statut", "CP3 ; liens vers les pages "
         "re-contrôlés"],
    ], [3.6, 7.6, 5.8])]
    st += [P("4.3 Flux de création de ticket", "h2"), P(
        "L'agent prépare un brouillon (équipement, titre, symptôme, sources, priorité proposée). L'utilisateur voit le "
        "contenu exact et l'approuve ; l'API émet alors un jeton signé qui lie l'utilisateur, le hash du contenu et une "
        "clé d'idempotence. Le serveur MCP recalcule le hash et refuse tout contenu différent de celui approuvé ; "
        "s'il a déjà vu la clé, il renvoie le ticket existant au lieu d'en créer un second. Un ticket déjà ouvert sur "
        "l'équipement (ex. TCK-0102 sur EQ-P-002) est signalé avant toute proposition."),
        KeepTogether([diagram_ticket(), P("Figure 3 — Flux de création de ticket (source : docs/diagrammes/flux_ticket.mmd)",
                                          "cap")])]
    st += [P("4.4 Schéma des métadonnées d'un élément indexé", "h2"), table([
        ["Champ", "Exemple", "Usage"],
        ["document_id, version, statut", "mdp_bt_2025_01, v2.0, actif", "Citation ; préférence pour la version active"],
        ["remplace / remplacé par", "mdp_bt_2024_03", "Signaler un document obsolète"],
        ["page, element_id, type d'élément", "p.1, figure_1_1, figure", "Citation précise (page + figure)"],
        ["bbox", "[x0, y0, x1, y1]", "Afficher la zone de la figure citée"],
        ["famille, modèles, equipement_id", "pompes, MDP-200, EQ-P-002", "Filtre et désambiguïsation"],
        ["groupes d'accès, confidentialité", "grp_pompes ; grp_responsables, interne", "CP2 : filtre avant récupération"],
        ["langue, format, source OCR", "fr, pdf_scanne, ocr=oui", "Qualité du texte, repli sur l'image"],
        ["sha256, fichier", "73a154…, documents/famille_1/…", "Intégrité, affichage de l'original"],
        ["usage_test", "contradictoire", "Rattachement aux scénarios d'évaluation"],
    ], [5.0, 5.4, 6.6])]
    group_count = Counter()
    for r in rows:
        for g in r["groupe_acces"].split(" ; "):
            group_count[g.strip()] += 1
    st += [P("4.5 Modèle d'accès", "h2"), P(
        "Quatre groupes fictifs. Le droit est vérifié à trois endroits : avant la recherche (filtre de l'index), à "
        "l'ouverture d'un fichier, et dans le serveur MCP à chaque appel."), table([
        ["Groupe (utilisateurs)", "Documents accessibles", "Nb d'éléments", "Outils MCP / tickets"],
        ["grp_pompes (u_tech_p01, u_tech_p02)", "Famille pompes + transverses non confidentiels",
         str(group_count["grp_pompes"]), "Historique, tickets ouverts et création : MDP"],
        ["grp_compresseurs (u_tech_c01)", "Famille compresseurs + transverses non confidentiels",
         str(group_count["grp_compresseurs"]), "Historique, tickets ouverts et création : MDC"],
        ["grp_responsables (u_resp_01)", "Tout le corpus, y compris le contrat (confidentiel)",
         str(group_count["grp_responsables"]), "Toutes familles"],
        ["grp_prestataires (u_presta_01)", "Sécurité (consignation, EPI) et glossaire",
         str(group_count["grp_prestataires"]), "Aucun"],
    ], [4.6, 5.6, 2.0, 4.8])]

    # ---------------- 5. risques
    r = lambda i: who(i)  # noqa: E731
    st += [CondPageBreak(9 * cm), P("5. Analyse des risques", "h1"), P(
        "Probabilité (P) et impact (I) de 1 (faible) à 3 (fort) ; criticité C = P × I. Les risques de criticité ≥ 6 "
        "ont une mesure planifiée et un test associé. Le registre complet (modèle de menaces inclus) est tenu dans "
        "docs/03_analyse_risques.md et revu chaque semaine."), table([
        ["#", "Risque", "Catégorie", "P", "I", "C", "Mesure prévue", "Resp."],
        ["R1", "Hallucination, citation inexistante ou qui ne soutient pas l'affirmation", "Technique", "3", "3", "9",
         "Citations limitées aux éléments récupérés ; vérification CP3 ; abstention ; mesure en semaine 5", r(0)],
        ["R2", "Injection de prompt dans un document, une photo (OCR) ou une réponse MCP", "Sécurité", "3", "3", "9",
         "Contenus traités comme données ; liste blanche d'outils ; pas d'accès réseau sortant ; 3 cas piégés + tests", r(1)],
        ["R3", "Fuite entre groupes d'accès (passage, image ou existence d'un document)", "Sécurité", "2", "3", "6",
         "Filtre dans la requête à l'index ; contrôle à l'ouverture des fichiers ; scénarios d'accès refusé", r(1)],
        ["R4", "Création de ticket non approuvée, modifiée après approbation, ou en double", "Sécurité", "2", "3", "6",
         "Jeton HMAC lié à l'utilisateur et au hash ; vérif. serveur MCP ; clé d'idempotence ; tests de falsification", r(0)],
        ["R5", "Erreurs introduites par l'IA dans le corpus (valeurs, repères, renvois)", "Données", "3", "2", "6",
         "Relecture par famille ; corrections tracées ; validation automatique du manifeste ; cohérence avec l'historique", r(2)],
        ["R6", "Licence d'un document ou d'un jeu externe non respectée", "Données", "2", "2", "4",
         "Corpus 100 % synthétique ; licence vérifiée sur la page officielle avant tout ajout ; sources écartées listées", r(2)],
        ["R7", "Ressources matérielles insuffisantes (VLM trop lourd pour le GPU)", "Technique", "2", "3", "6",
         "Quantification 4 bits ; limite de pixels ; embeddings sur CPU ; repli Qwen2.5-VL-3B ; client factice pour les tests", r(0)],
        ["R8", "Confusion entre familles à cause de voyants similaires", "Technique", "3", "2", "6",
         "Identification par la plaque exigée ; filtre par famille ; négatifs difficiles pour le reranker", r(1)],
        ["R9", "Citation d'un document remplacé ou contradiction non signalée", "Données", "2", "2", "4",
         "Statut et lien de remplacement dans les métadonnées ; consigne de signaler les divergences", r(2)],
        ["R10", "Corpus trop simple : métriques flatteuses", "Données", "3", "2", "6",
         "Pièges volontaires ; séparation train/test par document ; manuels publics réels en test de généralisation", r(2)],
        ["R11", "Retard d'intégration bout en bout", "Organisation", "2", "3", "6",
         "Chaîne complète « fil fin » avec composants factices dès la semaine 3 ; revue hebdomadaire du planning", r(0)],
        ["R12", "Secret (clé, mot de passe) publié dans le dépôt", "Sécurité", "1", "3", "3",
         ".env exclu par .gitignore ; .env.example sans valeur ; scan de secrets avant chaque rendu", r(0)],
    ], [1.1, 4.1, 2.0, 0.5, 0.5, 0.6, 6.5, 1.7], font=7.4)]

    # ---------------- 6. planning
    st += [P("6. Planning et organisation de l'équipe", "h1"), P("6.1 Répartition des responsabilités", "h2")]
    areas = [("Corpus, inventaire, relecture famille pompes ; ingestion ; agent et MCP", 0),
             ("Relecture famille compresseurs ; recherche et reranker ; évaluation", 1),
             ("Documents transverses ; interface ; déploiement et documentation", 2)]
    role_rows = [["Membre", "Responsabilités principales"]]
    for i, m in enumerate(membres):
        resp = [a for a, k in areas if min(k, len(membres) - 1) == i]
        role_rows.append([f"{m['prenom']} {m['nom']}", " ; ".join(resp)])
    st.append(table(role_rows, [4.0, 13.0]))
    st += [P("6.2 Planning des semaines 2 à 6", "h2"), table([
        ["Sem", "Objectif", "Tâches principales", "Critère de fin", "Resp."],
        ["2", "Ingestion et recherche", "Extraction PyMuPDF + OCR ; découpage en éléments ; index Qdrant avec "
         "métadonnées et groupes ; recherche hybride + RRF ; 30 questions pilotes", "Recall@5 mesuré ; 0 fuite "
         "inter-groupes sur les cas d'accès", whos(0, 1)],
        ["3", "VLM et réponses sourcées", "Servir le VLM (quantifié si besoin) ; prompts versionnés ; schéma de réponse "
         "(statut, citations, incertitudes) ; vérification des citations ; chaîne « fil fin »", "Réponse citant page "
         "+ figure sur CU1 ; mémoire GPU mesurée", f"{who(0)}"],
        ["4", "Agent, MCP, validation humaine", "Graphe LangGraph avec budgets ; serveur MCP (3 outils) ; jeton "
         "d'approbation + idempotence ; API et interface", "Ticket créé seulement après approbation, contenu identique",
         whos(0, 2)],
        ["5", "Évaluation", "Jeu de scénarios (nominal, ambigu, contradictions, accès, injections) ; adaptation du "
         "reranker ; indicateurs chiffrés", "Rapport comparatif sans / avec reranker, même négatif", f"{who(1)}"],
        ["6", "Déploiement et soutenance", "Docker Compose ; tests et scan de secrets ; mesures de latence ; fiche de "
         "limites ; répétition de la démo", "Démo bout en bout depuis un clone propre", "tous"],
    ], [1.2, 2.8, 6.7, 4.3, 2.0], font=7.6)]
    st.append(P("Marge : une demi-journée par semaine est réservée aux imprévus (installation GPU, versions de "
                "bibliothèques). Si le GPU n'est pas disponible, le développement continue avec un client VLM factice "
                "et le modèle 3B sur CPU (risque R7).", "note"))

    # ---------------- annexe
    st += [PageBreak(), P("Annexe A — Inventaire du corpus (résumé)", "h1"), P(
        "Version complète (20 colonnes) : corpus/inventaire.csv. Provenance et licence : synthétique pour tous les "
        "éléments ; généré avec Claude Code, relu par l'équipe.")]
    st.append(table([["document_id", "famille", "type", "p.", "format", "groupes", "usage_test"]] +
                    [[x["document_id"], x["famille_equipement"], x["type_document"], str(x["nb_pages"]), x["format"],
                      x["groupe_acces"].replace("grp_", ""), x["usage_test"]] for x in rows],
                    [4.6, 2.1, 2.2, 0.6, 1.7, 3.9, 1.9], font=7))

    SimpleDocTemplate(str(out_path), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                      bottomMargin=1.8 * cm, title=f"L1 MaintiDoc — {team} — Rapport",
                      author=", ".join(f"{m['prenom']} {m['nom']}" for m in membres)).build(
        st, onFirstPage=lambda c, d: None, onLaterPages=footer)
    if not _second_pass:
        import pymupdf
        with pymupdf.open(out_path) as pdf:
            for t in TOC_TITLES:
                TOC[t] = next(i + 1 for i, pg in enumerate(pdf) if i > 0 and t in pg.get_text())
        build(cfg, rows, out_path, _second_pass=True)
