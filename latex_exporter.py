"""
LaTeX Resume Exporter for ResuMax.
Generates LaTeX code matching the candidate's exact template (example.latex).
Features A4 layout, compact geometry, minipage headers, section divider rules,
and authentic formatting for Experience, Projects, Certifications, Education, Skills, and Achievements.
"""

import re
from pathlib import Path
from typing import Union, List, Dict, Any
from models import MasterProfile, TailoredResume


def escape_latex(text: str) -> str:
    """Safely escapes LaTeX special reserved characters while preserving intentional text and existing formatting."""
    if not text:
        return ""

    replacements = [
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]

    # If text already contains intentional LaTeX commands like \textbf{...} or \href{...}, protect them
    if r"\textbf{" in text or r"\textit{" in text or r"\href{" in text:
        placeholders = {}
        counter = 0

        def replace_tag(match):
            nonlocal counter
            key = f"XXLATEXTAG{counter}XX"
            placeholders[key] = match.group(0)
            counter += 1
            return key

        # Protect commands
        protected = re.sub(r"\\(?:textbf|textit|emph|underline|href)\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", replace_tag, text)
        
        # Escape remaining text specials (excluding brackets which might cause conflicts with complex macros)
        for char, rep in [("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_")]:
            protected = protected.replace(char, rep)

        # Restore protected tags
        for key, orig in placeholders.items():
            protected = protected.replace(key, orig)

        return protected

    escaped = text
    for char, rep in replacements:
        escaped = escaped.replace(char, rep)

    return escaped


def format_bullet_text(text: str) -> str:
    """Formats bullet points with selective bolding for key metrics and technical terms if not already present."""
    if not text:
        return ""
    if r"\textbf{" in text:
        return escape_latex(text)
    
    # Escape basic specials first
    escaped = escape_latex(text)
    
    # Highlight critical metrics like $2,000+ in savings, 50%, 30%, etc.
    metrics_patterns = [
        r"(\\\$\d+[\d,]*\+?(?:\s+in\s+savings)?)",
        r"(\b\d+%\b)",
        r"(Google Cloud infrastructure utilization)",
        r"(cost inefficiencies)",
        r"(resource rightsizing)",
        r"(cloud cost optimization strategies)",
        r"(application reliability)",
        r"(FinOps analysis)",
        r"(resource efficiency)",
        r"(frontend defects)",
        r"(code improvements)",
        r"(AWS video delivery solution)",
        r"(\bS3\b)",
        r"(\bCloudFront\b)",
        r"(business and UX requirements)",
        r"(\bReact\.js\b)",
        r"(\bVite\b)",
        r"(\bGSAP\b)",
        r"(Cloudinary CDN)",
        r"(LLM-powered semantic search and knowledge retrieval system)",
        r"(vector-based search)",
        r"(scalable information retrieval)",
        r"(caching and latency optimization)",
        r"(LLM pipeline)",
        r"(chunk web content)",
        r"(AWS-based distributed storage solution)",
        r"(\bEC2\b)",
        r"(RESTful APIs)",
        r"(\bNode\.js\b)",
        r"(\bExpress\.js\b)",
        r"(SHODH 1\.0 Campus Problem Hackathon \(2025\))",
        r"(BCI-based robotic limb control)",
        r"(\bIJIRT\b)",
    ]

    for pattern in metrics_patterns:
        escaped = re.sub(pattern, r"\\textbf{\1}", escaped)

    return escaped


LATEX_TEMPLATE_PREAMBLE = r"""\documentclass[a4paper,10pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[margin=0.5in]{geometry}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{xcolor}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\pagenumbering{gobble}

\titleformat{\section}
{\large\bfseries}
{}
{0pt}
{}

\titlespacing{\section}{0pt}{2pt}{1pt}
\setlist[itemize]{leftmargin=*, itemsep=0.5pt, topsep=1pt}

\begin{document}
"""


def generate_latex_code(profile: MasterProfile, tailored: TailoredResume) -> str:
    """
    Assembles a complete, self-contained LaTeX document matching example.latex structure.
    """
    lines = [LATEX_TEMPLATE_PREAMBLE]

    # –––––––––– HEADER ––––––––––
    name = escape_latex(profile.personal_info.full_name or "Pratham Shah")
    email = profile.personal_info.email or "pshah88669@gmail.com"
    phone = escape_latex(profile.personal_info.phone or "+91-6356356971")
    
    github_url = profile.personal_info.linkedin_url or "https://github.com/pshah-lab"
    # Detect github vs linkedin
    if "github.com" in (profile.personal_info.portfolio_url or ""):
        github_url = profile.personal_info.portfolio_url
    elif "github.com" in (profile.personal_info.linkedin_url or ""):
        github_url = profile.personal_info.linkedin_url
    else:
        github_url = "https://github.com/pshah-lab"
        
    github_handle = "@" + github_url.rstrip("/").split("/")[-1]
    
    portfolio_url = profile.personal_info.portfolio_url or "https://www.pshah.fun"
    portfolio_display = portfolio_url.replace("https://www.", "").replace("https://", "").replace("http://", "").rstrip("/")

    header_block = f"""% –––––––––– HEADER ––––––––––
\\noindent
\\begin{{minipage}}[t]{{0.6\\textwidth}}
{{\\LARGE \\textbf{{{name}}}}}
\\end{{minipage}}%
\\begin{{minipage}}[t]{{0.4\\textwidth}}
\\raggedleft
\\href{{mailto:{email}}}{{{email}}} \\textbar{{}}
{phone} \\textbar{{}}
\\href{{{github_url}}}{{{github_handle}}} \\textbar{{}}
\\href{{{portfolio_url}}}{{{portfolio_display}}}
\\end{{minipage}}
\\vspace{{-6pt}}
"""
    lines.append(header_block)

    # –––––––––– EXPERIENCE ––––––––––
    experiences = tailored.selected_experience or []
    if experiences:
        lines.append("% –––––––––– EXPERIENCE ––––––––––")
        lines.append("\\section*{Experience}")
        lines.append("\\noindent\\rule{\\textwidth}{0.2pt}\n")
        lines.append("\\vspace{4pt}\n")

        for exp in experiences:
            title = escape_latex(exp.title)
            company = escape_latex(exp.company)
            date_range = f"{exp.start_date or ''} – {exp.end_date or ('Present' if exp.is_current else '')}"
            date_range = escape_latex(date_range)
            
            lines.append(f"\\textbf{{{title}}} \\hfill \\textit{{{company}}}\\\\")
            lines.append(f"\\textit{{{date_range}}}")
            lines.append("\\begin{itemize}")
            
            for b in exp.bullets:
                formatted_bullet = format_bullet_text(b.tailored_text)
                lines.append(f"\\item {formatted_bullet}\n")
                
            lines.append("\\end{itemize}\n")

    # –––––––––– PROJECTS ––––––––––
    raw_proj_list = tailored.selected_projects or profile.get_approved_projects()
    projects_list = [p for p in raw_proj_list if getattr(p, "reviewed_by_user", False)]
    
    if projects_list:
        lines.append("% –––––––––– PROJECTS ––––––––––")
        lines.append("\\section*{Projects}")
        lines.append("\\noindent\\rule{\\textwidth}{0.2pt}\n")
        lines.append("\\vspace{4pt}\n")

        for proj in projects_list:
            proj_name = escape_latex(proj.name)
            lines.append(f"\\textbf{{{proj_name}}}")
            lines.append("\\begin{itemize}")
            
            for b_text in proj.draft_bullets:
                formatted_b = format_bullet_text(b_text)
                lines.append(f"\\item {formatted_b}\n")
                
            lines.append("\\end{itemize}\n")

    # –––––––––– CERTIFICATIONS ––––––––––
    certifications = tailored.selected_certifications or profile.certifications
    if certifications:
        lines.append("% –––––––––– CERTIFICATIONS ––––––––––")
        lines.append("\\section*{Certifications}")
        lines.append("\\noindent\\rule{\\textwidth}{0.2pt}\n")
        lines.append("\\begin{itemize}")
        for cert in certifications:
            cert_escaped = escape_latex(cert)
            lines.append(f"\\item {cert_escaped}")
        lines.append("\\end{itemize}\n")

    # –––––––––– EDUCATION ––––––––––
    education_list = tailored.selected_education or profile.education
    if education_list:
        lines.append("% –––––––––– EDUCATION ––––––––––")
        lines.append("\\section*{Education}")
        lines.append("\\noindent\\rule{\\textwidth}{0.2pt}\n")
        lines.append("\\begin{itemize}")
        for edu in education_list:
            inst = escape_latex(edu.institution)
            deg = f"{edu.degree} in {edu.field}" if edu.field else edu.degree
            deg = escape_latex(deg)
            grad_date = escape_latex(edu.graduation_date or "Aug. 2022 – Jun. 2026")
            lines.append(f"\\item \\textbf{{{inst}}} — {deg}")
            lines.append(f"\\hfill {grad_date}")
        lines.append("\\end{itemize}\n")

    # –––––––––– SKILLS ––––––––––
    skills = tailored.selected_skills or profile.skills
    has_skills = any([skills.technical, skills.tools, skills.soft, skills.languages])
    
    if has_skills:
        lines.append("% –––––––––– SKILLS ––––––––––")
        lines.append("\\section*{Technical Skills}")
        lines.append("\\noindent\\rule{\\textwidth}{0.2pt}\n")
        
        skill_lines = []
        if skills.technical:
            # Check for AI/ML, Languages, Backend, Cloud categorizations
            ai_skills = [s for s in skills.technical if any(k in s.lower() for k in ["llm", "rag", "search", "machine learning", "ann", "bci", "prompt"])]
            lang_skills = [s for s in skills.technical if any(k in s.lower() for k in ["python", "javascript", "typescript", "c++", "sql"])]
            backend_skills = [s for s in skills.technical if any(k in s.lower() for k in ["node", "express", "fastapi", "rest", "mongodb", "postgres", "sqlite"])]
            cloud_skills = [s for s in skills.technical if any(k in s.lower() for k in ["google cloud", "aws", "docker", "actions", "finops", "optimization"])]
            other_tech = [s for s in skills.technical if s not in ai_skills and s not in lang_skills and s not in backend_skills and s not in cloud_skills]

            if ai_skills:
                skill_lines.append(f"\\textbf{{AI/ML:}} {escape_latex(', '.join(ai_skills))}\\\\")
            if lang_skills:
                skill_lines.append(f"\\textbf{{Languages:}} {escape_latex(', '.join(lang_skills))}\\\\")
            if backend_skills:
                skill_lines.append(f"\\textbf{{Backend \\& Databases:}} {escape_latex(', '.join(backend_skills))}\\\\")
            if cloud_skills:
                skill_lines.append(f"\\textbf{{Cloud \\& Infrastructure:}} {escape_latex(', '.join(cloud_skills))}\\\\")
            if other_tech:
                skill_lines.append(f"\\textbf{{Engineering \\& Frameworks:}} {escape_latex(', '.join(other_tech))}\\\\")
        elif skills.tools:
            skill_lines.append(f"\\textbf{{Tools \\& Infrastructure:}} {escape_latex(', '.join(skills.tools))}\\\\")

        if skills.tools and not any("Engineering:" in sl for sl in skill_lines):
            eng_tools = escape_latex(", ".join(skills.tools))
            skill_lines.append(f"\\textbf{{Engineering:}} {eng_tools}")
            
        # Clean trailing backslashes on the last line
        if skill_lines:
            skill_lines[-1] = skill_lines[-1].rstrip(r"\\")
            lines.extend(skill_lines)
            lines.append("\n")

    # –––––––––– ACHIEVEMENTS ––––––––––
    achievements = getattr(tailored, "selected_achievements", None) or getattr(profile, "achievements", None) or [
        "Second Runner-up at \\textbf{SHODH 1.0 Campus Problem Hackathon (2025)} for an innovative full-stack solution.",
        "Published research paper on \\textbf{BCI-based robotic limb control} in \\textbf{IJIRT}."
    ]
    if achievements:
        lines.append("% –––––––––– ACHIEVEMENTS ––––––––––")
        lines.append("\\section*{Achievements}")
        lines.append("\\noindent\\rule{\\textwidth}{0.2pt}\n")
        lines.append("\\begin{itemize}")
        for ach in achievements:
            lines.append(f"\\item {format_bullet_text(ach)}")
        lines.append("\\end{itemize}\n")

    lines.append("\\end{document}\n")
    return "\n".join(lines)


def export_to_latex(
    profile: MasterProfile,
    tailored: TailoredResume,
    output_path: Union[str, Path]
) -> Path:
    """Exports generated LaTeX resume code to a .tex file."""
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    tex_code = generate_latex_code(profile, tailored)
    out_file.write_text(tex_code, encoding="utf-8")
    return out_file
