import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import streamlit as st
from io import BytesIO
from pathlib import Path

from resume_matcher.scoring.ensemble_scoring import compute_score, clean_text
try:
    from pdfminer.high_level import extract_text as pdf_extract
except Exception:
    pdf_extract = None

try:
    import docx2txt
except Exception:
    docx2txt = None

# Path to the skills ontology
ONTOLOGY_PATH = Path(__file__).resolve().parents[2] / "data" / "skills_ontology.json"

# Configure Streamlit page
st.set_page_config(page_title="Resume Match Scorer", page_icon="🧠", layout="centered")

# --- Hero Section ---
st.markdown(
    """
    <div style='
        text-align: center;
        padding: 2rem;
        background: linear-gradient(90deg, #2c3e50, #8e44ad);
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        margin-bottom: 2rem;
    '>
        <h1 style='color: #ffffff; font-size: 2.8rem; margin-bottom: 0.5rem;'>🧠 Resume ⇄ JD Match Tool</h1>
        <p style='color: #e0e0e0; font-size: 1.1rem;'>Get clarity on how your resume aligns with your dream role.</p>
        <p style='color: #d0d0d0; font-size: 0.95rem;'>Upload your resume, paste the job description, and see your score.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Upload + Input Section ---
resume_file = st.file_uploader("📄 Upload Resume (PDF or DOCX)", type=["pdf", "docx"])
jd_text = st.text_area("📋 Paste Job Description", height=240, placeholder="Paste the job description you're applying to...")

# --- Scoring Button ---
if st.button("⚡ Check Match"):
    if not resume_file or not jd_text.strip():
        st.error("Please upload a resume and paste a job description first.")
    else:
        filename = resume_file.name.lower()

        if filename.endswith(".pdf") and pdf_extract:
            resume_text = clean_text(pdf_extract(resume_file))
        elif filename.endswith(".docx") and docx2txt:
            resume_text = clean_text(docx2txt.process(resume_file))
        else:
            resume_text = clean_text(resume_file.read().decode("utf-8", errors="ignore"))

        if not resume_text:
            st.error("We couldn't parse your resume. Try uploading a different format.")
        else:
            result = compute_score(resume_text, jd_text, ONTOLOGY_PATH)

            # --- Output Section ---
            st.markdown("## 📊 Match Results")
            st.metric("Overall Match Score", f"{result['total_score']} / 100")

            st.markdown("### 🧩 Skill Breakdown")
            st.write("**Subscores**")
            st.json(result["subscores"])

            st.write("**✅ Matching Skills**")
            st.write(", ".join(result["aligned_skills"]) or "—")

            st.write("**🔍 Skills You May Want to Add**")
            st.write(", ".join([x["term"] for x in result["missing_skills"]]) or "—")
