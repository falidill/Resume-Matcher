import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import streamlit as st
from io import BytesIO
from pathlib import Path

from scoring.ensemble_scoring import compute_score, clean_text


try:
    from pdfminer.high_level import extract_text as pdf_extract
except Exception:
    pdf_extract = None

try:
    import docx2txt
except Exception:
    docx2txt = None

ONTOLOGY_PATH = Path(__file__).resolve().parents[2] / "data" / "skills_ontology.json"

st.set_page_config(page_title="Resume ↔ JD Match AI", page_icon="🧠", layout="centered")
st.title("🧠 Resume ↔ Job Description Match Scoring AI")
st.caption("Upload your resume + paste a job description. Get a match score, insights, and skill suggestions.")

resume_file = st.file_uploader("Upload Resume (PDF or DOCX)", type=["pdf", "docx"])
jd_text = st.text_area("Paste Job Description", height=220, placeholder="Paste the full job description here...")

if st.button("⚡ Score Match"):
    if not resume_file or not jd_text.strip():
        st.error("Please upload a resume and paste a job description.")
    else:
        name = resume_file.name.lower()
        if name.endswith(".pdf") and pdf_extract:
            resume_text = clean_text(pdf_extract(resume_file))
        elif name.endswith(".docx") and docx2txt:
            resume_text = clean_text(docx2txt.process(resume_file))
        else:
            resume_text = clean_text(resume_file.read().decode("utf-8", errors="ignore"))

        if not resume_text:
            st.error("Could not parse the resume. Try a different file format.")
        else:
            result = compute_score(resume_text, jd_text, ONTOLOGY_PATH)
            st.subheader("Results")
            st.metric("Match Score", f"{result['total_score']}/100")
            st.write("**Subscores**")
            st.json(result["subscores"])
            st.write("**Aligned Skills**")
            st.write(", ".join(result["aligned_skills"]) or "—")
            st.write("**Missing Skills (Targets)**")
            st.write(", ".join([x["term"] for x in result["missing_skills"]]) or "—")
