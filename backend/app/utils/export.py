"""Word document export for newsletters using python-docx.

The layout follows UCM's requests from the 2026-11-18 Builder session (#536):
an AP-style date under the title, 14 pt body text, section headings that are
plain styled paragraphs rather than Word headings (so Word shows no
collapse arrow), a tight one-line-per-job list, and no footer line. The file
is marked as a current-format Word document so Word does not open it in
Compatibility Mode (#535).
"""

import io
from datetime import date

from docx import Document
from docx.document import Document as DocumentObject
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from docx.text.paragraph import Paragraph

from app.utils.ap_dates import ap_date
from app.utils.body_links import parse_body

LINK_COLOR = "0056B3"
NO_EVENTS_TEXT = "No events."

BODY_SIZE = Pt(14)
DATE_SIZE = Pt(14)
SECTION_HEADING_SIZE = Pt(16)
SECTION_HEADING_STYLE = "UCM Section Heading"
GOLD = RGBColor(0xB5, 0x8A, 0x2A)
DARK_GOLD = RGBColor(0x8C, 0x6E, 0x1A)

# Word 2013 and later. python-docx's template says 14 (Word 2010), which
# opens in Compatibility Mode and blocks sensitivity labels (#535).
WORD_COMPATIBILITY_MODE = "15"
_WORD_COMPAT_URI = "http://schemas.microsoft.com/office/word"


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
            - empty_text (optional): shown under the heading when there are
              no items; sections with neither are left out
            - compact (optional): list items one per line with no blank
              lines or paragraph spacing between them (job listings)

    Returns:
        BytesIO buffer containing the .docx file
    """
    doc = Document()
    _set_compatibility_mode(doc, WORD_COMPATIBILITY_MODE)

    # Styles
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = BODY_SIZE
    _add_section_heading_style(doc)

    # Title. The Title style carries no outline level, so it has no
    # collapse arrow in Word.
    title_text = (
        "The Daily Register" if newsletter_type == "tdr" else "My UI"
    )
    title = doc.add_heading(title_text, level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.color.rgb = GOLD

    # Date line
    date_para = doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_run = date_para.add_run(ap_date(publish_date))
    date_run.font.size = DATE_SIZE
    date_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    doc.add_paragraph()  # Spacer

    for section in sections:
        if not section.get("items") and not section.get("empty_text"):
            continue

        doc.add_paragraph(section["name"], style=SECTION_HEADING_STYLE)

        if not section.get("items"):
            doc.add_paragraph(section["empty_text"])
            doc.add_paragraph()  # Spacer
            continue

        compact = bool(section.get("compact"))

        # Items
        for item in section["items"]:
            headline = item["Final_Headline"]
            body = item["Final_Body"]

            if headline:
                # Jobs are body-only linked lines; other items retain a bold headline.
                h_para = doc.add_paragraph()
                h_run = h_para.add_run(headline)
                h_run.bold = True
                h_run.font.size = BODY_SIZE
                if compact:
                    _remove_paragraph_spacing(h_para)

            body_para = _add_body_with_links(doc, body)

            if compact:
                _remove_paragraph_spacing(body_para)
            else:
                doc.add_paragraph()  # Spacer between items

        if compact:
            doc.add_paragraph()  # One spacer after the list, before the next section

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def _set_compatibility_mode(doc: DocumentObject, mode: str) -> None:
    """Set Word's compatibilityMode compat setting in word/settings.xml."""
    settings = doc.settings.element
    compat = settings.find(qn("w:compat"))
    if compat is None:
        compat = OxmlElement("w:compat")
        settings.append(compat)
    for setting in compat.findall(qn("w:compatSetting")):
        if setting.get(qn("w:name")) == "compatibilityMode":
            setting.set(qn("w:val"), mode)
            return
    setting = OxmlElement("w:compatSetting")
    setting.set(qn("w:name"), "compatibilityMode")
    setting.set(qn("w:uri"), _WORD_COMPAT_URI)
    setting.set(qn("w:val"), mode)
    compat.append(setting)


def _add_section_heading_style(doc: DocumentObject) -> None:
    """Add the section heading paragraph style.

    It looks like the old Heading 1 (bold, dark gold, heading font, space
    above, kept with the next line) but is a plain paragraph style with no
    outline level, so Word shows no collapse arrow beside it (#536).
    """
    heading_style = doc.styles.add_style(SECTION_HEADING_STYLE, WD_STYLE_TYPE.PARAGRAPH)
    heading_style.base_style = doc.styles['Normal']
    heading_style.next_paragraph_style = doc.styles['Normal']
    heading_style.font.bold = True
    heading_style.font.size = SECTION_HEADING_SIZE
    heading_style.font.color.rgb = DARK_GOLD
    fmt = heading_style.paragraph_format
    fmt.space_before = Pt(24)
    fmt.space_after = Pt(0)
    fmt.keep_with_next = True
    fmt.keep_together = True

    # Use the theme heading font, as Heading 1 did.
    r_fonts = heading_style.element.get_or_add_rPr().get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        r_fonts.attrib.pop(qn(attr), None)
    r_fonts.set(qn("w:asciiTheme"), "majorHAnsi")
    r_fonts.set(qn("w:hAnsiTheme"), "majorHAnsi")
    r_fonts.set(qn("w:eastAsiaTheme"), "majorEastAsia")
    r_fonts.set(qn("w:cstheme"), "majorBidi")


def _remove_paragraph_spacing(paragraph: Paragraph) -> None:
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)


def _add_body_with_links(doc: DocumentObject, body: str) -> Paragraph:
    """Add body text, turning each inline link into a clickable Word hyperlink."""
    para = doc.add_paragraph()
    for segment in parse_body(body):
        if segment.href:
            _add_hyperlink(para, segment.href, segment.text)
        else:
            run = para.add_run(segment.text)
            run.font.size = BODY_SIZE
    return para


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
    # w:sz is in half-points.
    half_points = str(int(BODY_SIZE.pt * 2))
    for tag, value in (("w:color", LINK_COLOR), ("w:sz", half_points), ("w:u", "single")):
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
