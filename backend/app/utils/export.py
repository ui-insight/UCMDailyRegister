"""Word document export for newsletters using python-docx."""

import io
from datetime import date

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from docx.text.paragraph import Paragraph

from app.utils.body_links import parse_body

LINK_COLOR = "0056B3"


def export_newsletter_docx(
    newsletter_type: str,
    publish_date: date,
    sections: list[dict],
) -> io.BytesIO:
    """Generate a Word document for a newsletter.

    Args:
        newsletter_type: "tdr" or "myui"
        publish_date: The publish date
        sections: List of section dicts, each with:
            - name: Section name
            - items: List of item dicts with 'Final_Headline', 'Final_Body'

    Returns:
        BytesIO buffer containing the .docx file
    """
    doc = Document()

    # Styles
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)

    # Title
    title_text = (
        "The Daily Register" if newsletter_type == "tdr" else "My UI"
    )
    title = doc.add_heading(title_text, level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.color.rgb = RGBColor(0xB5, 0x8A, 0x2A)  # Gold

    # Date line
    date_para = doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_run = date_para.add_run(publish_date.strftime("%A, %B %d, %Y"))
    date_run.font.size = Pt(12)
    date_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    doc.add_paragraph()  # Spacer

    for section in sections:
        if not section.get("items"):
            continue

        # Section heading
        heading = doc.add_heading(section["name"], level=1)
        for run in heading.runs:
            run.font.color.rgb = RGBColor(0x8C, 0x6E, 0x1A)  # Dark gold

        # Items
        for item in section["items"]:
            headline = item["Final_Headline"]
            body = item["Final_Body"]

            if headline:
                # Jobs are body-only linked lines; other items retain a bold headline.
                h_para = doc.add_paragraph()
                h_run = h_para.add_run(headline)
                h_run.bold = True
                h_run.font.size = Pt(11)

            _add_body_with_links(doc, body)

            doc.add_paragraph()  # Spacer between items

    # Footer
    doc.add_paragraph()
    footer_para = doc.add_paragraph()
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer_para.add_run(
        "University of Idaho | University Communications and Marketing"
    )
    footer_run.font.size = Pt(9)
    footer_run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def _add_body_with_links(doc: Document, body: str) -> None:
    """Add body text, turning each inline link into a clickable Word hyperlink."""
    para = doc.add_paragraph()
    for segment in parse_body(body):
        if segment.href:
            _add_hyperlink(para, segment.href, segment.text)
        else:
            run = para.add_run(segment.text)
            run.font.size = Pt(11)


def _add_hyperlink(paragraph: Paragraph, url: str, text: str) -> None:
    """Append ``text`` as an external hyperlink to ``url``.

    python-docx has no hyperlink API, so this writes the w:hyperlink element
    and its relationship directly; the destination lives in the relationship.
    """
    rel_id = paragraph.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), rel_id)

    run = OxmlElement("w:r")
    run_props = OxmlElement("w:rPr")
    # Child order follows the WordprocessingML schema: color, sz, u.
    for tag, value in (("w:color", LINK_COLOR), ("w:sz", "22"), ("w:u", "single")):
        prop = OxmlElement(tag)
        prop.set(qn("w:val"), value)
        run_props.append(prop)
    run.append(run_props)

    for index, line in enumerate(text.split("\n")):
        if index:
            run.append(OxmlElement("w:br"))
        text_el = OxmlElement("w:t")
        text_el.set(qn("xml:space"), "preserve")
        text_el.text = line
        run.append(text_el)

    hyperlink.append(run)
    paragraph._p.append(hyperlink)
