"""Create the downloadable farm report from the saved assessment.

The same plain-language summary feeds the website and this PDF. Downloading a
report never calls a language model or recalculates the assessment.
"""

from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

from cropnova.web.assessment_summary import build_summary, explanation_text

INK = colors.HexColor("#20382c")
MUTED = colors.HexColor("#647062")
LINE = colors.HexColor("#dce1d3")
PAPER = colors.HexColor("#f3f5ed")


def plain(value):
    # Built-in PDF fonts cover these characters consistently without downloads.
    text = (
        str(value)
        .replace("–", "-")
        .replace("—", "-")
        .replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
    )
    return escape(text)


def create_pdf(report, reference=""):
    summary = build_summary(report)
    buffer = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Brand",
            fontName="Times-Bold",
            fontSize=23,
            leading=27,
            textColor=INK,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            fontName="Times-Roman",
            fontSize=25,
            leading=29,
            textColor=INK,
            spaceAfter=9,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            fontName="Times-Bold",
            fontSize=15,
            leading=19,
            textColor=INK,
            spaceBefore=18,
            spaceAfter=9,
            keepWithNext=True,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Text", fontName="Helvetica", fontSize=9, leading=13.5, textColor=INK, spaceAfter=7
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallText",
            fontName="Helvetica",
            fontSize=7.5,
            leading=11,
            textColor=MUTED,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(name="Cell", fontName="Helvetica", fontSize=8, leading=11.5, textColor=INK)
    )
    styles.add(
        ParagraphStyle(
            name="CellHead", fontName="Helvetica-Bold", fontSize=7.5, leading=10.5, textColor=INK
        )
    )
    paragraph = lambda text, style="Text": Paragraph(plain(text), styles[style])
    width = A4[0] - 36 * mm
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="CropNova - Personalised Farm Assessment",
        author="CropNova",
    )
    date = datetime.fromisoformat(summary["created"]).strftime("%d %B %Y, %I:%M %p IST")
    story = [
        paragraph("CropNova", "Brand"),
        paragraph("Your farm assessment", "ReportTitle"),
        paragraph(summary["location"] + " | " + date, "SmallText"),
        paragraph(
            "Reference: " + reference[:10] if reference else "Personalised field assessment",
            "SmallText",
        ),
        Spacer(1, 8),
        paragraph(summary["title"], "SectionTitle"),
        paragraph(
            f"{summary['matches']} crop(s) match the checked conditions. {summary['reviews']} need more information. {summary['attention']} need attention."
        ),
        paragraph(summary["note"], "SmallText"),
        paragraph("Your field details", "SectionTitle"),
    ]
    profile = summary["profile"]
    profile_rows = []
    for index in range(0, len(profile), 2):
        pair = []
        for label, value in profile[index : index + 2]:
            pair.append(
                Paragraph("<b>" + plain(label) + "</b><br/>" + plain(value), styles["Cell"])
            )
        profile_rows.append(pair)
    table = Table(profile_rows, colWidths=[width / 2] * 2, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PAPER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE),
            ]
        )
    )
    story.append(table)
    written = report.get("generative_ai", {})
    if written.get("status") == "generated":
        story.append(paragraph("Your assessment explained", "SectionTitle"))
        for row in written.get("explanations", []):
            # This export uses Latin fonts. Keep native-language explanations on
            # the website instead of producing unreadable missing-glyph boxes.
            english = next(
                (t["text"] for t in row.get("translations", []) if t["language"] == "en"), None
            )
            text = english or (
                row["text"] if report.get("profile", {}).get("language", "en") == "en" else None
            )
            if text:
                story.append(
                    Paragraph(
                        "<b>"
                        + plain(row["crop_id"].title())
                        + "</b> - "
                        + plain(explanation_text(text)),
                        styles["Text"],
                    )
                )
        if report.get("profile", {}).get("language", "en") != "en":
            story.append(
                paragraph(
                    "This PDF contains the English findings. Your chosen-language explanation is available on your saved website page.",
                    "SmallText",
                )
            )
        story.append(
            paragraph(
                "This wording was generated from the assessment evidence. Check the recorded findings and sources before making decisions.",
                "SmallText",
            )
        )
    elif written.get("status") not in {None, "not_requested"}:
        story.extend(
            [
                paragraph("Written explanation", "SectionTitle"),
                paragraph(
                    "The optional written explanation was unavailable. The recorded crop findings and reasons are included below."
                ),
            ]
        )
    source_numbers = {
        source["source_id"]: index + 1 for index, source in enumerate(summary["sources"])
    }
    labels = {"satisfied": "Matches", "violated": "Needs attention", "unknown": "Open question"}
    for candidate in summary["candidates"]:
        story.append(paragraph(candidate["name"] + " - " + candidate["label"], "SectionTitle"))
        story.append(
            paragraph(
                f"{candidate['matched']} of {len(candidate['checks'])} conditions matched. This count is not a probability of crop success.",
                "SmallText",
            )
        )
        rows = [
            [
                paragraph(label, "CellHead")
                for label in [
                    "Condition",
                    "Your entry",
                    "Published reference and reason",
                    "Finding",
                ]
            ]
        ]
        for check in candidate["checks"]:
            citations = ", ".join(
                str(source_numbers[s["source_id"]])
                for s in check["sources"]
                if s["source_id"] in source_numbers
            )
            evidence = "<b>" + plain(check["reference"]) + "</b><br/>" + plain(check["reason"])
            if citations:
                evidence += '<br/><font color="#647062">Sources: ' + citations + "</font>"
            rows.append(
                [
                    paragraph(check["name"], "Cell"),
                    paragraph(check["entered"], "Cell"),
                    Paragraph(evidence, styles["Cell"]),
                    paragraph(labels[check["status"]], "Cell"),
                ]
            )
        checks = Table(
            rows,
            colWidths=[width * 0.14, width * 0.14, width * 0.56, width * 0.16],
            repeatRows=1,
            hAlign="LEFT",
        )
        checks.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), PAPER),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ]
            )
        )
        story.append(checks)
        if candidate["actions"]:
            story.append(Spacer(1, 8))
            story.append(Paragraph("<b>What would help clarify this result?</b>", styles["Text"]))
            for action in candidate["actions"]:
                story.append(paragraph("- " + action))
    story.append(paragraph("Questions still to resolve", "SectionTitle"))
    questions = summary["questions"] or list(
        dict.fromkeys(action for c in summary["candidates"] for action in c["actions"])
    )
    if questions:
        story.extend(paragraph("- " + q) for q in questions)
    else:
        story.append(
            paragraph(
                "No required input questions remain for the checks performed. Local crop variety, weather, drainage and water timing still need confirmation before planting."
            )
        )
    story.append(paragraph("Sources used", "SectionTitle"))
    if not summary["sources"]:
        story.append(paragraph("No applicable published source was available for these checks."))
    for index, source in enumerate(summary["sources"], 1):
        url = source.get("url", "")
        title = plain(source.get("title", "Published source"))
        if url.startswith(("https://", "http://")):
            title = (
                '<link href="'
                + escape(url, {'"': "&quot;"})
                + '" color="#244c38">'
                + title
                + "</link>"
            )
        details = " | ".join(
            str(v)
            for v in [
                source.get("publisher") or source.get("organization"),
                source.get("section"),
                urlparse(url).netloc,
            ]
            if v
        )
        story.append(
            KeepTogether(
                [
                    Paragraph(f"<b>{index}.</b> " + title, styles["Text"]),
                    paragraph(details, "SmallText"),
                ]
            )
        )
    story.extend(
        [
            paragraph("Important context", "SectionTitle"),
            paragraph(summary["water_note"], "SmallText"),
            paragraph(summary["note"], "SmallText"),
        ]
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, "CropNova | Personalised farm assessment")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, "Page " + str(doc.page))
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
