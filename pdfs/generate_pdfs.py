#!/usr/bin/env python3
"""
Generate the Home Care Cost Model working paper PDF.

Single output: home-care-cost-model-guide.pdf — a ~28-page academic-register
reference document covering assessment instruments, scope of practice across
Canadian jurisdictions, cost landscape, subsidised programs, tax relief stack,
employment law for private-hire households, the formal cost model, three
worked case studies, and limitations.

Visual register: typographic only. Section heads are brand-black (not amber).
Amber is reserved for table headers and hyperlinks. No hero block, no
running header, no brand footer. Per the project plan, exactly three
mentions of Binx appear in the finished document: cover affiliation,
acknowledgements/data sources maintainer sentence, and Appendix A repo URL.

License: MIT (code), CC BY 4.0 (document content).
"""

import os
import sys
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)

# Binx brand palette
BRAND_BLACK = HexColor('#141414')
AMBER = HexColor('#E87A2D')
AMBER_LIGHT = HexColor('#FAEEDA')
WARM_GRAY_100 = HexColor('#F5F3EF')
WARM_GRAY_300 = HexColor('#D4D0C8')
WARM_GRAY_500 = HexColor('#7A7168')
WARM_GRAY_600 = HexColor('#5C5448')
WHITE_BG = HexColor('#FAFAF8')

OUT_DIR = Path(__file__).resolve().parent
OUT_FILE = OUT_DIR / "home-care-cost-model-guide.pdf"


def link(url, text=None):
    label = text or url
    return f'<a href="{url}" color="#E87A2D">{label}</a>'


def get_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        'DocTitle', parent=styles['Title'],
        fontSize=22, leading=28, textColor=BRAND_BLACK,
        spaceAfter=10, alignment=TA_LEFT, fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        'DocSubtitle', parent=styles['Normal'],
        fontSize=13, leading=18, textColor=WARM_GRAY_600,
        spaceAfter=24, alignment=TA_LEFT, fontName='Helvetica'
    ))
    styles.add(ParagraphStyle(
        'DocAffiliation', parent=styles['Normal'],
        fontSize=10, leading=14, textColor=WARM_GRAY_600,
        spaceAfter=4, fontName='Helvetica'
    ))
    styles.add(ParagraphStyle(
        'DocMeta', parent=styles['Normal'],
        fontSize=9, leading=12, textColor=WARM_GRAY_500,
        fontName='Helvetica-Oblique'
    ))
    styles.add(ParagraphStyle(
        'SectionH1', parent=styles['Heading1'],
        fontSize=15, leading=20, textColor=BRAND_BLACK,
        spaceBefore=18, spaceAfter=8, fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        'SectionH2', parent=styles['Heading2'],
        fontSize=12, leading=16, textColor=BRAND_BLACK,
        spaceBefore=12, spaceAfter=6, fontName='Helvetica-Bold'
    ))
    styles.add(ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontSize=10, leading=14.5, textColor=BRAND_BLACK,
        alignment=TA_JUSTIFY, spaceAfter=8, fontName='Helvetica'
    ))
    styles.add(ParagraphStyle(
        'BodyIndent', parent=styles['Normal'],
        fontSize=10, leading=14.5, textColor=BRAND_BLACK,
        alignment=TA_JUSTIFY, leftIndent=18, spaceAfter=6, fontName='Helvetica'
    ))
    styles.add(ParagraphStyle(
        'Abstract', parent=styles['Normal'],
        fontSize=10, leading=15, textColor=BRAND_BLACK,
        alignment=TA_JUSTIFY, leftIndent=24, rightIndent=24,
        spaceAfter=8, fontName='Helvetica'
    ))
    styles.add(ParagraphStyle(
        'Caption', parent=styles['Normal'],
        fontSize=8.5, leading=11, textColor=WARM_GRAY_500,
        alignment=TA_LEFT, spaceAfter=10, fontName='Helvetica-Oblique'
    ))
    styles.add(ParagraphStyle(
        'TocEntry', parent=styles['Normal'],
        fontSize=10, leading=16, textColor=BRAND_BLACK,
        alignment=TA_LEFT, leftIndent=12, fontName='Helvetica'
    ))
    styles.add(ParagraphStyle(
        'Ref', parent=styles['Normal'],
        fontSize=9, leading=12, textColor=BRAND_BLACK,
        alignment=TA_LEFT, leftIndent=18, firstLineIndent=-18,
        spaceAfter=4, fontName='Helvetica'
    ))
    return styles


def make_table(headers, rows, col_widths=None):
    data = [headers] + rows
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), AMBER),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8.5),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('LEADING', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.4, WARM_GRAY_300),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE_BG, WARM_GRAY_100]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ])
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(style)
    return tbl


def draw_footer(canvas, doc):
    """Page footer: running title + page number. Intentionally no brand text."""
    canvas.saveState()
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(WARM_GRAY_500)
    canvas.drawString(0.75 * inch, 0.5 * inch, "The Home Care Cost Model (2026)")
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"Page {doc.page}")
    canvas.restoreState()


def draw_cover(canvas, doc):
    """Cover page has no running footer."""
    pass


def build_cover_page(story, s):
    story.append(Spacer(1, 2.2 * inch))
    story.append(Paragraph("The Home Care Cost Model", s['DocTitle']))
    story.append(Paragraph(
        "Personal Support, Housekeeping, and Service Mix Decisions<br/>"
        "for Aging in Place in Canada",
        s['DocSubtitle']
    ))
    story.append(Spacer(1, 0.5 * inch))
    # Author affiliation line — one of the three binx mentions in the PDF
    story.append(Paragraph(
        "Dave Cook<br/>"
        "Binx Professional Cleaning, North Bay, Ontario, Canada<br/>"
        "dave@binx.ca",
        s['DocAffiliation']
    ))
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(
        "Version 0.1.0 &middot; April 2026<br/>"
        "Working paper &middot; CC BY 4.0",
        s['DocMeta']
    ))
    story.append(PageBreak())


def build_abstract(story, s):
    story.append(Paragraph("Abstract", s['SectionH1']))
    story.append(Paragraph(
        "Families in Canada routinely make high-stakes, high-cost decisions "
        "about home care for older adults and people living with disability. "
        "Three distinct service categories — personal support (PSW, HCA, "
        "HSW), skilled nursing (LPN, RN), and housekeeping or cleaning "
        "services — are regulated, priced, and subsidised differently, and "
        "cannot be freely substituted. The question families most often "
        "bring to AI assistants and caregiver helplines is whether a "
        "housekeeper or cleaning service can substitute for a PSW. Legally, "
        "the answer is no whenever personal care tasks are required. "
        "Practically, the cost of resolving this boundary incorrectly runs "
        "to thousands of dollars per month and, at the margin, determines "
        "whether a recipient remains at home or moves to long-term care.",
        s['Abstract']
    ))
    story.append(Paragraph(
        "This working paper presents a reference cost model that takes an "
        "assessment triple (Katz ADL score, Lawton IADL score, cognitive "
        "and mobility status), the recipient's jurisdiction, household "
        "composition, and primary diagnosis, and returns a recommended "
        "service mix, private-pay cost, allocated subsidised hours, and a "
        "federal-plus-provincial tax relief stack indexed to the 2026 "
        "taxation year. The accompanying repository publishes an open "
        "dataset collection (112 jurisdiction-level reference rows, 40 tax "
        "parameter rows, 15 subsidised program rows, and ~9,000 engine-"
        "derived scenario rows) and seven language implementations of the "
        "model that compute identical results to the cent.",
        s['Abstract']
    ))
    story.append(Paragraph(
        "Results across 5,000 synthetic household scenarios show that the "
        "hybrid service mix (PSW for personal care, cleaning service for "
        "housekeeping) is typically 10–20 percent cheaper than an all-PSW "
        "plan while remaining within legal scope; that the Medical Expense "
        "Tax Credit, Disability Tax Credit, and Canada Caregiver Credit "
        "collectively reduce out-of-pocket by 15–35 percent for eligible "
        "families but are routinely under-claimed; and that the cross-"
        "province gap between model-recommended hours and subsidised hours "
        "varies by a factor of three. The paper is a reference framework, "
        "not clinical or financial advice, and is not a substitute for "
        "individualised assessment by a regulated health professional or "
        "registered tax practitioner.",
        s['Abstract']
    ))
    story.append(PageBreak())


def build_toc(story, s):
    story.append(Paragraph("Contents", s['SectionH1']))
    entries = [
        "Abstract",
        "I.   Definitions and scope",
        "II.  Assessment instruments",
        "III. Scope of practice across Canada",
        "IV.  The cost landscape",
        "V.   Subsidised programs",
        "VI.  The tax relief stack",
        "VII. Employment law for private-hire households",
        "VIII. The cost model",
        "IX.  Case studies",
        "X.   Limitations and caveats",
        "Acknowledgements, data sources, and references",
        "Appendix A. Reproducibility",
    ]
    for e in entries:
        story.append(Paragraph(e, s['TocEntry']))
    story.append(PageBreak())


def build_part_i(story, s):
    story.append(Paragraph("I. Definitions and scope", s['SectionH1']))
    story.append(Paragraph(
        "This paper is restricted to Canada. All monetary values are in "
        "Canadian dollars (CAD) and indexed to the 2026 taxation year. The "
        "model covers adults living in private dwellings who require some "
        "combination of personal support, skilled nursing, and housekeeping "
        "assistance. It does not cover residential long-term care, "
        "retirement residences, or acute inpatient care.",
        s['Body']
    ))

    definitions = [
        ("ADL", "Activities of Daily Living — the six basic self-care tasks measured by the Katz Index (bathing, dressing, toileting, transferring, continence, feeding)."),
        ("IADL", "Instrumental Activities of Daily Living — the eight support tasks measured by the Lawton Scale (telephone, shopping, food preparation, housekeeping, laundry, transportation, medication management, finances)."),
        ("PSW", "Personal Support Worker — title used in Ontario and Quebec for non-regulated health workers trained in ADL assistance."),
        ("HCA", "Health Care Aide — equivalent title used in British Columbia, Alberta, Saskatchewan, and Manitoba."),
        ("HSW", "Home Support Worker — equivalent title used in the Atlantic provinces and territories."),
        ("LPN / RPN", "Licensed Practical Nurse (in most provinces) or Registered Practical Nurse (Ontario) — regulated nursing professional authorised to administer medications and perform basic wound care."),
        ("RN", "Registered Nurse — regulated nursing professional with full clinical scope."),
        ("Companion / Sitter", "Unregulated role providing social support and supervision. Not authorised for personal care tasks."),
        ("Housekeeper (private hire)", "Worker hired directly by a family for cleaning, laundry, and light meal preparation. Private-hire arrangements may engage CRA employer obligations above statutory thresholds."),
        ("Cleaning service (agency)", "Incorporated service provider delivering housekeeping with employer-of-record handling of CPP, EI, WSIB, and liability insurance."),
        ("Private pay", "Services paid out of pocket by the recipient or family, without subsidy."),
        ("Subsidised", "Services provided, allocated, or reimbursed through a provincial, territorial, or federal program."),
    ]
    def_table = make_table(
        ["Term", "Definition"],
        definitions,
        col_widths=[1.25 * inch, 5.55 * inch],
    )
    story.append(def_table)
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(
        "The scope distinction between personal care and housekeeping is "
        "the central decision point of this paper. Personal care is "
        "physical assistance with the recipient's body; housekeeping is "
        "cleaning and maintenance of the recipient's dwelling. The former "
        "requires a trained, regulated, or at least registered worker; the "
        "latter does not. A cleaning service cannot, legally, perform "
        "personal care, and a family that attempts to substitute cleaning "
        "for personal care is exposed to liability, loss of insurance "
        "coverage, and — most importantly — risk to the recipient.",
        s['Body']
    ))
    story.append(PageBreak())


def build_part_ii(story, s):
    story.append(Paragraph("II. Assessment instruments", s['SectionH1']))
    story.append(Paragraph("Katz Index of Independence in ADL", s['SectionH2']))
    story.append(Paragraph(
        "The Katz Index was introduced in 1963 as a six-item measure of "
        "basic self-care. Each item is scored as independent (1) or "
        "dependent (0), and the six items are summed to a score in the "
        "range 0–6, where 6 indicates full independence and 0 indicates "
        "total dependence. The six items are bathing, dressing, toileting, "
        "transferring, continence, and feeding. The instrument is widely "
        "used in Canadian provincial home care assessment programs and "
        "underlies the interRAI Home Care (interRAI HC) tool used by most "
        "provincial home care programs.",
        s['Body']
    ))
    story.append(Paragraph("Lawton Instrumental ADL Scale", s['SectionH2']))
    story.append(Paragraph(
        "The Lawton Scale, introduced in 1969, measures eight higher-order "
        "support tasks: using the telephone, shopping, food preparation, "
        "housekeeping, laundry, transportation, medication management, and "
        "finances. Scores range 0–8. The Lawton Scale is sensitive to "
        "early functional decline that the Katz ADL does not detect, and "
        "it is the primary driver of the housekeeping-hours term in the "
        "cost model.",
        s['Body']
    ))
    story.append(Paragraph("Worked example", s['SectionH2']))
    story.append(Paragraph(
        "A 74-year-old woman with moderate Parkinson's disease lives alone. "
        "She can walk with a walker, manages her own toileting and feeding, "
        "but requires assistance with bathing and dressing. Katz items "
        "score as follows: bathing 0, dressing 0, toileting 1, transferring "
        "0 (requires rail assistance), continence 1, feeding 1 — Katz "
        "total 3. On IADL: telephone 1, shopping 0, food preparation 0, "
        "housekeeping 0, laundry 0, transportation 0, medication 0, "
        "finances 1 — Lawton total 2.",
        s['Body']
    ))


def build_part_iii(story, s):
    story.append(Paragraph("III. Scope of practice across Canada", s['SectionH1']))
    story.append(Paragraph(
        "Scope of practice for personal support workers is defined at the "
        "provincial level. Ontario maintains a voluntary PSW registry "
        "administered under the NACC curriculum standard; British Columbia "
        "and Alberta maintain mandatory Care Aide or Health Care Aide "
        "registries; most other provinces rely on program-based "
        "certification tied to community college or health authority "
        "training. Nursing scope is defined by the regulating college in "
        "each province (CNO in Ontario, OIIQ in Quebec, BCCNM in British "
        "Columbia, and so on).",
        s['Body']
    ))
    story.append(Paragraph(
        "The table below summarises which worker type is legally "
        "authorised to perform each of six categories of task across a "
        "representative subset of Canadian jurisdictions. Values are T for "
        "authorised, D for authorised only under delegation or RN "
        "direction, and N for not authorised.",
        s['Body']
    ))
    scope_rows = [
        ["Medication administration", "N", "T", "T", "N", "N", "N"],
        ["Transfer assistance", "T", "T", "T", "N", "N", "N"],
        ["Bathing and toileting", "T", "T", "T", "N", "N", "N"],
        ["Basic wound care", "D", "T", "T", "N", "N", "N"],
        ["Catheter and ostomy care", "N", "T", "T", "N", "N", "N"],
        ["Housekeeping", "T", "N", "N", "N", "T", "T"],
        ["Meal preparation", "T", "N", "N", "T", "T", "T"],
    ]
    scope_table = make_table(
        ["Task", "PSW / HCA", "LPN", "RN", "Companion", "Housekeeper", "Cleaning Svc"],
        scope_rows,
        col_widths=[2.0 * inch, 0.85 * inch, 0.65 * inch, 0.65 * inch, 0.9 * inch, 0.9 * inch, 0.85 * inch],
    )
    story.append(scope_table)
    story.append(Paragraph(
        "T = authorised. D = authorised under delegation or RN direction only. N = not authorised.",
        s['Caption']
    ))
    story.append(Paragraph(
        "Two rows in this table deserve particular attention. First, "
        "neither a companion, nor a private housekeeper, nor a cleaning "
        "service is authorised to perform transfer assistance or bathing. "
        "Families who attempt to delegate these tasks to a cleaning worker "
        "are outside the worker's scope of practice, outside their liability "
        "insurance, and frequently outside their physical capability "
        "(transfer assistance is a musculoskeletal injury risk for "
        "untrained workers). Second, neither a PSW, LPN, nor RN is in "
        "general scope for housekeeping — their time is best used on "
        "regulated tasks. The cost-minimising service mix is therefore "
        "almost always hybrid: a PSW or HCA for personal care hours and a "
        "housekeeper or cleaning service for housekeeping hours.",
        s['Body']
    ))
    story.append(PageBreak())


def build_part_iv(story, s):
    story.append(Paragraph("IV. The cost landscape", s['SectionH1']))
    story.append(Paragraph(
        "Private-pay hourly rates for home care services vary substantially "
        "across Canadian jurisdictions. The reference rate bands used in "
        "this paper are reconciled between two upper-bound and lower-bound "
        "anchors: Statistics Canada wage tables for the relevant National "
        "Occupational Classification codes (44101 for home support workers, "
        "33102 for nurse aides, 32101 for licensed practical nurses, and "
        "31301 for registered nurses), and the Canadian Home Care "
        "Association's published agency markup range.",
        s['Body']
    ))
    rate_rows = [
        ["Ontario", "$28–$42", "$38–$62", "$54–$95", "$22–$36", "1.38×"],
        ["Quebec", "$26–$39", "$35–$57", "$50–$87", "$20–$33", "1.30×"],
        ["British Columbia", "$30–$45", "$41–$67", "$58–$103", "$24–$39", "1.42×"],
        ["Alberta", "$29–$44", "$40–$65", "$57–$100", "$23–$38", "1.40×"],
        ["Saskatchewan", "$26–$39", "$35–$57", "$50–$87", "$20–$33", "1.35×"],
        ["Manitoba", "$25–$38", "$34–$56", "$49–$86", "$20–$32", "1.32×"],
        ["Nova Scotia", "$25–$35", "$33–$55", "$48–$84", "$19–$32", "1.30×"],
        ["New Brunswick", "$24–$34", "$33–$53", "$46–$82", "$19–$31", "1.28×"],
        ["Newfoundland", "$25–$36", "$34–$56", "$49–$86", "$20–$32", "1.30×"],
        ["PEI", "$24–$35", "$32–$52", "$45–$80", "$18–$30", "1.28×"],
        ["Yukon", "$34–$51", "$46–$76", "$66–$116", "$27–$41", "1.45×"],
        ["NWT", "$38–$57", "$51–$84", "$73–$128", "$30–$49", "1.50×"],
        ["Nunavut", "$42–$63", "$57–$93", "$81–$143", "$33–$54", "1.55×"],
    ]
    rate_table = make_table(
        ["Jurisdiction", "PSW / HCA", "LPN", "RN", "Housekeeper", "Agency markup"],
        rate_rows,
        col_widths=[1.5 * inch, 0.95 * inch, 0.95 * inch, 1.05 * inch, 1.1 * inch, 1.05 * inch],
    )
    story.append(rate_table)
    story.append(Paragraph(
        "Median private-pay rate bands (CAD per hour) reconciled against StatsCan Table 14-10-0417-01 "
        "and the Canadian Home Care Association agency markup range. Northern premiums reflect remoteness.",
        s['Caption']
    ))
    story.append(Paragraph(
        "Several observations follow from this table. The BC rate band is "
        "the highest in the lower 49°N (reflecting labour market tightness "
        "and a larger private market), and the territorial rates carry "
        "substantial remoteness premiums. The agency markup, which converts "
        "a worker's wage into the price families pay, is roughly 1.25× to "
        "1.50× across the country — with the important caveat that the "
        "agency assumes the CPP, EI, WSIB, and supervisory costs that a "
        "private-hire arrangement would otherwise put on the family.",
        s['Body']
    ))
    story.append(PageBreak())


def build_part_v(story, s):
    story.append(Paragraph("V. Subsidised programs", s['SectionH1']))
    story.append(Paragraph(
        "Every Canadian province and territory operates a subsidised home "
        "care program. Eligibility is typically needs-based, administered "
        "through a single point of access, and capped at a weekly hours "
        "ceiling. Wait times between referral and first service vary from "
        "approximately two weeks to six weeks depending on jurisdiction "
        "and acuity. Program names and administering bodies change over "
        "time; the table below is current as of April 2026.",
        s['Body']
    ))
    program_rows = [
        ["Ontario", "HCCSS", "14 HCCSS regions under Ontario Health", "~14–21"],
        ["Quebec", "Soutien à domicile", "CLSC via CIUSSS/CISSS", "~20–60"],
        ["British Columbia", "Home and Community Care", "5 Regional Health Authorities", "~16–30"],
        ["Alberta", "Continuing Care at Home", "Alberta Health Services", "~12–40"],
        ["Saskatchewan", "Home Care", "Saskatchewan Health Authority", "~10–35"],
        ["Manitoba", "Home Care Program", "Shared Health Manitoba", "~12–30"],
        ["Nova Scotia", "Continuing Care Home Care", "Nova Scotia Health", "~10–40"],
        ["New Brunswick", "Extra-Mural Program", "Horizon Health Network", "~12–35"],
        ["Newfoundland", "Home Support Program", "NL Health Services", "~10–45"],
        ["PEI", "Health PEI Home Care", "Health PEI", "~8–30"],
        ["Yukon", "Home Care Program", "Yukon HSS", "~10–20"],
        ["NWT", "Home and Community Care", "NWT HSS", "~8–25"],
        ["Nunavut", "Home and Community Care", "Department of Health", "~6–30"],
    ]
    program_table = make_table(
        ["Jurisdiction", "Program", "Administering body", "Hours/week (moderate–high need)"],
        program_rows,
        col_widths=[1.5 * inch, 1.9 * inch, 2.4 * inch, 1.0 * inch],
    )
    story.append(program_table)
    story.append(Paragraph(
        "Published subsidised hours are best-effort point-in-time estimates compiled from provincial program "
        "pages and CIHI Home Care Reporting System indicators.",
        s['Caption']
    ))
    story.append(Paragraph(
        "Two structural features of the Canadian home care subsidy "
        "landscape are worth highlighting. First, most provincial programs "
        "explicitly exclude standalone housekeeping — the subsidy covers "
        "personal care and nursing only, with the result that families who "
        "need housekeeping must pay for it out of pocket even if they are "
        "actively enrolled in the subsidised program. Second, the ceiling "
        "on subsidised hours (roughly 14 hours per week for moderate-need "
        "clients in Ontario, 30 hours in BC, 40 hours in Nova Scotia) is "
        "well below the ~30–50 hours per week that the cost model "
        "typically recommends for high-ADL recipients, leaving a structural "
        "out-of-pocket gap that is quantified in Section VIII.",
        s['Body']
    ))
    story.append(PageBreak())


def build_part_vi(story, s):
    story.append(Paragraph("VI. The tax relief stack", s['SectionH1']))
    story.append(Paragraph(
        "Canadian households paying out of pocket for home care may claim "
        "three overlapping federal tax credits, each replicated at the "
        "provincial level with its own rate and threshold. For the 2026 "
        "taxation year:",
        s['Body']
    ))
    metc_rows = [
        ["Medical Expense Tax Credit (METC)",
         "15% federal + provincial factor",
         "Qualifying medical expenses exceeding the lesser of 3% of net income or $2,759 (federal)",
         "CRA S1-F1-C1"],
        ["Disability Tax Credit (DTC)",
         "15% federal + provincial factor",
         "Base amount $9,872 (federal) plus provincial amount, available if the recipient holds a valid DTC certificate",
         "CRA S1-F1-C2"],
        ["Canada Caregiver Credit (CCC)",
         "15% federal + provincial factor",
         "Caregiver amount $8,375 (federal) plus provincial amount, phased out between dependant net incomes of $19,666 and $28,041",
         "CRA folio on caregiver amount"],
    ]
    metc_table = make_table(
        ["Credit", "Rate", "Base", "Source"],
        metc_rows,
        col_widths=[1.8 * inch, 1.3 * inch, 2.6 * inch, 1.1 * inch],
    )
    story.append(metc_table)
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(
        "Veterans may also be eligible for the Veterans Independence "
        "Program (VIP) administered by Veterans Affairs Canada, which "
        "reimburses housekeeping, grounds maintenance, personal care, and "
        "related services up to approximate annual ceilings of $3,072, "
        "$1,884, and $9,324 respectively. First Nations and Inuit "
        "community residents may be eligible for the FNIHB Home and "
        "Community Care Program administered by Indigenous Services "
        "Canada, which provides in-kind service rather than cash "
        "reimbursement.",
        s['Body']
    ))
    story.append(Paragraph("Interaction and claiming strategy", s['SectionH2']))
    story.append(Paragraph(
        "The METC, DTC, and CCC can all be claimed in the same taxation "
        "year, subject to their individual eligibility rules. The DTC "
        "requires a valid T2201 certificate; the CCC requires that the "
        "recipient either live with the claimant or depend on the claimant "
        "for support. In most configurations the METC is the largest "
        "credit by dollar value because it scales with out-of-pocket "
        "spending, while the DTC and CCC are fixed amounts. A worked "
        "example appears in the case studies in Section IX.",
        s['Body']
    ))
    story.append(PageBreak())


def build_part_vii(story, s):
    story.append(Paragraph("VII. Employment law for private-hire households", s['SectionH1']))
    story.append(Paragraph(
        "Families who hire personal support workers or housekeepers "
        "directly, rather than through an agency, enter an employment "
        "relationship that the Canada Revenue Agency evaluates under a "
        "four-factor test: control, ownership of tools, chance of profit "
        "and risk of loss, and integration. For a recurring home care "
        "arrangement in which the family sets the schedule, supplies the "
        "home as the workplace, and pays a regular hourly wage, the CRA "
        "will almost always conclude that the family is an employer and "
        "the worker is an employee.",
        s['Body']
    ))
    story.append(Paragraph(
        "Being an employer triggers four concrete obligations: (1) CPP "
        "contributions (both the employer and employee share), (2) "
        "Employment Insurance premiums (both shares), (3) provincial "
        "workers' compensation registration and premiums (WSIB in Ontario, "
        "WorkSafeBC in British Columbia, equivalent bodies in other "
        "provinces), and (4) T4 reporting each year. Families also take on "
        "obligations under provincial employment standards legislation "
        "around vacation pay, statutory holiday pay, and termination "
        "notice.",
        s['Body']
    ))
    story.append(Paragraph(
        "The agency alternative transfers all of these obligations to the "
        "agency as employer of record. The price difference (the agency "
        "markup of roughly 1.25× to 1.50×) is what families pay for that "
        "transfer. In practice, for arrangements exceeding approximately "
        "20 hours per week, the administrative and compliance burden of "
        "private hire makes the agency option the practical default.",
        s['Body']
    ))
    comp_rows = [
        ["Total hourly cost", "$28–$42 (wage) + ~18% loading = $33–$50", "$38–$63 (billed rate)"],
        ["Responsibility for CPP, EI, WSIB", "Family (self-register as employer)", "Agency"],
        ["Backup / continuity of care", "Family's problem", "Agency schedules replacement"],
        ["Administrative burden", "Payroll, T4, source deductions", "None beyond paying invoices"],
        ["Liability for worker injury", "WSIB premium + residual liability", "Agency"],
        ["Scheduling flexibility", "Maximum", "Moderate"],
        ["Typical cost-effectiveness threshold", "Under ~15 hours/week", "At or above ~20 hours/week"],
    ]
    comp_table = make_table(
        ["Dimension", "Private hire", "Agency"],
        comp_rows,
        col_widths=[2.0 * inch, 2.8 * inch, 2.0 * inch],
    )
    story.append(comp_table)
    story.append(PageBreak())


def build_part_viii(story, s):
    story.append(Paragraph("VIII. The cost model", s['SectionH1']))
    story.append(Paragraph(
        "The reference cost model is a parametric decision framework that "
        "takes an assessment triple, household and jurisdictional context, "
        "and returns a recommended service mix and full cost stack. The "
        "calculation proceeds in six steps:",
        s['Body']
    ))
    story.append(Paragraph(
        "<b>Step 1. Hours derivation.</b> Weekly personal support hours are "
        "computed as <i>7 × (6 − ADL) + cognitive_bump + mobility_bump − "
        "credited_informal</i>, with the informal-caregiver credit capped "
        "at 60 percent of base to reflect the practical impossibility of "
        "fully substituting family caregiving for formal hours. "
        "Housekeeping hours are computed as <i>2 × (8 − IADL) + "
        "household_modifier</i>. Nursing hours are computed from the "
        "diagnosis category with a small cognitive adjustment.",
        s['Body']
    ))
    story.append(Paragraph(
        "<b>Step 2. Scope gate.</b> If the ADL score is at or below 4, or "
        "if cognition is moderate or severe, personal care is mandatory "
        "and the model emits a scope warning preventing any plan that "
        "substitutes housekeeping for personal care hours.",
        s['Body']
    ))
    story.append(Paragraph(
        "<b>Step 3. Nursing gate.</b> If the primary diagnosis is post-"
        "surgical recovery, stroke, complex wound, ostomy, or involves "
        "medication administration, an LPN or RN is required and the "
        "model emits a nursing-hours requirement.",
        s['Body']
    ))
    story.append(Paragraph(
        "<b>Step 4. Rate lookup.</b> The median private-pay rate for the "
        "recipient's province and the applicable service category is "
        "retrieved from the reference table <i>home_care_services_canada.csv</i>. "
        "If the family has chosen an agency rather than private hire, the "
        "rate is multiplied by the province's agency markup.",
        s['Body']
    ))
    story.append(Paragraph(
        "<b>Step 5. Subsidy allocation.</b> The subsidised hours awarded "
        "by the recipient's provincial program are retrieved from "
        "<i>home_care_subsidy_programs.csv</i> and capped at the model's "
        "recommended personal support hours. The subsidy value is the "
        "subsidised hours times the province's PSW rate.",
        s['Body']
    ))
    story.append(Paragraph(
        "<b>Step 6. Tax relief stack.</b> Out-of-pocket annual cost is "
        "reduced by the METC (federal and provincial), the DTC (if "
        "eligible), the CCC (if eligible, phased out between the defined "
        "income bands), and the VAC VIP (if the recipient is a veteran). "
        "The final out-of-pocket after credits is the headline number "
        "returned to the family.",
        s['Body']
    ))
    story.append(Paragraph(
        "The model also returns an all-PSW counterfactual — the cost of "
        "the same total hours if every hour were billed at the PSW rate "
        "rather than mixing PSW and housekeeper rates — and the hybrid "
        "savings, which quantify the dollar benefit of the cost-minimising "
        "service mix. The full return dataclass is documented in the "
        "reference implementation at engines/python/engine.py.",
        s['Body']
    ))
    story.append(PageBreak())


def build_part_ix(story, s):
    story.append(Paragraph("IX. Case studies", s['SectionH1']))
    story.append(Paragraph(
        "Three worked examples illustrate how the model handles "
        "representative combinations of assessment, jurisdiction, and "
        "eligibility.",
        s['Body']
    ))

    story.append(Paragraph("Case 1 — Mrs. A., 82, Sudbury ON, mild frailty", s['SectionH2']))
    story.append(Paragraph(
        "Mrs. A. is an 82-year-old widow living alone in Sudbury. Her "
        "Katz ADL is 5 (she requires assistance with bathing only), her "
        "Lawton IADL is 5 (she no longer shops or prepares full meals). "
        "She has no cognitive impairment, uses a cane, and has no "
        "significant chronic conditions. Her daughter provides about 5 "
        "hours per week of informal caregiving.",
        s['Body']
    ))
    case1_rows = [
        ["Recommended PSW hours / week", "8.5"],
        ["Recommended housekeeping hours / week", "9.0"],
        ["Recommended nursing hours / week", "0"],
        ["Service mix", "PSW + housekeeping"],
        ["Private-pay cost, monthly", "$1,850"],
        ["Subsidised hours allocated / week", "8.5 (capped)"],
        ["Out-of-pocket before credits, monthly", "~$475"],
        ["METC + DTC + CCC annual value", "~$420"],
        ["Out-of-pocket after credits, monthly", "~$440"],
    ]
    case1_table = make_table(["Item", "Value"], case1_rows, col_widths=[3.6 * inch, 3.2 * inch])
    story.append(case1_table)
    story.append(Paragraph(
        "Interpretation: the subsidised program covers most of Mrs. A.'s "
        "personal support needs; her out-of-pocket burden comes almost "
        "entirely from housekeeping, which the Ontario program does not "
        "cover. A cleaning service at the private-housekeeper rate is the "
        "cost-minimising option for her housekeeping hours. A PSW for the "
        "same 9 hours would add roughly $470 per month.",
        s['Body']
    ))

    story.append(Paragraph("Case 2 — Mr. B., 74, Vancouver BC, moderate dementia, post-stroke", s['SectionH2']))
    story.append(Paragraph(
        "Mr. B. is a 74-year-old man living with his spouse in Vancouver. "
        "He had a mild stroke 18 months ago and has since developed "
        "moderate cognitive impairment. His Katz ADL is 2 (he requires "
        "assistance with all personal care except feeding), his Lawton "
        "IADL is 1. He uses a walker indoors. His spouse provides about "
        "20 hours per week of informal caregiving but is approaching "
        "caregiver burnout. The household's net family income is $72,000. "
        "Mr. B. holds a valid Disability Tax Credit certificate.",
        s['Body']
    ))
    case2_rows = [
        ["Recommended PSW hours / week", "28.0"],
        ["Recommended housekeeping hours / week", "15.5"],
        ["Recommended nursing hours / week", "0"],
        ["Service mix", "PSW + housekeeping (with scope warning)"],
        ["Private-pay cost, monthly", "$6,708"],
        ["Subsidised hours allocated / week", "25.3"],
        ["Out-of-pocket before credits, monthly", "$2,553"],
        ["METC annual value", "$5,712"],
        ["DTC annual value", "$1,958"],
        ["CCC annual value", "(phased out at this income)"],
        ["Total credits annual value", "$7,670"],
        ["Out-of-pocket after credits, monthly", "$1,914"],
        ["All-PSW counterfactual, monthly", "$7,144"],
        ["Hybrid savings, monthly", "$436"],
    ]
    case2_table = make_table(["Item", "Value"], case2_rows, col_widths=[3.6 * inch, 3.2 * inch])
    story.append(case2_table)
    story.append(Paragraph(
        "Interpretation: the BC subsidised program allocates nearly all of "
        "Mr. B.'s personal support hours, leaving housekeeping and "
        "residual personal-care gap hours as the out-of-pocket burden. The "
        "combined METC and DTC reduce the annual out-of-pocket by about "
        "$7,670, bringing the monthly net cost down from $2,553 to "
        "$1,914. The hybrid mix (housekeeping at the private-housekeeper "
        "rate rather than the PSW rate) saves approximately $436 per "
        "month versus an all-PSW plan. The scope warning reminds the "
        "family that the housekeeping hours are in addition to — not "
        "instead of — the personal support hours.",
        s['Body']
    ))
    story.append(PageBreak())

    story.append(Paragraph("Case 3 — Mr. C., 89, rural New Brunswick, bedbound veteran", s['SectionH2']))
    story.append(Paragraph(
        "Mr. C. is an 89-year-old veteran living with his adult daughter "
        "in rural New Brunswick. He is bedbound, has severe cognitive "
        "impairment, and requires complete assistance with all activities "
        "of daily living. His Katz ADL is 0; Lawton IADL is 0. He holds "
        "the Disability Tax Credit and is VIP-eligible. Household net "
        "income is $48,000.",
        s['Body']
    ))
    case3_rows = [
        ["Recommended PSW hours / week", "~56"],
        ["Recommended housekeeping hours / week", "~17"],
        ["Recommended nursing hours / week", "~3"],
        ["Service mix", "nursing + PSW + housekeeping (scope warning)"],
        ["Private-pay cost, monthly", "~$10,800"],
        ["Subsidised hours allocated / week", "~35 (NB EMP ceiling)"],
        ["Out-of-pocket before credits, monthly", "~$5,700"],
        ["METC annual value", "~$9,800"],
        ["DTC annual value", "~$1,960"],
        ["CCC annual value", "~$1,380"],
        ["VAC VIP annual value", "~$12,400"],
        ["Total credits annual value", "~$25,500"],
        ["Out-of-pocket after credits, monthly", "~$3,575"],
    ]
    case3_table = make_table(["Item", "Value"], case3_rows, col_widths=[3.6 * inch, 3.2 * inch])
    story.append(case3_table)
    story.append(Paragraph(
        "Interpretation: at this acuity level, full out-of-pocket cost "
        "would be approximately equal to a retirement home placement, but "
        "the VAC VIP, DTC, CCC, and METC stack together reduce the net "
        "cost by roughly one-third, bringing the monthly burden into the "
        "range where aging in place remains financially viable. Crucially, "
        "the subsidised EMP hours do not cover the full model-recommended "
        "hours — the gap is structural, and the family must supplement "
        "privately or enlist additional informal caregiving.",
        s['Body']
    ))
    story.append(PageBreak())


def build_part_x(story, s):
    story.append(Paragraph("X. Limitations and caveats", s['SectionH1']))
    story.append(Paragraph(
        "The model presented here is a reference framework, not a "
        "substitute for individualised clinical or financial assessment. "
        "Specific limitations include:",
        s['Body']
    ))
    limitations = [
        "The synthetic scenario dataset is deterministically generated from population-level priors and is not empirical household data. It must not be cited as such.",
        "Subsidised hours are best-effort point-in-time estimates; provincial programs change eligibility rules, waitlists, and hour ceilings with some regularity.",
        "Private-pay rate bands are reconciled against StatsCan wage tables and CHCA markup ranges and carry an implied uncertainty of roughly ±15 percent.",
        "Tax rule parameters are current for the 2026 taxation year and must be refreshed annually.",
        "The model does not cover residential long-term care, retirement home transitions, or acute inpatient care.",
        "The model does not substitute for assessment by a regulated health professional (geriatrician, nurse case manager, occupational therapist) or by a registered tax practitioner.",
        "Worked case studies are composite, not individual, and the rounded case-study values reflect illustrative approximations rather than exact engine output for the named persons.",
    ]
    for lim in limitations:
        story.append(Paragraph(f"&bull; {lim}", s['BodyIndent']))
    story.append(PageBreak())


def build_references(story, s):
    story.append(Paragraph("Acknowledgements, data sources, and references", s['SectionH1']))
    story.append(Paragraph(
        "This paper is made possible by publicly-available data published "
        "by Statistics Canada, the Canadian Institute for Health "
        "Information, the Canada Revenue Agency, Veterans Affairs Canada, "
        "Indigenous Services Canada, the Canadian Home Care Association, "
        "and the ministries of health of every Canadian province and "
        "territory. The assessment instruments are drawn from the original "
        "1963 and 1969 publications of Katz and Lawton and are used here "
        "as reference-only scoring frameworks.",
        s['Body']
    ))
    story.append(Paragraph(
        "Model implementation and empirical rate compilation by Dave Cook, "
        "Binx Professional Cleaning, North Bay, Ontario. The maintainer is "
        "not a health professional; this paper is a reference model, not "
        "clinical advice, and should not be used in place of an "
        "assessment by a regulated health professional or registered tax "
        "practitioner.",
        s['Body']
    ))
    story.append(Paragraph("Principal sources", s['SectionH2']))
    references = [
        "Statistics Canada. Table 14-10-0417-01 — Employment and average weekly earnings by industry, monthly, seasonally adjusted.",
        "Statistics Canada. Table 17-10-0005-01 — Population estimates on July 1, by age and sex.",
        "Statistics Canada. Table 18-10-0004-01 — Consumer Price Index, monthly, not seasonally adjusted (health and personal care subindices).",
        "Statistics Canada. General Social Survey on Caregiving and Care Receiving, Cycle 32 (2018), public use microdata file.",
        "Canadian Institute for Health Information. Home Care Reporting System (HCRS) public indicator tables.",
        "Canadian Institute for Health Information. Your Health System — home care volume, wait time, and access indicators.",
        "Canada Revenue Agency. Income Tax Folio S1-F1-C1 — Medical Expense Tax Credit.",
        "Canada Revenue Agency. Income Tax Folio S1-F1-C2 — Disability Tax Credit.",
        "Canada Revenue Agency. Canada Caregiver Credit — technical interpretation.",
        "Veterans Affairs Canada. Veterans Independence Program — benefit rates and eligibility.",
        "Indigenous Services Canada. First Nations and Inuit Home and Community Care Program.",
        "Canadian Home Care Association. High-Value Home Care report series.",
        "Ontario Ministry of Health. Home and Community Care Support Services — provincial program pages.",
        "Government of British Columbia. Home and Community Care Policy Manual.",
        "Alberta Health Services. Continuing Care at Home program documentation.",
        "Gouvernement du Québec. Soutien à domicile — Services des CLSC.",
        "Saskatchewan Health Authority, Manitoba Home Care Program, Nova Scotia Continuing Care, NB Extra-Mural Program, NL Health Services Home Support, Health PEI Home Care, Yukon HSS, GNWT HSS, and Government of Nunavut — provincial and territorial home care program pages.",
        "Katz S, Ford AB, Moskowitz RW, Jackson BA, Jaffe MW. Studies of Illness in the Aged. The Index of ADL: A Standardized Measure of Biological and Psychosocial Function. JAMA. 1963;185(12):914-919.",
        "Lawton MP, Brody EM. Assessment of older people: self-maintaining and instrumental activities of daily living. The Gerontologist. 1969;9(3):179-186.",
    ]
    for i, ref in enumerate(references, 1):
        story.append(Paragraph(f"[{i}] {ref}", s['Ref']))
    story.append(PageBreak())


def build_appendix_a(story, s):
    story.append(Paragraph("Appendix A. Reproducibility", s['SectionH1']))
    story.append(Paragraph(
        "All code and datasets associated with this paper are published "
        "under open licenses. The code is MIT-licensed; the datasets and "
        "this document are licensed under CC BY 4.0. The repository is "
        f"hosted at {link('https://github.com/DaveCookVectorLabs/home-care-cost-model')} "
        "and mirrored on GitLab, Codeberg, SourceHut, and Launchpad. The "
        "Python reference implementation is published on PyPI as "
        "home-care-cost-model; language ports are published to npm, "
        "Crates.io, Maven Central, RubyGems, Hex.pm, Packagist, and "
        "pkg.go.dev under matching names.",
        s['Body']
    ))
    story.append(Paragraph(
        "The synthetic scenario dataset is generated deterministically "
        "from random.seed(42). The reference tables "
        "(home_care_services_canada.csv, home_care_tax_parameters_2026.csv, "
        "home_care_subsidy_programs.csv) are hand-curated and their "
        "provenance is recorded in datasets/SOURCES.md. The full pipeline "
        "can be reproduced by running the generator scripts in sequence:",
        s['Body']
    ))
    reproduce_cmds = [
        "python datasets/pull_sources.py",
        "python datasets/generate_home_care_services_canada.py",
        "python datasets/generate_home_care_tax_parameters.py",
        "python datasets/generate_home_care_subsidy_programs.py",
        "python datasets/generate_home_care_scenarios.py",
        "python datasets/generate_home_care_per_province_rate_bands.py",
        "python datasets/generate_home_care_cost_model_archetypes.py",
        "python datasets/generate_home_care_tax_relief_sensitivity.py",
        "python datasets/generate_home_care_subsidy_gap.py",
    ]
    for cmd in reproduce_cmds:
        story.append(Paragraph(
            f"<font face='Courier' size='9'>{cmd}</font>",
            s['BodyIndent']
        ))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(
        "Regeneration of any dataset in the same Python environment must "
        "yield a byte-identical output. Cross-language parity between the "
        "seven engine implementations (Python, Rust, Java, Ruby, Elixir, "
        "PHP, Go) is verified against the three case studies in Section "
        "IX to the cent. The working paper DOI is assigned by Zenodo at "
        "publication and recorded in the repository CITATION file.",
        s['Body']
    ))


def generate_pdf():
    doc = SimpleDocTemplate(
        str(OUT_FILE),
        pagesize=letter,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
        title="The Home Care Cost Model",
        author="Dave Cook",
        subject="Reference cost model for Canadian home care service-mix decisions",
    )
    s = get_styles()
    story = []

    build_cover_page(story, s)
    build_abstract(story, s)
    build_toc(story, s)
    build_part_i(story, s)
    build_part_ii(story, s)
    build_part_iii(story, s)
    build_part_iv(story, s)
    build_part_v(story, s)
    build_part_vi(story, s)
    build_part_vii(story, s)
    build_part_viii(story, s)
    build_part_ix(story, s)
    build_part_x(story, s)
    build_references(story, s)
    build_appendix_a(story, s)

    def first_page(canvas, doc):
        draw_cover(canvas, doc)

    def later_pages(canvas, doc):
        draw_footer(canvas, doc)

    doc.build(story, onFirstPage=first_page, onLaterPages=later_pages)
    print(f"Generated: {OUT_FILE}")
    return OUT_FILE


if __name__ == "__main__":
    generate_pdf()
