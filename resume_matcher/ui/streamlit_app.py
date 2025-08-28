import sys
import os
import time
from io import BytesIO
from pathlib import Path

import streamlit as st

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

# Streamlit Page Setup
st.set_page_config(page_title="Resume ↔ JD Match AI", page_icon="🧠", layout="centered")

# Hero Banner (Replace with your own banner URL if you'd like)
st.image("https://www.pexels.com/photo/man-and-woman-near-table-3184465/", use_column_width=True)

st.title("🧠 Resume ↔ Job Description Match Scoring AI")
st.caption("Upload your resume + paste a job description. Get a match score, insights, and skill suggestions.")

# Feature Overview
st.markdown("## ✨ How It Works")
st.markdown("""
1. **Upload** your resume (PDF or DOCX)  
2. **Paste** the job description  
3. Click ⚡ Score Match to get:  
   - AI match score  
   - Aligned & missing skills  
   - Targeted resume improvement tips
""")

# Tech badges
st.markdown("### 🔧 Powered By:")
st.markdown("![Python](https://img.shields.io/badge/Python-3.9-blue) ![NLP](https://img.shields.io/badge/NLP-BERT-yellowgreen) ![Streamlit](https://img.shields.io/badge/Streamlit-🎈-brightgreen)")

# User Testimonial
st.markdown("### 💬 User Feedback")
st.markdown("""> “This app helped me tailor my resume in minutes!” — Beta Tester""")

# Optional Demo Video
st.markdown("### ▶️ Demo Walkthrough")
st.video("https://www.youtube.com/watch?v=3jZ5vnv-LZc")  # Replace with your own demo link

st.markdown("---")

# Upload Section
resume_file = st.file_uploader("📄 Upload Resume (PDF or DOCX)", type=["pdf", "docx"])
jd_text = st.text_area("📝 Paste Job Description", height=220, placeholder="Paste the full job description here...")

if st.button("⚡ Score Match"):
    if not resume_file or not jd_text.strip():
        st.error("Please upload a resume and paste a job description.")
    else:
        name = resume_file.name.lower()
        with st.spinner("Scoring your resume..."):
            if name.endswith(".pdf") and pdf_extract:
                resume_text = clean_text(pdf_extract(resume_file))
            elif name.endswith(".docx") and docx2txt:
                resume_text = clean_text(docx2txt.process(resume_file))
            else:
                resume_text = clean_text(resume_file.read().decode("utf-8", errors="ignore"))

            time.sleep(1.5)

        if not resume_text:
            st.error("Could not parse the resume. Try a different file format.")
        else:
            result = compute_score(resume_text, jd_text, ONTOLOGY_PATH)
            st.success("✅ Match analysis complete!")

            st.markdown("## 🧾 Results")
            st.metric("Match Score", f"{result['total_score']}/100")
            st.markdown("### 📊 Subscores")
            st.json(result["subscores"])

            st.markdown("### ✅ Aligned Skills")
            st.write(", ".join(result["aligned_skills"]) or "—")

            st.markdown("### ⚠️ Missing Skills (Targets)")
            st.write(", ".join([x["term"] for x in result["missing_skills"]]) or "—")

st.markdown("---")
st.caption("Built with 💡 by Fali Dillys Honutse | GitHub: [falidill](https://github.com/falidill)")
