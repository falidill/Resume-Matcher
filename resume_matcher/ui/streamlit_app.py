# streamlit_app.py — Modern Resume Matcher with Dark Theme

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
    page_icon="✨", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# -------------------------------------------------------------------
# Dark Modern Theme CSS
# -------------------------------------------------------------------
DARK_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Global Styles */
.stApp {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    font-family: 'Inter', sans-serif;
    color: #ffffff;
}

/* Navigation */
.nav-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem 3rem;
    background: rgba(26, 26, 46, 0.9);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 1000;
}

.logo {
    display: flex;
    align-items: center;
    font-size: 1.5rem;
    font-weight: 700;
    color: #ffffff;
    text-decoration: none;
}

.logo-icon {
    color: #e91e63;
    margin-right: 0.5rem;
    font-size: 1.8rem;
}

.nav-links {
    display: flex;
    gap: 2rem;
}

.nav-link {
    color: rgba(255, 255, 255, 0.8);
    text-decoration: none;
    font-weight: 500;
    transition: all 0.3s ease;
    padding: 0.5rem 1rem;
    border-radius: 8px;
}

.nav-link:hover, .nav-link.active {
    color: #ffffff;
    background: rgba(255, 255, 255, 0.1);
}

/* Main Content */
.main-content {
    padding-top: 100px;
    min-height: 100vh;
}

.hero-section {
    text-align: center;
    padding: 4rem 2rem 2rem 2rem;
    max-width: 1200px;
    margin: 0 auto;
}

.tagline {
    color: #e91e63;
    font-size: 1.1rem;
    font-weight: 500;
    margin-bottom: 2rem;
    font-style: italic;
}

.hero-title {
    font-size: 4rem;
    font-weight: 800;
    margin-bottom: 1.5rem;
    line-height: 1.1;
}

.hero-title-gradient {
    background: linear-gradient(135deg, #ffffff 0%, #e91e63 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.hero-subtitle {
    font-size: 1.4rem;
    color: rgba(255, 255, 255, 0.8);
    font-weight: 400;
    margin-bottom: 2rem;
}

.hero-description {
    font-size: 1.1rem;
    color: rgba(255, 255, 255, 0.7);
    max-width: 800px;
    margin: 0 auto 3rem auto;
    line-height: 1.6;
}

/* Cards */
.upload-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 24px;
    padding: 3rem;
    margin: 2rem auto;
    max-width: 1000px;
    backdrop-filter: blur(10px);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.upload-title {
    text-align: center;
    font-size: 2rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 2rem;
}

/* Score Display */
.score-container {
    background: linear-gradient(135deg, #e91e63 0%, #f06292 100%);
    border-radius: 24px;
    padding: 4rem;
    text-align: center;
    color: white;
    margin: 2rem auto;
    max-width: 600px;
    box-shadow: 0 20px 40px rgba(233, 30, 99, 0.3);
    transform: translateY(-20px);
}

.score-number {
    font-size: 5rem;
    font-weight: 800;
    margin-bottom: 1rem;
    text-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
}

.score-label {
    font-size: 1.5rem;
    opacity: 0.95;
    font-weight: 600;
    margin-bottom: 1rem;
}

.score-description {
    font-size: 1.1rem;
    opacity: 0.9;
    max-width: 400px;
    margin: 0 auto;
    line-height: 1.5;
}

/* Metric Cards */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 2rem;
    margin: 3rem 0;
    max-width: 1000px;
    margin-left: auto;
    margin-right: auto;
}

.metric-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 2rem;
    text-align: center;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}

.metric-card:hover {
    transform: translateY(-10px);
    border-color: rgba(233, 30, 99, 0.3);
    box-shadow: 0 15px 30px rgba(0, 0, 0, 0.2);
}

.metric-value {
    font-size: 2.5rem;
    font-weight: 800;
    color: #e91e63;
    margin-bottom: 0.5rem;
}

.metric-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 0.5rem;
}

.metric-description {
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.7);
    line-height: 1.4;
}

/* Skills Section */
.skills-section {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 2rem;
    margin: 3rem auto;
    max-width: 1000px;
}

.skills-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 1.5rem;
    text-align: center;
}

.skills-count {
    color: #e91e63;
    font-weight: 700;
}

.skills-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    justify-content: center;
    margin-top: 1.5rem;
}

.skill-chip {
    background: linear-gradient(135deg, #e91e63 0%, #f06292 100%);
    color: white;
    padding: 8px 16px;
    border-radius: 50px;
    font-size: 0.9rem;
    font-weight: 600;
    border: none;
    box-shadow: 0 4px 15px rgba(233, 30, 99, 0.3);
    transition: all 0.3s ease;
}

.skill-chip:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(233, 30, 99, 0.4);
}

/* Buttons */
.cta-button {
    background: linear-gradient(135deg, #e91e63 0%, #f06292 100%);
    color: white;
    border: none;
    border-radius: 50px;
    padding: 1.2rem 3rem;
    font-size: 1.2rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.3s ease;
    box-shadow: 0 8px 25px rgba(233, 30, 99, 0.4);
    text-decoration: none;
    display: inline-block;
    margin: 1rem;
}

.cta-button:hover {
    transform: translateY(-3px);
    box-shadow: 0 15px 35px rgba(233, 30, 99, 0.6);
}

/* About Page */
.about-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
}

.about-title {
    font-size: 3rem;
    font-weight: 800;
    text-align: center;
    margin-bottom: 2rem;
    background: linear-gradient(135deg, #ffffff 0%, #e91e63 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.about-text {
    font-size: 1.2rem;
    line-height: 1.8;
    color: rgba(255, 255, 255, 0.8);
    margin-bottom: 2rem;
    text-align: center;
}

.about-links {
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-top: 3rem;
}

.about-link {
    background: rgba(255, 255, 255, 0.1);
    color: white;
    padding: 1rem 2rem;
    border-radius: 12px;
    text-decoration: none;
    font-weight: 600;
    transition: all 0.3s ease;
    border: 1px solid rgba(255, 255, 255, 0.2);
}

.about-link:hover {
    background: rgba(233, 30, 99, 0.2);
    border-color: rgba(233, 30, 99, 0.5);
    transform: translateY(-2px);
}

/* Hide Streamlit elements */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stDeployButton {display: none;}
.stAppViewContainer > .main > div > div > div > div {background: transparent;}

/* File uploader styling */
.stFileUploader > div {
    background: rgba(255, 255, 255, 0.05);
    border: 2px dashed rgba(255, 255, 255, 0.3);
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
}

.stTextArea > div > div > textarea {
    background: rgba(255, 255, 255, 0.05);
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-radius: 16px;
    color: white;
    font-family: 'Inter', sans-serif;
}

.stTextArea > div > div > textarea:focus {
    border-color: #e91e63;
    box-shadow: 0 0 0 3px rgba(233, 30, 99, 0.2);
}
</style>
"""

st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

# -------------------------------------------------------------------
# Navigation
# -------------------------------------------------------------------
def render_navigation():
    st.markdown("""
    <div class="nav-container">
        <div class="logo">
            <span class="logo-icon">✨</span>
            RESUME MATCHER
        </div>
        <div class="nav-links">
            <a href="?page=home" class="nav-link">Home</a>
            <a href="?page=about" class="nav-link">About</a>
            <a href="https://falidill-portfoliowebsite.vercel.app/" target="_blank" class="nav-link">Portfolio</a>
            <a href="https://www.linkedin.com/in/fali-dillys-honutse/" target="_blank" class="nav-link">LinkedIn</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

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
        return "<p style='text-align: center; color: rgba(255,255,255,0.6);'>No skills detected</p>"
    
    chips_html = "<div class='skills-grid'>"
    for skill in skills[:20]:
        chips_html += f"<span class='skill-chip'>✓ {skill}</span>"
    chips_html += "</div>"
    return chips_html

# -------------------------------------------------------------------
# Page Routing
# -------------------------------------------------------------------
query_params = st.query_params
page = query_params.get("page", "home")

# Render navigation
render_navigation()

# -------------------------------------------------------------------
# About Page
# -------------------------------------------------------------------
if page == "about":
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    st.markdown("""
    <div class="about-container">
        <h1 class="about-title">About Resume Matcher</h1>
        
        <p class="about-text">
            Resume Matcher is an AI-powered tool designed to help job seekers optimize their resumes 
            for specific job opportunities. By analyzing the compatibility between your resume and job 
            descriptions, we provide data-driven insights to improve your chances of landing interviews.
        </p>
        
        <p class="about-text">
            Our advanced algorithm evaluates keyword alignment, content similarity, evidence quality, 
            and skills coverage to give you a comprehensive match score. Whether you're a recent graduate 
            or an experienced professional, Resume Matcher helps you tailor your application materials 
            for maximum impact.
        </p>
        
        <p class="about-text">
            Built with cutting-edge natural language processing and machine learning technologies, 
            our platform ensures accurate analysis while maintaining your privacy and data security.
        </p>
        
        <div class="about-links">
            <a href="https://falidill-portfoliowebsite.vercel.app/" target="_blank" class="about-link">
                View Portfolio
            </a>
            <a href="https://www.linkedin.com/in/fali-dillys-honutse/" target="_blank" class="about-link">
                Connect on LinkedIn  
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------------------------
# Home Page
# -------------------------------------------------------------------
else:
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # Initialize session state
    if "analysis_done" not in st.session_state:
        st.session_state.analysis_done = False

    # Hero Section
    if not st.session_state.analysis_done:
        st.markdown("""
        <div class="hero-section">
            <p class="tagline">Unlock Interview Opportunities with Resume Matcher</p>
            <h1 class="hero-title">
                Craft a Resume That<br>
                <span class="hero-title-gradient">Lands Interviews</span>
            </h1>
            <p class="hero-subtitle">
                Know exactly how well your resume fits the roles you want.
            </p>
            <p class="hero-description">
                Empower your job search with Resume Matcher. Upload your resume and the job description, 
                and let Resume Matcher reveal your compatibility score and crucial keywords. 
                Optimize smarter, tailor faster, and take control of your application process.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Upload Section
        st.markdown("""
        <div class="upload-card">
            <h2 class="upload-title">Upload Your Documents</h2>
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
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Try Resume Matcher", type="primary", use_container_width=True):
                if not resume_file or not jd_text.strip():
                    st.error("Please upload both a resume and job description to continue.")
                else:
                    with st.spinner("Analyzing your resume match..."):
                        jd_text_clean = clean_text(jd_text or "")
                        resume_text = extract_resume_text(resume_file)
                        
                        if not resume_text:
                            st.error("Could not extract text from your resume. Please try a different format.")
                            st.stop()

                        result = compute_score(resume_text, jd_text_clean, ONTOLOGY_PATH)
                        
                        st.session_state.analysis_result = result
                        st.session_state.analysis_done = True
                        st.session_state.resume_name = resume_file.name
                        st.rerun()

    # Results Section
    if st.session_state.analysis_done and "analysis_result" in st.session_state:
        result = st.session_state.analysis_result
        
        # Calculate overall score
        subs = result.get("subscores", {}) or {}
        kw = subs.get("keyword_alignment", 0)
        ev = subs.get("evidence", 0) 
        emb = subs.get("embedding_similarity", 0)
        cov = subs.get("skills_coverage", 0)
        
        overall_score = round(0.30*kw + 0.30*ev + 0.25*emb + 0.15*cov, 1)
        score_int = int(round(overall_score))
        
        # Score Display
        st.markdown(f"""
        <div class="score-container">
            <div class="score-number">{score_int}%</div>
            <div class="score-label">Resume Match Score</div>
            <div class="score-description">
                {"Your resume aligns exceptionally well with this job opportunity!" if score_int >= 80 
                 else "Good match! Consider minor improvements for better alignment." if score_int >= 60
                 else "Room for improvement. Focus on adding relevant skills and experience." if score_int >= 40
                 else "Significant improvements needed. Consider major resume updates."}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Detailed Metrics
        st.markdown("""
        <div class="metrics-grid">
        """, unsafe_allow_html=True)
        
        metrics_data = [
            ("Keyword Alignment", kw, "How well your resume keywords match job requirements"),
            ("Evidence Quality", ev, "Strength of examples and achievements in your resume"),
            ("Content Similarity", emb, "Overall semantic similarity with job description"),
            ("Skills Coverage", cov, "Percentage of required skills present in your resume")
        ]
        
        for title, value, description in metrics_data:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{value:.1f}%</div>
                <div class="metric-title">{title}</div>
                <div class="metric-description">{description}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Matched Skills
        aligned_skills = result.get("aligned_skills", [])
        if aligned_skills:
            st.markdown(f"""
            <div class="skills-section">
                <div class="skills-title">
                    Matched Skills & Keywords
                </div>
                <p style="text-align: center; color: rgba(255,255,255,0.8);">
                    <span class="skills-count">{len(aligned_skills)} skills</span> from the job description were found in your resume
                </p>
                {render_skills_chips(aligned_skills)}
            </div>
            """, unsafe_allow_html=True)
        
        # Action Button
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Analyze Another Resume", use_container_width=True):
                st.session_state.analysis_done = False
                st.session_state.analysis_result = {}
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)