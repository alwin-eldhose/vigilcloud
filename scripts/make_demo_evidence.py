"""Build the demo evidence files: PDF packets, Word documents, and an architecture diagram.

    uv run python scripts/make_demo_evidence.py

Outputs
    samples/*.pdf                         one-click samples used by the app
    demo_evidence/*.docx, *.png           files to upload by hand in the demo

The text comes from the Markdown sources next to them. Re-run after editing a source.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SAMPLES = ROOT / "samples"
DEMO = ROOT / "demo_evidence"
SOURCE = DEMO / "source"

NAVY = colors.HexColor("#14213d")
SLATE = colors.HexColor("#5b6b8c")
RULE = colors.HexColor("#c8d0e0")

META_KEYS = ("Vendor name", "Product", "Review date", "Packet date", "Respondent", "Prepared by")

BRIGHTPATH_APPENDIX = [
    ("Subprocessor", "Service", "Location"),
    ("Northwind Cloud", "Cloud hosting provider", "Frankfurt, DE"),
    ("MailRelay", "Email delivery service", "Dublin, IE"),
    ("PayGate Files", "Payment file gateway", "Frankfurt, DE"),
    ("HelpDeskly", "Support ticketing tool", "Amsterdam, NL"),
]


def clean(text: str) -> str:
    return text.replace("`", "").replace("**", "").strip()


def parse_source(path: Path) -> dict:
    """Split a Markdown source into a title, metadata, and a list of blocks."""
    title = ""
    meta: dict[str, str] = {}
    blocks: list[tuple[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("# "):
            title = clean(line[2:])
        elif line.startswith("## "):
            blocks.append(("h2", clean(line[3:])))
        elif line.startswith("- "):
            blocks.append(("bullet", clean(line[2:])))
        else:
            key = line.split(":", 1)[0]
            if key in META_KEYS and ":" in line:
                meta[key] = clean(line.split(":", 1)[1])
            else:
                blocks.append(("p", clean(line)))
    return {"title": title, "meta": meta, "blocks": blocks}


# ---------------------------------------------------------------- PDF packets


def build_pdf(source: Path, target: Path, classification: str, appendix: list[tuple[str, ...]] | None = None) -> None:
    doc_data = parse_source(source)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=20, leading=25, textColor=NAVY, alignment=0, spaceAfter=4)
    kicker = ParagraphStyle("K", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9, textColor=SLATE, spaceAfter=10)
    h2 = ParagraphStyle("H", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=NAVY, spaceBefore=14, spaceAfter=5)
    body = ParagraphStyle("B", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.5, leading=15, spaceAfter=6)
    small = ParagraphStyle("S", parent=body, fontSize=9, textColor=SLATE)

    vendor = doc_data["meta"].get("Vendor name", "Vendor")

    def footer(canvas, doc):  # noqa: ANN001
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.line(0.8 * inch, 0.7 * inch, letter[0] - 0.8 * inch, 0.7 * inch)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(SLATE)
        canvas.drawString(0.8 * inch, 0.5 * inch, f"{vendor}  |  {classification}")
        canvas.drawRightString(letter[0] - 0.8 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()

    story: list = [Paragraph(escape(classification.upper()), kicker), Paragraph(escape(doc_data["title"]), title), Spacer(1, 6)]

    if doc_data["meta"]:
        rows = [[Paragraph(f"<b>{escape(key)}</b>", small), Paragraph(escape(value), small)] for key, value in doc_data["meta"].items()]
        table = Table(rows, colWidths=[1.5 * inch, 5.2 * inch])
        table.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f2f5fb")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story += [table, Spacer(1, 8)]

    bullets: list[str] = []

    def flush() -> None:
        if bullets:
            story.append(ListFlowable([ListItem(Paragraph(escape(item), body), leftIndent=14) for item in bullets], bulletType="bullet", start="•", leftIndent=14))
            bullets.clear()

    for kind, text in doc_data["blocks"]:
        if kind == "bullet":
            bullets.append(text)
            continue
        flush()
        story.append(Paragraph(escape(text), h2 if kind == "h2" else body))
    flush()

    if appendix:
        story.append(Paragraph("Appendix B. Subprocessors", h2))
        table = Table([[Paragraph(escape(cell), small) for cell in row] for row in appendix], colWidths=[2.0 * inch, 2.6 * inch, 2.1 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6ecf8")),
            ("GRID", (0, 0), (-1, -1), 0.4, RULE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)

    SimpleDocTemplate(
        str(target), pagesize=letter, leftMargin=0.8 * inch, rightMargin=0.8 * inch,
        topMargin=0.8 * inch, bottomMargin=0.9 * inch, title=doc_data["title"], author=vendor,
    ).build(story, onFirstPage=footer, onLaterPages=footer)
    print("wrote", target.relative_to(ROOT))


# ---------------------------------------------------------------- Word files


def build_docx_packet(source: Path, target: Path, classification: str) -> None:
    data = parse_source(source)
    document = Document()
    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    label = document.add_paragraph(classification.upper())
    label.runs[0].font.size = Pt(9)
    label.runs[0].font.bold = True
    label.runs[0].font.color.rgb = RGBColor(0x5B, 0x6B, 0x8C)
    document.add_heading(data["title"], level=0)
    for kind, text in data["blocks"]:
        if kind == "h2":
            document.add_heading(text, level=1)
        elif kind == "bullet":
            document.add_paragraph(text, style="List Bullet")
        else:
            document.add_paragraph(text)
    section = document.sections[0]
    footer = section.footer.paragraphs[0]
    footer.text = f"{data['title'].split('—')[0].strip()}  |  {classification}"
    footer.alignment = WD_ALIGN_PARAGRAPH.LEFT
    document.save(target)
    print("wrote", target.relative_to(ROOT))


def build_docx_questionnaire(target: Path, vendor: str, items: list[tuple[str, str]]) -> None:
    document = Document()
    document.styles["Normal"].font.name = "Calibri"
    document.styles["Normal"].font.size = Pt(11)
    document.add_heading(f"Vendor Security Questionnaire. {vendor}", level=0)
    document.add_paragraph(
        "These statements were supplied by the vendor in response to our third-party security review. "
        "Each one is a claim to be checked against the evidence packet."
    )
    document.add_paragraph("")
    for number, (label, claim) in enumerate(items, start=1):
        document.add_paragraph(f"Q{number} ({label}): {claim}")
        document.add_paragraph("")
    document.save(target)
    print("wrote", target.relative_to(ROOT))


# ---------------------------------------------------------------- Diagram


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in ("/System/Library/Fonts/Helvetica.ttc", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size, index=1 if bold and candidate.endswith(".ttc") else 0)
            except OSError:
                continue
    return ImageFont.load_default(size=size)


def build_diagram(target: Path) -> None:
    width, height = 1800, 1120
    image = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(image)
    ink, grey = "#14213d", "#5b6b8c"
    red, amber = "#c62828", "#d9822b"

    def centered(box: tuple[int, int, int, int], text: str, size: int = 26, fill: str = ink, bold: bool = False) -> None:
        lines = text.split("\n")
        fnt = font(size, bold)
        line_height = size + 8
        top = box[1] + (box[3] - box[1] - line_height * len(lines)) / 2
        for index, line in enumerate(lines):
            line_width = draw.textlength(line, font=fnt)
            draw.text((box[0] + (box[2] - box[0] - line_width) / 2, top + index * line_height), line, font=fnt, fill=fill)

    def zone(box: tuple[int, int, int, int], label: str, tint: str) -> None:
        draw.rounded_rectangle(box, radius=24, fill=tint, outline="#aab4c8", width=3)
        draw.text((box[0] + 24, box[1] + 16), label, font=font(28, True), fill=grey)

    def node(box: tuple[int, int, int, int], text: str, outline: str = ink, fill: str = "#ffffff", dashed: bool = False, size: int = 26) -> None:
        if dashed:
            x1, y1, x2, y2 = box
            for x in range(x1, x2, 28):
                draw.line([(x, y1), (min(x + 14, x2), y1)], fill=outline, width=4)
                draw.line([(x, y2), (min(x + 14, x2), y2)], fill=outline, width=4)
            for y in range(y1, y2, 28):
                draw.line([(x1, y), (x1, min(y + 14, y2))], fill=outline, width=4)
                draw.line([(x2, y), (x2, min(y + 14, y2))], fill=outline, width=4)
            draw.rectangle(box, fill=fill, outline=None)
            for x in range(x1, x2, 28):
                draw.line([(x, y1), (min(x + 14, x2), y1)], fill=outline, width=4)
                draw.line([(x, y2), (min(x + 14, x2), y2)], fill=outline, width=4)
            for y in range(y1, y2, 28):
                draw.line([(x1, y), (x1, min(y + 14, y2))], fill=outline, width=4)
                draw.line([(x2, y), (x2, min(y + 14, y2))], fill=outline, width=4)
        else:
            draw.rounded_rectangle(box, radius=14, fill=fill, outline=outline, width=4)
        centered(box, text, size)

    def arrow(start: tuple[int, int], end: tuple[int, int], color: str = ink, label: str = "", label_at: tuple[int, int] | None = None) -> None:
        draw.line([start, end], fill=color, width=5)
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = max((dx * dx + dy * dy) ** 0.5, 1)
        ux, uy = dx / length, dy / length
        left = (end[0] - 24 * ux + 12 * uy, end[1] - 24 * uy - 12 * ux)
        right = (end[0] - 24 * ux - 12 * uy, end[1] - 24 * uy + 12 * ux)
        draw.polygon([end, left, right], fill=color)
        if label:
            at = label_at or ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2 - 36)
            draw.text(at, label, font=font(22), fill=color)

    draw.text((40, 30), "Brightpath Ledger. Production architecture and data flow (v3.2)", font=font(40, True), fill=ink)
    draw.text((40, 84), "Prepared by Trust and Compliance  |  2026-10-30  |  Confidential", font=font(24), fill=grey)

    zone((40, 150, 320, 1010), "Customer side", "#f4f7fc")
    zone((370, 150, 1270, 1010), "Brightpath EU region (Frankfurt)", "#eef6f1")
    zone((1330, 150, 1770, 590), "Third parties", "#f7f4fb")
    zone((1330, 640, 1770, 1010), "US-East region (Virginia)", "#fcf3ec")

    node((70, 250, 290, 390), "Customer ERP\nbank and\ninvoice files")
    node((70, 560, 290, 720), "Partner bank\nclient\n(legacy)")

    node((420, 250, 720, 390), "API gateway\nTLS 1.2 or newer")
    node((800, 250, 1080, 390), "Reconciliation\nworkers")
    node((800, 470, 1080, 610), "Ledger database\nAES-256 at rest")
    node((1100, 470, 1255, 610), "Support\nattachments", size=21)
    node((420, 560, 720, 720), "Partner SFTP\nendpoint\nTLS 1.0 still accepted\nretire Q1 2027", outline=amber)
    node((420, 810, 720, 950), "Nightly analytics\nextract job")
    node((800, 780, 1250, 960), "Staging bucket\nbp-staging-extracts\n30-day retention\nServer-side encryption: NOT enabled", outline=red, fill="#fdecec")

    for index, name in enumerate(("Cloud hosting provider", "Payment file gateway", "Email delivery service", "Support ticketing tool")):
        top = 215 + index * 66
        node((1360, top, 1740, top + 56), name)
    node((1350, 490, 1750, 578), "Observability vendor (TraceLens)\nnot listed in Appendix B", outline=red, fill="#fdecec", dashed=True, size=23)

    node((1370, 740, 1730, 920), "Support attachment replica\nBoston support team\nnot in residency statement", outline=red, fill="#fdecec")

    arrow((290, 320), (420, 320), label="HTTPS", label_at=(310, 280))
    arrow((290, 640), (420, 640), amber, label="SFTP", label_at=(310, 600))
    arrow((720, 320), (800, 320))
    arrow((940, 390), (940, 470))
    arrow((820, 610), (640, 810), label="nightly export", label_at=(748, 722))
    arrow((720, 880), (800, 880), red)
    arrow((1080, 300), (1360, 309), label="payment files", label_at=(1150, 262))
    arrow((1080, 360), (1350, 520), red, label="application traces", label_at=(1150, 356))
    arrow((1250, 610), (1370, 800), red, label="replicated", label_at=(1135, 660))

    legend_y = 1050
    draw.rectangle((40, legend_y, 70, legend_y + 26), outline=red, width=4)
    draw.text((82, legend_y - 2), "control gap", font=font(24), fill=ink)
    draw.rectangle((280, legend_y, 310, legend_y + 26), outline=amber, width=4)
    draw.text((322, legend_y - 2), "known exception", font=font(24), fill=ink)

    image.save(target)
    print("wrote", target.relative_to(ROOT))


def main() -> None:
    DEMO.mkdir(exist_ok=True)
    build_pdf(SAMPLES / "high_risk_etl_vendor.md", SAMPLES / "high_risk_etl_vendor.pdf", "Vendor response. Confidential")
    build_pdf(SAMPLES / "compliant_identity_vendor.md", SAMPLES / "compliant_identity_vendor.pdf", "Vendor response. Confidential")
    build_pdf(SAMPLES / "subtle_discrepancy_vendor.md", SAMPLES / "subtle_discrepancy_vendor.pdf", "Vendor security packet. Confidential under NDA", BRIGHTPATH_APPENDIX)

    build_diagram(DEMO / "brightpath_architecture_diagram.png")

    from sample_catalog import SUBTLE_CLAIMS

    labels = ["Encryption at rest", "Encryption in transit", "Multi-factor authentication", "Data residency", "Subprocessors",
              "Penetration testing", "Access reviews", "Audit logging", "Incident response", "Assurance report"]
    claims = [line.strip() for line in SUBTLE_CLAIMS.splitlines() if line.strip()]
    build_docx_questionnaire(DEMO / "brightpath_questionnaire.docx", "Brightpath Reconciliation Ltd.", list(zip(labels, claims)))

    build_docx_packet(SOURCE / "northstar_security_packet.md", DEMO / "northstar_security_packet.docx", "Security and architecture evidence. Confidential")
    north = (SOURCE / "northstar_questionnaire.md").read_text(encoding="utf-8")
    north_labels = re.findall(r"\*\*Q\d+ \((.+?)\):\*\*", north)
    from inference_verifier import parse_claims

    north_claims = parse_claims(north)
    build_docx_questionnaire(DEMO / "northstar_questionnaire.docx", "NorthStar Data Pulse", list(zip(north_labels, north_claims)))


if __name__ == "__main__":
    main()
