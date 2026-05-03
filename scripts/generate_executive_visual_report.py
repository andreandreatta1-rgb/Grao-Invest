from __future__ import annotations

import json
import math
import shutil
import textwrap
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "executive_reports"
LATEST_PATH = ROOT / "data" / "executive_report_whatsapp_latest.png"
EXECUTIVE_URL = "http://127.0.0.1:8000/api/reports/executive"
DASHBOARD_URL = "http://127.0.0.1:8000/api/dashboard/summary/1"


W, H = 1080, 2860
SCALE = 2
CW, CH = W * SCALE, H * SCALE

COLORS = {
    "bg": (6, 10, 22),
    "panel": (15, 24, 42),
    "panel_2": (10, 18, 34),
    "line": (35, 51, 82),
    "text": (239, 246, 255),
    "muted": (130, 154, 198),
    "dim": (84, 105, 146),
    "cyan": (33, 158, 255),
    "teal": (0, 210, 154),
    "green": (39, 220, 119),
    "red": (255, 86, 106),
    "amber": (250, 174, 45),
    "purple": (165, 129, 255),
    "white": (255, 255, 255),
}


def fetch_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if mono:
        candidates = [
            r"C:\Windows\Fonts\consolab.ttf" if bold else r"C:\Windows\Fonts\consola.ttf",
            r"C:\Windows\Fonts\CascadiaMono.ttf",
        ]
    else:
        candidates = [
            r"C:\Windows\Fonts\bahnschrift.ttf",
            r"C:\Windows\Fonts\seguisb.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size * SCALE)
    return ImageFont.load_default()


FONTS = {
    "title": font(62, bold=True),
    "h1": font(44, bold=True),
    "h2": font(28, bold=True),
    "body": font(23),
    "body_bold": font(23, bold=True),
    "small": font(18),
    "tiny": font(15),
    "metric": font(45, bold=True, mono=True),
    "metric_small": font(29, bold=True, mono=True),
    "mono": font(18, mono=True),
    "mono_bold": font(18, bold=True, mono=True),
}


def s(v: float | int) -> int:
    return int(round(v * SCALE))


def pct(value: Any, digits: int = 1) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return f"{number:+.{digits}f}%".replace(".", ",")


def pct_no_sign(value: Any, digits: int = 1) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return f"{number:.{digits}f}%".replace(".", ",")


def brl(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    return f"R$ {number:.2f}".replace(".", ",")


def short_date(value: Any) -> str:
    raw = str(value or "")
    if len(raw) < 10:
        return "-"
    return f"{raw[8:10]}/{raw[5:7]}/{raw[0:4]}"


def friendly_strategy(case: dict[str, Any]) -> str:
    return f"Compra simulada com alvo e stop | esperado {pct(case.get('expected_financial_pct'), 2)}"


def draw_gradient(draw: ImageDraw.ImageDraw) -> None:
    for y in range(CH):
        t = y / CH
        r = int(5 + 7 * t)
        g = int(10 + 14 * t)
        b = int(24 + 16 * t)
        draw.line([(0, y), (CW, y)], fill=(r, g, b))
    draw.ellipse((s(-220), s(-160), s(520), s(470)), fill=(12, 70, 105, 120))
    draw.ellipse((s(690), s(-80), s(1380), s(560)), fill=(4, 90, 75, 105))


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill, outline=None, width=1, radius=28) -> None:
    draw.rounded_rectangle(box, radius=s(radius), fill=fill, outline=outline, width=s(width))


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, fnt, fill=None, **kwargs) -> None:
    draw.text(xy, value, font=fnt, fill=fill or COLORS["text"], **kwargs)


def wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    value: str,
    fnt,
    max_width: int,
    fill=None,
    line_gap: int = 8,
    max_lines: int | None = None,
) -> int:
    words = str(value or "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=fnt)
        if bbox[2] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".") + "..."
    y = xy[1]
    line_h = draw.textbbox((0, 0), "Ag", font=fnt)[3] + s(line_gap)
    for line in lines:
        draw.text((xy[0], y), line, font=fnt, fill=fill or COLORS["text"])
        y += line_h
    return y


def chip(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, color) -> int:
    pad_x, pad_y = s(16), s(8)
    bbox = draw.textbbox((0, 0), label, font=FONTS["mono_bold"])
    w = bbox[2] - bbox[0] + pad_x * 2
    h = bbox[3] - bbox[1] + pad_y * 2
    rounded(draw, (x, y, x + w, y + h), fill=(*color, 32), outline=(*color, 150), width=1, radius=12)
    draw.text((x + pad_x, y + pad_y - s(1)), label, font=FONTS["mono_bold"], fill=color)
    return x + w + s(12)


def metric_card(draw: ImageDraw.ImageDraw, box, label: str, value: str, sub: str, color) -> None:
    rounded(draw, box, fill=COLORS["panel"], outline=(*color, 170), width=2, radius=26)
    x1, y1, x2, _ = box
    text(draw, (x1 + s(26), y1 + s(24)), label.upper(), FONTS["tiny"], fill=COLORS["muted"])
    text(draw, (x1 + s(26), y1 + s(58)), value, FONTS["metric"], fill=color)
    wrapped(draw, (x1 + s(26), y1 + s(112)), sub, FONTS["small"], x2 - x1 - s(52), fill=COLORS["muted"], max_lines=2)


def method_node(draw: ImageDraw.ImageDraw, x: int, y: int, num: str, title: str, desc: str, color) -> None:
    rounded(draw, (x, y, x + s(184), y + s(160)), fill=COLORS["panel"], outline=COLORS["line"], width=1, radius=22)
    text(draw, (x + s(18), y + s(16)), num, FONTS["metric_small"], fill=(*color[:3], 255))
    text(draw, (x + s(18), y + s(68)), title, FONTS["small"], fill=COLORS["text"])
    wrapped(draw, (x + s(18), y + s(100)), desc, FONTS["tiny"], s(145), fill=COLORS["muted"], line_gap=4, max_lines=2)


def case_card(draw: ImageDraw.ImageDraw, box, case: dict[str, Any], label: str) -> None:
    result = float(case.get("realized_financial_pct") or 0)
    color = COLORS["green"] if result >= 0 else COLORS["red"]
    x1, y1, x2, y2 = box
    rounded(draw, box, fill=COLORS["panel_2"], outline=(*color, 180), width=2, radius=24)
    text(draw, (x1 + s(22), y1 + s(18)), label.upper(), FONTS["tiny"], fill=COLORS["muted"])
    text(draw, (x1 + s(22), y1 + s(50)), str(case.get("instrument", "-")), FONTS["h2"], fill=COLORS["text"])
    text(draw, (x2 - s(172), y1 + s(50)), pct(result, 2), FONTS["metric_small"], fill=color)
    text(draw, (x1 + s(22), y1 + s(96)), friendly_strategy(case), FONTS["small"], fill=COLORS["cyan"])
    y = y1 + s(138)
    rows = [
        ("Entrada", f"{short_date(case.get('entry_date'))} | {brl(case.get('entry_price'))}"),
        ("Alvo", brl(case.get("target_price"))),
        ("Stop", brl(case.get("stop_price"))),
        ("Saida", f"{short_date(case.get('exit_date'))} | {brl(case.get('exit_price'))}"),
    ]
    col_w = (x2 - x1 - s(60)) // 2
    for idx, (k, v) in enumerate(rows):
        cx = x1 + s(22) + (idx % 2) * (col_w + s(14))
        cy = y + (idx // 2) * s(66)
        rounded(draw, (cx, cy, cx + col_w, cy + s(54)), fill=(7, 13, 25), outline=COLORS["line"], radius=12)
        text(draw, (cx + s(12), cy + s(7)), k.upper(), FONTS["tiny"], fill=COLORS["dim"])
        text(draw, (cx + s(12), cy + s(26)), v, FONTS["mono_bold"], fill=COLORS["text"])
    why_y = y + s(142)
    text(draw, (x1 + s(22), why_y), "POR QUE ENTROU", FONTS["tiny"], fill=COLORS["cyan"])
    wrapped(
        draw,
        (x1 + s(22), why_y + s(24)),
        str(case.get("why_entered", "")),
        FONTS["tiny"],
        x2 - x1 - s(44),
        fill=COLORS["muted"],
        max_lines=2,
        line_gap=4,
    )
    learn_y = why_y + s(78)
    rounded(draw, (x1 + s(22), learn_y, x2 - s(22), y2 - s(24)), fill=(0, 210, 154, 18), outline=COLORS["line"], radius=14)
    text(draw, (x1 + s(40), learn_y + s(12)), "APRENDIZADO", FONTS["tiny"], fill=COLORS["amber"])
    wrapped(
        draw,
        (x1 + s(40), learn_y + s(38)),
        str(case.get("learning", "")),
        FONTS["tiny"],
        x2 - x1 - s(80),
        fill=COLORS["text"],
        max_lines=2,
        line_gap=4,
    )


def build_image(executive: dict[str, Any], dashboard: dict[str, Any]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (CW, CH), COLORS["bg"])
    draw = ImageDraw.Draw(img, "RGBA")
    draw_gradient(draw)

    now = datetime.now(timezone.utc).astimezone()
    generated_label = now.strftime("%d/%m/%Y %H:%M")
    overview = dashboard.get("thesis_history_overview") or {}
    kpis = executive.get("kpis") or {}
    evo = executive.get("evolution") or {}
    last7 = evo.get("last_7_days") or {}
    cases = (executive.get("learning_evolution") or {}).get("cases") or []

    margin = s(56)
    text(draw, (margin, s(52)), "GRAO INVEST", FONTS["body_bold"], fill=COLORS["teal"])
    text(draw, (margin, s(86)), f"Reporte executivo | {generated_label}", FONTS["small"], fill=COLORS["muted"])
    rounded(draw, (s(830), s(54), s(1024), s(104)), fill=(250, 174, 45, 35), outline=(*COLORS["amber"], 120), radius=18)
    text(draw, (s(858), s(69)), "SIMULACAO", FONTS["mono_bold"], fill=COLORS["amber"])

    y = s(150)
    text(draw, (margin, y), "Do teste ao aprendizado", FONTS["title"], fill=COLORS["text"])
    y += s(80)
    wrapped(
        draw,
        (margin, y),
        "Avaliamos teses historicas, simulamos operacoes, fazemos pos-morte e transformamos o aprendizado em criterio para a proxima decisao.",
        FONTS["body"],
        s(910),
        fill=COLORS["muted"],
        line_gap=8,
        max_lines=3,
    )
    y += s(130)
    x = margin
    x = chip(draw, x, y, f"{int(overview.get('total_tested') or 0)} teses avaliadas", COLORS["cyan"])
    x = chip(draw, x, y, f"{pct_no_sign(overview.get('success_rate_pct'), 1)} sucesso", COLORS["green"])
    chip(draw, x, y, f"{int(last7.get('sample_count') or 0)} exercicios/7d", COLORS["purple"])

    y += s(86)
    card_w = s(462)
    metric_card(draw, (margin, y, margin + card_w, y + s(168)), "Resultado medio", pct(overview.get("expectancy_net_pct"), 2), "Media por tese resolvida", COLORS["teal"])
    metric_card(draw, (margin + card_w + s(36), y, margin + card_w * 2 + s(36), y + s(168)), "Taxa de sucesso", pct_no_sign(overview.get("success_rate_pct"), 2), f"{int(overview.get('success_count') or 0)} de {int(overview.get('total_tested') or 0)}", COLORS["green"])

    y += s(210)
    text(draw, (margin, y), "Como o motor evolui", FONTS["h1"], fill=COLORS["text"])
    y += s(56)
    nodes = [
        ("01", "Mercado", "preco, volume, noticias", COLORS["cyan"]),
        ("02", "Tese", "hipotese testavel", COLORS["amber"]),
        ("03", "Operacao", "entrada, alvo, stop", COLORS["teal"]),
        ("04", "Pos-morte", "erro e acerto viram regra", COLORS["purple"]),
        ("05", "Monitor", "teses abertas no dia", COLORS["green"]),
    ]
    nx = margin
    for idx, item in enumerate(nodes):
        method_node(draw, nx, y, *item)
        if idx < len(nodes) - 1:
            ax = nx + s(186)
            ay = y + s(80)
            draw.line((ax, ay, ax + s(32), ay), fill=(*COLORS["line"], 255), width=s(3))
            draw.polygon([(ax + s(32), ay), (ax + s(18), ay - s(8)), (ax + s(18), ay + s(8))], fill=COLORS["line"])
        nx += s(196)

    y += s(216)
    text(draw, (margin, y), "Pos-morte na pratica", FONTS["h1"], fill=COLORS["text"])
    y += s(50)
    case_h = s(488)
    for idx, case in enumerate(cases[:3]):
        case_card(draw, (margin, y, s(1024), y + case_h), case, f"Tese {chr(65 + idx)}")
        y += case_h + s(26)

    conclusion = (executive.get("learning_evolution") or {}).get("conclusion") or ""
    conclusion_h = s(132)
    rounded(draw, (margin, y, s(1024), y + conclusion_h), fill=(0, 210, 154, 24), outline=(*COLORS["teal"], 140), radius=24)
    text(draw, (margin + s(24), y + s(18)), "Conclusao executiva", FONTS["body_bold"], fill=COLORS["teal"])
    wrapped(draw, (margin + s(24), y + s(52)), conclusion, FONTS["small"], s(880), fill=COLORS["text"], max_lines=3)

    y += conclusion_h + s(42)
    draw.line((margin, y, s(1024), y), fill=(*COLORS["line"], 255), width=s(2))
    wrapped(
        draw,
        (margin, y + s(24)),
        "Conteudo analitico e educacional. Nao constitui recomendacao de investimento. Operacoes simuladas.",
        FONTS["tiny"],
        s(900),
        fill=COLORS["dim"],
        max_lines=2,
    )

    img = img.resize((W, H), Image.Resampling.LANCZOS)
    out = OUT_DIR / f"executive_report_whatsapp_{now.strftime('%Y%m%d_%H%M%S')}.png"
    img.save(out, quality=95)
    shutil.copyfile(out, LATEST_PATH)
    return out


def main() -> None:
    executive = fetch_json(EXECUTIVE_URL)
    dashboard = fetch_json(DASHBOARD_URL)
    out = build_image(executive, dashboard)
    print(out)
    print(LATEST_PATH)


if __name__ == "__main__":
    main()
