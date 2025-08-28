# streamlit_app.py — Clean Resume Matcher with Modern Design

import sys
import os
import re
import json
import datetime as dt
from pathlib import Path

import streamlit as st
import pandas as pd

# Make the local package importable (repo root two levels up from this file)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from resume_matcher.scoring.ensemble_scoring import compute_score, clean_text

# Optional parsers
try:
    from pdfminer.high_level import extract_text as pdf_extract
except Exception:
    pdf_extract = None

try:
    import docx2txt
except Exception:
    docx2txt = None

# -------------------------------------------------------------------
# Paths / Page config
# -------------------------------------------------------------------
ONTOLOGY_PATH = Path(__file__).resolve().parents[2] / "data" / "skills_ontology.json"
st.set_page_config(
    page_title="Resume Matcher - AI-Powered Resume Analysis", 
    page_icon="🎯", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------------
# Modern Styles
# -------------------------------------------------------------------
MODERN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.stApp {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    font-family: 'Inter', sans-serif;
}

.main-container {
    background: white;
    border-radius: 20px;
    padding: 3rem;
    margin: 2rem auto;
    max-width: 1200px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
}

.hero-section {
    text-align: center;
    margin-bottom: 3rem;
}

.hero-title {
    font-size: 3.5rem;
    font-weight: 700;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 1rem;
}

.hero-subtitle {
    font-size: 1.25rem;
    color: #6b7280;
    font-weight: 400;
    max-width: 600px;
    margin: 0 auto;
}

.upload-section {
    background: #f8fafc;
    border-radius: 16px;
    padding: 2rem;
    margin: 2rem 0;
    border: 2px dashed #e2e8f0;
    transition: all 0.3s ease;
}

.upload-section:hover {
    border-color: #667eea;
    background: #f1f5ff;
}

.score-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 20px;
    padding: 3rem;
    text-align: center;
    color: white;
    margin: 2rem 0;
    box-shadow: 0 15px 30px rgba(102, 126, 234, 0.3);
}

.score-number {
    font-size: 4rem;
    font-weight: 800;
    margin-bottom: 1rem;
}

.score-label {
    font-size: 1.25rem;
    opacity: 0.9;
    font-weight: 500;
}

.metric-card {
    background: white;
    border-radius: 16px;
    padding: 2rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    border: 1px solid #f1f5f9;
    transition: all 0.3s ease;
    height: 100%;
}

.metric-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.15);
}

.metric-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #374151;
    margin-bottom: 1rem;
}

.metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #667eea;
}

.chip { 
    display: inline-block; 
    padding: 8px 16px; 
    margin: 6px 8px 6px 0; 
    border-radius: 50px; 
    font-size: 0.9rem; 
    font-weight: 500;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
}

.skills-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: center;
    margin-top: 1rem;
}

.cta-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 50px;
    padding: 1rem 3rem;
    font-size: 1.1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.cta-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.6);
}

.footer {
    text-align: center;
    padding: 2rem;
    color: #6b7280;
    font-size: 0.9rem;
}

.footer a {
    color: #667eea;
    text-decoration: none;
    font-weight: 500;
}

/* Hide Streamlit default elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}

/* Custom file uploader */
.stFileUploader > div > div > div {
    background: transparent;
    border: none;
}

.stTextArea > div > div > textarea {
    border-radius: 12px;
    border: 2px solid #e2e8f0;
    font-family: 'Inter', sans-serif;
}

.stTextArea > div > div > textarea:focus {
    border-color: #667eea;
    box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}
</style>
"""

st.markdown(MODERN_CSS, unsafe_allow_html=True)

# -------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------
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

def render_skills_chips(skills):
    if not skills:
        return "<p style='text-align: center; color: #6b7280;'>No skills detected</p>"
    
    chips_html = "<div class='skills-grid'>"
    for skill in skills[:20]:  # Limit to first 20 skills
        chips_html += f"<span class='chip'>✓ {skill}</span>"
    chips_html += "</div>"
    return chips_html

# Session state
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

# -------------------------------------------------------------------
# Hero Section
# -------------------------------------------------------------------
st.markdown("""
<div class="main-container">
    <div class="hero-section">
        <h1 class="hero-title">Resume Matcher</h1>
        <p class="hero-subtitle">
            Get instant AI-powered analysis of how well your resume matches job descriptions. 
            Improve your chances of landing interviews with data-driven insights.
        </p>
    </div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# Upload Section
# -------------------------------------------------------------------
if not st.session_state.analysis_done:
    st.markdown("""
    <div class="upload-section">
        <h3 style="text-align: center; color: #374151; margin-bottom: 2rem;">Upload Your Documents</h3>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("### 📄 Resume")
        resume_file = st.file_uploader(
            "Upload your resume", 
            type=["pdf", "docx", "txt"], 
            help="Supported formats: PDF, DOCX, TXT",
            label_visibility="collapsed"
        )
        
    with col2:
        st.markdown("### 📋 Job Description")
        jd_text = st.text_area(
            "Paste the job description here", 
            height=200, 
            placeholder="Paste the complete job description here...",
            label_visibility="collapsed"
        )

    # Analyze button
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_clicked = st.button("🎯 Analyze Match", type="primary", use_container_width=True)

    # Analysis
    if analyze_clicked:
        if not resume_file or not jd_text.strip():
            st.error("⚠️ Please upload both a resume and job description to continue.")
        else:
            with st.spinner("🔄 Analyzing your resume match..."):
                # Clean JD text
                jd_text_clean = clean_text(jd_text or "")
                
                # Extract resume text
                resume_text = extract_resume_text(resume_file)
                if not resume_text:
                    st.error("❌ Could not extract text from your resume. Please try a different format.")
                    st.stop()

                # Get scoring results
                result = compute_score(resume_text, jd_text_clean, ONTOLOGY_PATH)
                
                # Store results in session state
                st.session_state.analysis_result = result
                st.session_state.analysis_done = True
                st.session_state.resume_name = resume_file.name
                st.rerun()

# -------------------------------------------------------------------
# Results Section
# -------------------------------------------------------------------
if st.session_state.analysis_done and "analysis_result" in st.session_state:
    result = st.session_state.analysis_result
    
    # Calculate overall score
    subs = result.get("subscores", {}) or {}
    kw = subs.get("keyword_alignment", 0)
    ev = subs.get("evidence", 0) 
    emb = subs.get("embedding_similarity", 0)
    cov = subs.get("skills_coverage", 0)
    
    # Weighted score calculation
    overall_score = round(0.30*kw + 0.30*ev + 0.25*emb + 0.15*cov, 1)
    score_int = int(round(overall_score))
    
    # Score section
    st.markdown(f"""
    <div class="score-container">
        <div class="score-number">{score_int}%</div>
        <div class="score-label">Resume Match Score</div>
        <p style="margin-top: 1rem; opacity: 0.8;">
            {"🎉 Excellent match! Your resume aligns very well with this job." if score_int >= 80 
             else "✅ Good match! Consider minor improvements for better alignment." if score_int >= 60
             else "📝 Room for improvement. Focus on adding relevant skills and experience." if score_int >= 40
             else "🔄 Significant improvements needed. Consider major resume updates."}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Detailed metrics
    st.markdown("### 📊 Detailed Analysis")
    
    metrics_data = [
        ("Keyword Alignment", kw, "How well your resume keywords match the job requirements"),
        ("Evidence Quality", ev, "Strength of examples and achievements in your resume"),
        ("Content Similarity", emb, "Overall semantic similarity between resume and job description"),
        ("Skills Coverage", cov, "Percentage of required skills present in your resume")
    ]
    
    cols = st.columns(2)
    for i, (title, value, description) in enumerate(metrics_data):
        with cols[i % 2]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">{title}</div>
                <div class="metric-value">{value:.1f}%</div>
                <p style="color: #6b7280; font-size: 0.9rem; margin-top: 0.5rem;">{description}</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
    
    # Matched skills section
    aligned_skills = result.get("aligned_skills", [])
    if aligned_skills:
        st.markdown("### ✅ Matched Skills & Keywords")
        st.markdown(f"""
        <div style="background: #f8fafc; padding: 2rem; border-radius: 16px; border-left: 4px solid #10b981;">
            <p style="color: #374151; margin-bottom: 1rem;">
                <strong>{len(aligned_skills)} skills</strong> from the job description were found in your resume:
            </p>
            {render_skills_chips(aligned_skills)}
        </div>
        """, unsafe_allow_html=True)
    
    # Action buttons
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Analyze Another Resume", use_container_width=True):
            st.session_state.analysis_done = False
            st.session_state.analysis_result = {}
            st.rerun()

# Footer
st.markdown("""
</div>

<div class="footer">
    <p>Built with ❤️ to help job seekers succeed</p>
    <p>
        Created by <a href="https://www.linkedin.com/in/fali-dillys-honutse/" target="_blank">Fali Honutse</a> | 
        <a href="https://falidill-portfoliowebsite.vercel.app/" target="_blank">Portfolio</a>
    </p>
    <p style="font-size: 0.8rem; color: #9ca3af; margin-top: 1rem;">
        Forked and modified from <a href="https://github.com/srbhr/Resume-Matcher" target="_blank">srbhr/Resume-Matcher</a> (Apache 2.0 License)
    </p>
</div>
""", unsafe_allow_html=True)