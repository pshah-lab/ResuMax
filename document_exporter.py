"""
Document Exporter for Stage 9.
Generates clean, ATS-compliant .docx and text-layer .pdf resumes.
Follows all structural guidelines from ATS_Guidelines_and_Prompt_Design.md §2 & §3.
"""

from pathlib import Path
from typing import Union, Tuple, Optional
import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from models import MasterProfile, TailoredResume, CoverLetter
from latex_exporter import export_to_latex, generate_latex_code


def export_to_docx(
    profile: MasterProfile,
    tailored: TailoredResume,
    output_path: Union[str, Path]
) -> Path:
    """
    Generates a clean, single-column, standard-styled ATS-compliant .docx file.
    Uses body-level contact info, built-in standard headings, and native bullet lists.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    doc = docx.Document()

    # Set 0.75 in margins (clean standard)
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Base font setting
    style_normal = doc.styles["Normal"]
    font = style_normal.font
    font.name = "Calibri"
    font.size = Pt(10.5)
    font.color.rgb = RGBColor(30, 30, 30)

    # 1. Header (Candidate Contact Info in Document Body - Not Header/Footer!)
    name = profile.personal_info.full_name or "Resume"
    p_name = doc.add_paragraph()
    p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_name = p_name.add_run(name)
    r_name.font.size = Pt(18)
    r_name.font.bold = True
    r_name.font.color.rgb = RGBColor(10, 10, 10)
    p_name.paragraph_format.space_after = Pt(2)

    # Contact line
    contact_parts = []
    if profile.personal_info.location:
        contact_parts.append(profile.personal_info.location)
    if profile.personal_info.phone:
        contact_parts.append(profile.personal_info.phone)
    if profile.personal_info.email:
        contact_parts.append(profile.personal_info.email)
    if profile.personal_info.linkedin_url:
        contact_parts.append(profile.personal_info.linkedin_url.replace("https://", ""))
    if profile.personal_info.portfolio_url:
        contact_parts.append(profile.personal_info.portfolio_url.replace("https://", ""))

    if contact_parts:
        p_contact = doc.add_paragraph()
        p_contact.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_contact.paragraph_format.space_after = Pt(12)
        p_contact.add_run(" | ".join(contact_parts))

    def add_section_heading(title: str):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        run = p.add_run(title.upper())
        run.font.size = Pt(11.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor(20, 40, 80)
        # Subtle horizontal divider
        p.paragraph_format.keep_with_next = True

    # 2. Professional Summary
    summary_text = tailored.summary or profile.summary
    if summary_text:
        add_section_heading("Professional Summary")
        p_sum = doc.add_paragraph(summary_text)
        p_sum.paragraph_format.space_after = Pt(8)

    # 3. Dedicated Skills Section
    skills = tailored.selected_skills
    has_skills = any([skills.technical, skills.tools, skills.soft, skills.languages])
    if has_skills:
        add_section_heading("Skills & Competencies")
        if skills.technical:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            r_label = p.add_run("Technical Skills: ")
            r_label.bold = True
            p.add_run(", ".join(skills.technical))
        if skills.tools:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            r_label = p.add_run("Developer Tools & Cloud: ")
            r_label.bold = True
            p.add_run(", ".join(skills.tools))
        if skills.soft:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            r_label = p.add_run("Leadership & Soft Skills: ")
            r_label.bold = True
            p.add_run(", ".join(skills.soft))
        if skills.languages:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(6)
            r_label = p.add_run("Languages: ")
            r_label.bold = True
            p.add_run(", ".join(skills.languages))

    # 4. Work Experience
    if tailored.selected_experience:
        add_section_heading("Professional Experience")
        for exp in tailored.selected_experience:
            p_exp = doc.add_paragraph()
            p_exp.paragraph_format.space_before = Pt(4)
            p_exp.paragraph_format.space_after = Pt(1)
            
            # Title and Company
            r_title = p_exp.add_run(f"{exp.title}")
            r_title.bold = True
            p_exp.add_run(f" — {exp.company}")

            # Location and Dates
            date_str = f"{exp.start_date or ''} – {exp.end_date or ('Present' if exp.is_current else '')}"
            loc_str = f" ({exp.location})" if exp.location else ""
            p_date = doc.add_paragraph(f"{date_str}{loc_str}")
            p_date.runs[0].font.italic = True
            p_date.paragraph_format.space_after = Pt(3)

            # Native Bullet points
            for b in exp.bullets:
                p_b = doc.add_paragraph(b.tailored_text, style="List Bullet")
                p_b.paragraph_format.space_after = Pt(2)

    # 5. Education
    education_list = tailored.selected_education or profile.education
    if education_list:
        add_section_heading("Education")
        for edu in education_list:
            p_edu = doc.add_paragraph()
            p_edu.paragraph_format.space_after = Pt(2)
            r_deg = p_edu.add_run(f"{edu.degree} in {edu.field}" if edu.field else edu.degree)
            r_deg.bold = True
            p_edu.add_run(f" | {edu.institution}")
            if edu.graduation_date:
                r_grad = p_edu.add_run(f" ({edu.graduation_date})")
                r_grad.font.italic = True

    # 6. Certifications
    certs = tailored.selected_certifications or profile.certifications
    if certs:
        add_section_heading("Certifications")
        for c in certs:
            p_c = doc.add_paragraph(c, style="List Bullet")
            p_c.paragraph_format.space_after = Pt(2)

    # 7. Projects (Approved Only)
    projects = tailored.selected_projects or profile.get_approved_projects()
    if projects:
        add_section_heading("Key Projects")
        for proj in projects:
            p_proj = doc.add_paragraph()
            p_proj.paragraph_format.space_after = Pt(1)
            r_pname = p_proj.add_run(proj.name)
            r_pname.bold = True
            if proj.tech_stack:
                p_proj.add_run(f" [{', '.join(proj.tech_stack)}]")

            for b in proj.draft_bullets:
                p_b = doc.add_paragraph(b, style="List Bullet")
                p_b.paragraph_format.space_after = Pt(2)

    doc.save(str(out_file))
    return out_file


def _clean_latin1(text: str) -> str:
    """Sanitizes unicode typography to latin-1 safe ASCII equivalents for FPDF."""
    if not text:
        return ""
    return (
        text.replace("—", " - ")
            .replace("–", " - ")
            .replace("•", "*")
            .replace("’", "'")
            .replace("‘", "'")
            .replace("“", '"')
            .replace("”", '"')
            .replace("…", "...")
            .encode("latin-1", "replace")
            .decode("latin-1")
    )


def export_to_pdf_text_layer(
    profile: MasterProfile,
    tailored: TailoredResume,
    output_path: Union[str, Path]
) -> Path:
    """
    Generates a clean text-layer PDF file using FPDF (guaranteeing selectable text).
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        from fpdf import FPDF
    except ImportError:
        # Fallback: create plain text representation with .pdf naming or skip
        return export_to_docx(profile, tailored, out_file.with_suffix(".docx"))

    class PDFResume(FPDF):
        def header(self):
            pass

    pdf = PDFResume(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)

    # Header Name
    pdf.set_font("Helvetica", style="B", size=16)
    name = _clean_latin1(profile.personal_info.full_name or "Resume")
    pdf.cell(0, 8, name, 0, 1, "C")

    # Contact line
    pdf.set_font("Helvetica", size=9)
    contact_parts = []
    if profile.personal_info.location:
        contact_parts.append(profile.personal_info.location)
    if profile.personal_info.phone:
        contact_parts.append(profile.personal_info.phone)
    if profile.personal_info.email:
        contact_parts.append(profile.personal_info.email)
    if profile.personal_info.linkedin_url:
        contact_parts.append(profile.personal_info.linkedin_url.replace("https://", ""))
    
    if contact_parts:
        pdf.cell(0, 5, _clean_latin1(" | ".join(contact_parts)), 0, 1, "C")
    pdf.ln(3)

    def pdf_heading(title: str):
        pdf.ln(2)
        pdf.set_font("Helvetica", style="B", size=11)
        pdf.cell(0, 6, _clean_latin1(title.upper()), 0, 1, "L")
        pdf.set_font("Helvetica", size=9.5)

    # Summary
    summary = tailored.summary or profile.summary
    if summary:
        pdf_heading("Professional Summary")
        pdf.multi_cell(0, 4.5, _clean_latin1(summary))
        pdf.ln(2)

    # Skills
    skills = tailored.selected_skills
    if any([skills.technical, skills.tools]):
        pdf_heading("Skills")
        if skills.technical:
            pdf.multi_cell(0, 4.5, _clean_latin1(f"Technical: {', '.join(skills.technical)}"))
        if skills.tools:
            pdf.multi_cell(0, 4.5, _clean_latin1(f"Tools & Cloud: {', '.join(skills.tools)}"))
        pdf.ln(2)

    # Experience
    if tailored.selected_experience:
        pdf_heading("Professional Experience")
        for exp in tailored.selected_experience:
            pdf.set_font("Helvetica", style="B", size=10)
            date_str = f"{exp.start_date or ''} - {exp.end_date or ('Present' if exp.is_current else '')}"
            pdf.cell(0, 5, _clean_latin1(f"{exp.title} - {exp.company} ({date_str})"), 0, 1)
            pdf.set_font("Helvetica", size=9)
            for b in exp.bullets:
                pdf.multi_cell(0, 4.5, _clean_latin1(f"- {b.tailored_text}"))
                pdf.ln(1)
            pdf.ln(2)

    # Education
    education_list = tailored.selected_education or profile.education
    if education_list:
        pdf_heading("Education")
        for edu in education_list:
            pdf.multi_cell(0, 4.5, _clean_latin1(f"{edu.degree} in {edu.field} | {edu.institution} ({edu.graduation_date or ''})"))

    # Projects (Approved Only)
    projects_list = tailored.selected_projects or profile.get_approved_projects()
    if projects_list:
        pdf_heading("Key Projects")
        for proj in projects_list:
            pdf.set_font("Helvetica", style="B", size=9.5)
            pdf.cell(0, 5, _clean_latin1(proj.name), 0, 1)
            pdf.set_font("Helvetica", size=9)
            for b_text in proj.draft_bullets:
                pdf.multi_cell(0, 4.5, _clean_latin1(f"- {b_text}"))
                pdf.ln(1)

    pdf.output(str(out_file))
    return out_file


def export_cover_letter_to_docx(
    profile: MasterProfile,
    cover_letter: CoverLetter,
    output_path: Union[str, Path]
) -> Path:
    """
    Generates an executive single-column Word cover letter matching resume header styling.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    doc = docx.Document()

    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    style_normal = doc.styles["Normal"]
    font = style_normal.font
    font.name = "Calibri"
    font.size = Pt(11)
    font.color.rgb = RGBColor(30, 30, 30)

    # 1. Header (Candidate Contact Info)
    name = profile.personal_info.full_name or "Applicant"
    p_name = doc.add_paragraph()
    r_name = p_name.add_run(name)
    r_name.font.size = Pt(18)
    r_name.font.bold = True
    r_name.font.color.rgb = RGBColor(10, 10, 10)
    p_name.paragraph_format.space_after = Pt(2)

    contact_parts = []
    if profile.personal_info.location:
        contact_parts.append(profile.personal_info.location)
    if profile.personal_info.phone:
        contact_parts.append(profile.personal_info.phone)
    if profile.personal_info.email:
        contact_parts.append(profile.personal_info.email)
    if profile.personal_info.portfolio_url:
        contact_parts.append(profile.personal_info.portfolio_url.replace("https://", ""))

    if contact_parts:
        p_contact = doc.add_paragraph(" | ".join(contact_parts))
        p_contact.paragraph_format.space_after = Pt(18)

    # 2. Date & Recipient
    date_str = cover_letter.generated_at or ""
    if date_str:
        p_date = doc.add_paragraph(date_str)
        p_date.paragraph_format.space_after = Pt(14)

    if cover_letter.target_company:
        p_recip = doc.add_paragraph()
        p_recip.add_run(f"{cover_letter.recipient_title}\n")
        p_recip.add_run(f"{cover_letter.target_company}")
        p_recip.paragraph_format.space_after = Pt(14)

    # 3. Salutation
    p_salut = doc.add_paragraph(cover_letter.salutation or "Dear Hiring Team,")
    p_salut.paragraph_format.space_after = Pt(10)

    # 4. Opening Paragraph
    if cover_letter.opening:
        p_open = doc.add_paragraph(cover_letter.opening)
        p_open.paragraph_format.space_after = Pt(10)

    # 5. Body Paragraphs
    for body_p in cover_letter.body_paragraphs:
        p_body = doc.add_paragraph(body_p)
        p_body.paragraph_format.space_after = Pt(10)

    # 6. Closing Paragraph
    if cover_letter.closing:
        p_close = doc.add_paragraph(cover_letter.closing)
        p_close.paragraph_format.space_after = Pt(16)

    # 7. Sign-off
    p_sign = doc.add_paragraph("Sincerely,\n\n")
    r_sign_name = p_sign.add_run(name)
    r_sign_name.bold = True

    doc.save(str(out_file))
    return out_file


def export_cover_letter_to_pdf(
    profile: MasterProfile,
    cover_letter: CoverLetter,
    output_path: Union[str, Path]
) -> Path:
    """Generates clean text-layer PDF cover letter."""
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        from fpdf import FPDF
    except ImportError:
        return export_cover_letter_to_docx(profile, cover_letter, out_file.with_suffix(".docx"))

    class PDFCoverLetter(FPDF):
        def header(self):
            pass

    pdf = PDFCoverLetter(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10.5)

    # Header
    pdf.set_font("Helvetica", style="B", size=16)
    name = profile.personal_info.full_name or "Applicant"
    pdf.cell(0, 8, name, 0, 1, "L")

    pdf.set_font("Helvetica", size=9.5)
    contact_parts = []
    if profile.personal_info.location:
        contact_parts.append(profile.personal_info.location)
    if profile.personal_info.phone:
        contact_parts.append(profile.personal_info.phone)
    if profile.personal_info.email:
        contact_parts.append(profile.personal_info.email)
    if profile.personal_info.portfolio_url:
        contact_parts.append(profile.personal_info.portfolio_url.replace("https://", ""))

    if contact_parts:
        pdf.cell(0, 5, " | ".join(contact_parts), 0, 1, "L")
    pdf.ln(5)

    # Date & Recipient
    if cover_letter.generated_at:
        pdf.cell(0, 5, cover_letter.generated_at, 0, 1, "L")
        pdf.ln(2)
    if cover_letter.target_company:
        pdf.cell(0, 5, cover_letter.recipient_title, 0, 1, "L")
        pdf.cell(0, 5, cover_letter.target_company, 0, 1, "L")
    pdf.ln(4)

    # Salutation
    pdf.cell(0, 5, cover_letter.salutation or "Dear Hiring Team,", 0, 1, "L")
    pdf.ln(3)

    # Opening
    if cover_letter.opening:
        pdf.multi_cell(0, 5, cover_letter.opening)
        pdf.ln(3)

    # Body
    for p in cover_letter.body_paragraphs:
        pdf.multi_cell(0, 5, p)
        pdf.ln(3)

    # Closing
    if cover_letter.closing:
        pdf.multi_cell(0, 5, cover_letter.closing)
        pdf.ln(5)

    # Sign-off
    pdf.cell(0, 5, "Sincerely,", 0, 1, "L")
    pdf.ln(4)
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.cell(0, 5, name, 0, 1, "L")

    pdf.output(str(out_file))
    return out_file
