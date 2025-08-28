# streamlit_app.py — improved UX with footer and branding

import sys
import os
import re
import json
import datetime as dt
from io import BytesIO
from pathlib import Path

import streamlit as st
import pandas as pd

# Make the local package importable (repo root two levels up from this file)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from resume_matcher.scoring.ensemble_scoring import compute_score, clean_text

try:
    from pdfminer.high_level import extract_text as pdf_extract
except Exception:
    pdf_extract = None

try:
    import docx2txt
except Exception:
    docx2txt = None

ONTOLOGY_PATH = Path(__file__).resolve().parents[2] / "data" / "skills_ontology.json"
st.set_page_config(page_title="Resume ⇄ JD Match Tool", page_icon="🧠", layout="wide")

CHIP_CSS = """
<style>
.chip { display:inline-block; padding:6px 10px; margin:4px 6px 0 0; border-radius:16px; font-size:0.85rem; border:1px solid rgba(0,0,0,0.06) }
.chip.ok { background:#e8f5e9; color:#1b5e20; border-color:#c8e6c9; }
.chip.miss { background:#fff3e0; color:#bf360c; border-color:#ffe0b2; }
.scorebar { height:10px; border-radius:8px; background:#eee; overflow:hidden; }
.scorefill { height:10px; border-radius:8px; }
.small { color:#666; font-size:0.85rem; }
</style>
"""
st.markdown(CHIP_CSS, unsafe_allow_html=True)


# st.markdown(
#     """
# <div class="block-card" style="text-align:center; padding:28px 20px; margin: 6px 0 16px">
#   <div class="h1">🧠 Resume Matcher</div>
#   <div class="sub">No more guessing — see how well your resume matches the job description.</div>
#   <div class="small">Clear, fast, and private • No login required</div>
# </div>
# """,
#     unsafe_allow_html=True
# )


st.markdown(
    """
<div style="padding:1.6rem; background:linear-gradient(90deg,#2c3e50,#8e44ad); border-radius:16px; text-align:center; margin-bottom:1rem">
  <h1 style="color:#fff; margin:0 0 .3rem 0">🧠 Resume Matcher</h1>
  <p style="color:#e6e6e6; margin:0">No more guessing — see how well your resume matches the job description.</p>
</div>
""",
    unsafe_allow_html=True
)

with st.sidebar:
    st.header("Options")
    privacy = st.checkbox("Delete processed text after scoring (privacy-first)", value=True)
    show_ats = st.checkbox("Run ATS-lite checks", value=True)
    show_history = st.checkbox("Keep session history (last 5)", value=True)
    st.caption("We do not store your documents by default. Keep the Apache-2.0 license & attribution from the base repo.")

col1, col2 = st.columns(2)
with col1:
    resume_file = st.file_uploader("📄 Upload Resume (PDF / DOCX / TXT)", type=["pdf", "docx", "txt"], help="Prefer a one-column ATS-friendly layout.")
with col2:
    jd_text = st.text_area("📋 Paste Job Description", height=280, placeholder="Paste the full job description here…")

def extract_resume_text(uploaded_file) -> str:
    if not uploaded_file:
        return ""
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".pdf") and pdf_extract:
            return clean_text(pdf_extract(uploaded_file))
        if name.endswith(".docx") and docx2txt:
            return clean_text(docx2txt.process(uploaded_file))
        return clean_text(uploaded_file.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        st.error(f"Could not read the resume: {e}. Try uploading a different format.")
        return ""

def ats_lite_findings(resume_txt: str):
    findings = []
    if re.search(r"\b(table|grid|columns?)\b", resume_txt, flags=re.I):
        findings.append("Layout may include tables/columns — some ATS parsers can misread complex layouts.")
    if not re.search(r"\b(?:\+?\d[\d\-\s\(\)]{7,})\b", resume_txt):
        findings.append("Phone number not clearly detected.")
    if not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", resume_txt):
        findings.append("Email address not clearly detected.")
    if not re.search(r"(20\d{2}|\bpresent\b|\bcurrent\b)", resume_txt, flags=re.I):
        findings.append("Employment dates not obvious (e.g., 2022–2024 / Present).")
    return findings

def render_chips(items, ok=True):
    css = "ok" if ok else "miss"
    if not items:
        return st.caption("None detected.")
    chips_html = "".join([f"<span class='chip {css}'>" + ("✅ " if ok else "⚠ ") + str(it) + "</span>" for it in items])
    st.markdown(chips_html, unsafe_allow_html=True)

def quick_suggestions(missing_terms):
    out = []
    templates = [
        "Implemented {term} to improve reporting speed by X%.",
        "Built {term} workflows for stakeholders, reducing manual effort by X%.",
        "Analyzed {term} data to inform decisions, resulting in measurable impact.",
        "Automated {term}-related tasks using Python, cutting cycle time by X%."
    ]
    for i, t in enumerate(missing_terms[:12]):
        term = t["term"] if isinstance(t, dict) and "term" in t else str(t)
        out.append(f"• {templates[i % len(templates)].format(term=term)}")
    return "\n".join(out) if out else "No suggestions — strong match."

if "history" not in st.session_state:
    st.session_state.history = []

run = st.button("⚡ Check Match", type="primary", use_container_width=True)
if run:
    if not resume_file or not jd_text.strip():
        st.error("Please upload a resume and paste a job description.")
        st.stop()

    progress = st.progress(0)
    with st.spinner("Analyzing your resume against the job description…"):
        for i in range(1, 51):
            progress.progress(i * 2)
        resume_text = extract_resume_text(resume_file)
        if not resume_text:
            st.stop()
        result = compute_score(resume_text, jd_text, ONTOLOGY_PATH)

    st.markdown("### 📊 Match Results")
    score = int(result.get("total_score", 0))
    color = "#e53935" if score < 50 else "#fb8c00" if score < 70 else "#43a047"

    st.markdown(
        f"""
<div style="display:flex;align-items:center;gap:.75rem; margin:.25rem 0 1rem 0;">
  <div style="font-size:2.25rem;font-weight:800;color:{color}">{score}/100</div>
  <div class="scorebar" style="flex:1;">
    <div class="scorefill" style="width:{score}%; background:{color};"></div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    subs = result.get("subscores", {})
    if isinstance(subs, dict) and subs:
        df = pd.DataFrame([{"Area": k, "Score": v} for k, v in subs.items()]).sort_values("Score", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No subscore breakdown available.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### ✅ Matched skills/keywords")
        matched = result.get("aligned_skills", [])
        render_chips(matched, ok=True)
    with c2:
        st.markdown("#### ⚠ Missing or weakly covered")
        raw_missing = result.get("missing_skills", [])
        missing_terms = [m["term"] if isinstance(m, dict) and "term" in m else str(m) for m in raw_missing]
        render_chips(missing_terms, ok=False)

    st.markdown("#### ✍️ Quick bullet ideas (use only if accurate)")
    suggestions_text = quick_suggestions(raw_missing)
    st.text_area("Copy suggestions", value=suggestions_text, height=170)
    st.code(suggestions_text, language='markdown')
    st.button("📋 Copy suggestions to clipboard")

    if show_ats:
        st.markdown("#### 🧪 ATS-lite checks")
        hints = ats_lite_findings(resume_text)
        if hints:
            for h in hints:
                st.write("•", h)
        else:
            st.write("Looks ATS-friendly at a glance.")

    if suggestions_text and suggestions_text.strip():
        st.download_button(
            "⬇️ Download suggestions.txt",
            data=suggestions_text.encode("utf-8"),
            file_name="resume_match_suggestions.txt",
            mime="text/plain",
            use_container_width=True,
        )

    if show_history:
        st.session_state.history.insert(0, {
            "Time": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Score": score,
            "Matched": len(result.get("aligned_skills", [])),
            "Missing": len(missing_terms),
            "Resume": resume_file.name,
        })
        st.session_state.history = st.session_state.history[:5]
        with st.expander("🕘 Recent matches (this session)"):
            st.table(pd.DataFrame(st.session_state.history))

    if privacy:
        resume_text = ""
        suggestions_text = ""

st.markdown("---")
st.markdown(
    """
    <div style="text-align:center; font-size: 0.95rem; color: #cbd5e1;">
        Built with ❤️ to help job seekers<br>
        Created by 
        <a href="https://www.linkedin.com/in/fali-dillys-honutse/" target="_blank" style="color:#22D3EE; text-decoration: none;">Fali Honutse</a> 
        &nbsp;|&nbsp; 
        <a href="https://falidill-portfoliowebsite.vercel.app/" target="_blank" style="color:#22D3EE; text-decoration: none;">Portfolio</a>
        <br><span style="color:#94a3b8;">Forked and modified from 
        <a href="https://github.com/srbhr/Resume-Matcher" target="_blank" style="color:#94a3b8;">srbhr/Resume-Matcher</a> (Apache 2.0 License)</span>
    </div>
    """,
    unsafe_allow_html=True
)



# st.markdown("---")
# st.markdown(
#     """
#     <div style="text-align: center; font-size: 0.9rem; color: #555;">
#         Created with ❤️ by <a href="https://www.linkedin.com/in/fali-dillys-honutse/" target="_blank" style="color:#6c63ff; text-decoration: none;">Fali Honutse</a> |
#         <a href="https://falidill-portfoliowebsite.vercel.app/" target="_blank" style="color:#6c63ff; text-decoration: none;">My Portfolio</a><br>
#         Forked and modified from <a href="https://github.com/srbhr/Resume-Matcher" target="_blank" style="color:#888;">srbhr/Resume-Matcher</a> under Apache 2.0 License.
#     </div>
#     """,
#     unsafe_allow_html=True
# )

# st.markdown("---")
# st.markdown(
#     """
#     <style>
#     .footer-btn {
#         display:inline-block;
#         padding:6px 14px;
#         margin:4px 6px;
#         border-radius:20px;
#         font-size:0.9rem;
#         font-weight:500;
#         text-decoration:none;
#         transition:all 0.2s ease;
#     }
#     .footer-btn.portfolio {background:#7C3AED; color:white;}
#     .footer-btn.linkedin {background:#22D3EE; color:#0F172A;}
#     .footer-btn:hover {opacity:0.85; transform:translateY(-1px);}
#     </style>

#     <div style="text-align:center; font-size: 0.95rem; color: #cbd5e1;">
#         Built with ❤️ to help job seekers<br><br>

#         <a href="https://www.linkedin.com/in/fali-dillys-honutse/" target="_blank" class="footer-btn linkedin">LinkedIn</a>
#         <a href="https://falidill-portfoliowebsite.vercel.app/" target="_blank" class="footer-btn portfolio">Portfolio</a>

#         <br><br><span style="color:#94a3b8;">Forked and modified from 
#         <a href="https://github.com/srbhr/Resume-Matcher" target="_blank" style="color:#94a3b8; text-decoration:none;">srbhr/Resume-Matcher</a> (Apache 2.0 License)</span>
#     </div>
#     """,
#     unsafe_allow_html=True
# )
