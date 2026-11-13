"""Figures vectorielles (reportlab.graphics) insérées dans les PDF du corpus."""

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors

W, H = 440, 220

LED_COLORS = {"vert": colors.HexColor("#2e9e44"), "orange": colors.HexColor("#f08a00"),
              "rouge": colors.HexColor("#d22b2b"), "eteint": colors.HexColor("#9a9a9a")}


def _box(d, x, y, w, h, label, fill=colors.HexColor("#eef2f7"), size=8):
    d.add(Rect(x, y, w, h, fillColor=fill, strokeColor=colors.black, strokeWidth=0.8))
    for i, part in enumerate(label.split("\n")):
        d.add(String(x + w / 2, y + h / 2 + 3 - i * 10, part, textAnchor="middle", fontSize=size))


def _arrow(d, x1, y1, x2, y2):
    d.add(Line(x1, y1, x2, y2, strokeWidth=1))
    if x2 != x1:
        s = 1 if x2 > x1 else -1
        d.add(Polygon([x2, y2, x2 - 6 * s, y2 + 3, x2 - 6 * s, y2 - 3], fillColor=colors.black))
    else:
        s = 1 if y2 > y1 else -1
        d.add(Polygon([x2, y2, x2 - 3, y2 - 6 * s, x2 + 3, y2 - 6 * s], fillColor=colors.black))


def control_panel(model, leds, lit=None):
    """Pupitre de commande : 3 voyants étiquetés, afficheur, boutons, arrêt d'urgence."""
    d = Drawing(W, H)
    d.add(Rect(20, 10, 400, 200, fillColor=colors.HexColor("#d9dde2"), strokeColor=colors.black))
    d.add(String(220, 190, f"PUPITRE {model}", textAnchor="middle", fontSize=11))
    for i, (repere, color, label) in enumerate(leds):
        x = 70 + i * 90
        fill = LED_COLORS[color] if lit in (None, repere) else LED_COLORS["eteint"]
        d.add(Circle(x, 140, 14, fillColor=fill, strokeColor=colors.black))
        d.add(String(x, 115, repere, textAnchor="middle", fontSize=8))
        d.add(String(x, 105, label, textAnchor="middle", fontSize=7))
    d.add(Rect(320, 125, 80, 30, fillColor=colors.HexColor("#1d3b2a"), strokeColor=colors.black))
    d.add(String(360, 136, "CODE --", textAnchor="middle", fontSize=9, fillColor=colors.HexColor("#7dff9a")))
    d.add(String(360, 112, "AF1 afficheur", textAnchor="middle", fontSize=7))
    for i, (rep, lab, col) in enumerate([("BP1", "MARCHE", "#2e9e44"), ("BP2", "ARRÊT", "#444444"),
                                         ("BP3", "ACQUIT.", "#2a5db0")]):
        x = 70 + i * 90
        d.add(Rect(x - 18, 45, 36, 24, fillColor=colors.HexColor(col), strokeColor=colors.black))
        d.add(String(x, 32, f"{rep} {lab}", textAnchor="middle", fontSize=7))
    d.add(Circle(360, 60, 20, fillColor=LED_COLORS["rouge"], strokeColor=colors.black))
    d.add(Circle(360, 60, 25, fillColor=None, strokeColor=colors.HexColor("#e8c400"), strokeWidth=4))
    d.add(String(360, 25, "AU arrêt d'urgence", textAnchor="middle", fontSize=7))
    return d


def hydraulic_pump(model):
    d = Drawing(W, H)
    _box(d, 10, 90, 60, 50, "Bâche\nd'aspiration")
    _box(d, 90, 100, 45, 30, "VA1\nvanne asp.", size=7)
    _box(d, 155, 95, 70, 40, f"POMPE\n{model}", fill=colors.HexColor("#cfe3ff"))
    _box(d, 245, 100, 45, 30, "CL1\nclapet", size=7)
    _box(d, 310, 100, 45, 30, "VR1\nvanne ref.", size=7)
    _box(d, 375, 95, 55, 40, "Réseau\naval")
    for x1, x2 in [(70, 90), (135, 155), (225, 245), (290, 310), (355, 375)]:
        _arrow(d, x1, 115, x2, 115)
    _box(d, 140, 30, 50, 28, "PS-102\npressostat", size=7)
    _arrow(d, 165, 58, 165, 95)
    _box(d, 200, 165, 55, 28, "TT-101\nsonde palier", size=7)
    _arrow(d, 210, 165, 200, 135)
    _box(d, 255, 30, 55, 28, "LS-103\nfuite garn.", size=7)
    _arrow(d, 270, 58, 210, 95)
    _box(d, 300, 160, 50, 28, "PI-104\nmanomètre", size=7)
    _arrow(d, 325, 160, 330, 130)
    return d


def pneumatic_compressor(model):
    d = Drawing(W, H)
    _box(d, 10, 120, 55, 40, "FA\nfiltre air")
    _box(d, 85, 115, 70, 50, f"BLOC VIS\n{model}", fill=colors.HexColor("#cfe3ff"))
    _box(d, 175, 115, 70, 50, "Réservoir\nséparateur\nSEP")
    _box(d, 265, 120, 60, 40, "Refroid.\nair final")
    _box(d, 345, 120, 50, 40, "Sortie\nair 8 bar")
    for x1, x2 in [(65, 85), (155, 175), (245, 265), (325, 345)]:
        _arrow(d, x1, 140, x2, 140)
    _box(d, 175, 35, 70, 35, "Refroid.\nhuile")
    _box(d, 85, 35, 70, 35, "FH\nfiltre huile")
    _arrow(d, 210, 115, 210, 70)
    _arrow(d, 175, 52, 155, 52)
    _arrow(d, 120, 70, 120, 115)
    _box(d, 10, 185, 70, 25, "PDS-201 ΔP filtre", size=7)
    _arrow(d, 40, 185, 40, 160)
    _box(d, 255, 185, 75, 25, "TT-202 temp. huile", size=7)
    _arrow(d, 270, 185, 230, 165)
    _box(d, 345, 60, 70, 25, "SV soupape 11 bar", size=7)
    _arrow(d, 380, 85, 370, 120)
    return d


def electrical(model, power_kw, prefix):
    d = Drawing(W, H)
    _box(d, 10, 160, 70, 35, "Q1\nsectionneur", size=7)
    _box(d, 110, 160, 70, 35, "KM1\ncontacteur", size=7)
    _box(d, 210, 160, 70, 35, "F1\nrelais therm.", size=7)
    _box(d, 310, 155, 90, 45, f"M1 moteur\n{power_kw} kW 400 V", fill=colors.HexColor("#cfe3ff"), size=7)
    for x1, x2 in [(80, 110), (180, 210), (280, 310)]:
        _arrow(d, x1, 177, x2, 177)
    _box(d, 110, 70, 90, 40, f"Automate\n{prefix}-PLC", size=8)
    _arrow(d, 155, 110, 145, 160)
    _box(d, 230, 70, 80, 40, "Pupitre\nvoyants V1–V3", size=7)
    _arrow(d, 200, 90, 230, 90)
    _box(d, 10, 70, 70, 40, "AU\narrêt urgence", size=7)
    _arrow(d, 80, 90, 110, 90)
    d.add(String(220, 25, f"Schéma de principe simplifié — {model}", textAnchor="middle", fontSize=8))
    return d


def exploded(parts):
    """Vue éclatée simplifiée : pièces numérotées alignées sur un axe."""
    d = Drawing(W, H)
    d.add(Line(20, 110, 420, 110, strokeDashArray=[4, 3]))
    step = 400 / len(parts)
    for i, (num, label) in enumerate(parts):
        x = 30 + i * step
        _box(d, x, 90, step - 15, 40, label, size=7)
        d.add(Circle(x + (step - 15) / 2, 165, 10, fillColor=colors.white, strokeColor=colors.black))
        d.add(String(x + (step - 15) / 2, 162, str(num), textAnchor="middle", fontSize=8))
        d.add(Line(x + (step - 15) / 2, 155, x + (step - 15) / 2, 130))
    return d


def thresholds(title, unit, levels):
    """Barre horizontale de seuils (normal / préalarme / arrêt)."""
    d = Drawing(W, 120)
    d.add(String(220, 105, title, textAnchor="middle", fontSize=9))
    lo, hi = levels[0][0], levels[-1][1]
    for start, end, color, label in levels:
        x1 = 20 + (start - lo) / (hi - lo) * 400
        x2 = 20 + (end - lo) / (hi - lo) * 400
        d.add(Rect(x1, 50, x2 - x1, 30, fillColor=LED_COLORS[color], strokeColor=colors.black))
        d.add(String((x1 + x2) / 2, 60, label, textAnchor="middle", fontSize=7, fillColor=colors.white))
        d.add(String(x1, 35, f"{start} {unit}", textAnchor="middle", fontSize=7))
    d.add(String(420, 35, f"{hi} {unit}", textAnchor="middle", fontSize=7))
    return d
