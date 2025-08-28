# streamlit_app.py — Modern Resume Matcher (compact header, single page, about blurb, footer)

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
# Dark Modern Theme CSS (compacted header + smaller hero)
# -------------------------------------------------------------------
DARK_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* Global */
.stApp{
  background: linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);
  font-family: 'Inter', sans-serif; color:#fff;
}

/* Compact fixed nav */
.nav-container{
  display:flex; justify-content:space-between; align-items:center;
  padding:.75rem 1.5rem;               /* ↓ smaller */
  background:rgba(26,26,46,.92);
  backdrop-filter: blur(8px);
  border-bottom:1px solid rgba(255,255,255,.08);
  position:fixed; inset:0 0 auto 0; z-index:1000;
}
.logo{display:flex; align-items:center; font-size:1.25rem; font-weight:800; letter-spacing:.5px}
.logo-icon{color:#e91e63; margin-right:.5rem; font-size:1.5rem}
.nav-links{display:flex; gap:1rem}
.nav-link{color:rgba(255,255,255,.85); text-decoration:none; font-weight:600; padding:.4rem .9rem; border-radius:10px}
.nav-link:hover{background:rgba(255,255,255,.12); color:#fff}

/* Main content: pad only as much as nav height */
.main-content{ padding-top:72px; min-height:100vh; } /* ↓ from 100px */

/* Hero (smaller top/bottom padding) */
.hero-section{
  text-align:center; padding:2.25rem 1rem 1.25rem;  /* ↓ from 4rem 2rem 2rem */
  max-width:1200px; margin:0 auto;
}
.tagline{color:#e91e63; font-size:1rem; font-weight:600; margin-bottom:1rem; font-style:italic}
.hero-title{font-size:3rem; font-weight:800; margin:.25rem 0 1rem; line-height:1.12}
.hero-title-gradient{
  background: linear-gradient(135deg,#ffffff 0%,#e91e63 100%);
  -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.hero-subtitle{font-size:1.2rem; color:rgba(255,255,255,.85); margin-bottom:.75rem}
.hero-description{font-size:1rem; color:rgba(255,255,255,.75); max-width:900px; margin:0 auto 1.25rem; line-height:1.55}

/* About blurb card (brief, on landing) */
.about-blurb{
  max-width:1000px; margin:0 auto 1.5rem; padding:1rem 1.25rem;
  background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.10); border-radius:16px;
  color:rgba(255,255,255,.9); line-height:1.55;
}

/* Upload card */
.upload-card{
  background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.1);
  border-radius:24px; padding:2rem; margin:1.25rem auto; max-width:1000px;
  backdrop-filter: blur(8px); box-shadow:0 16px 34px rgba(0,0,0,.28);
}
.upload-title{text-align:center; font-size:1.6rem; font-weight:800; margin-bottom:1.25rem}

/* Score */
.score-container{
  background: linear-gradient(135deg,#22c55e 0%,#16a34a 100%);
  border-radius:24px; padding:2.5rem; text-align:center; color:#fff;
  margin:1.25rem auto 1.5rem; max-width:600px; box-shadow:0 18px 36px rgba(22,163,74,.28);
}
.score-number{font-size:4rem; font-weight:900; margin-bottom:.3rem}
.score-label{font-size:1.2rem; font-weight:700; opacity:.95; margin-bottom:.25rem}
.score-description{font-size:1rem; opacity:.92; max-width:480px; margin:0 auto; line-height:1.5}

/* Metric cards */
.metrics-grid{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
  gap:1.25rem; max-width:1000px; margin:1.5rem auto;
}
.metric-card{
  background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.1);
  border-radius:18px; padding:1.25rem; text-align:center; backdrop-filter:blur(8px);
  transition:transform .25s ease, box-shadow .25s ease, border-color .25s ease;
}
.metric-card:hover{ transform:translateY(-6px); border-color:rgba(233,30,99,.28); box-shadow:0 14px 28px rgba(0,0,0,.22) }
.metric-value{font-size:2rem; font-weight:900; color:#e91e63; margin-bottom:.25rem}
.metric-title{font-size:1rem; font-weight:800}
.metric-description{font-size:.92rem; color:rgba(255,255,255,.75)}

/* Skills */
.skills-section{
  background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.1);
  border-radius:18px; padding:1.25rem; margin:1.5rem auto; max-width:1000px;
}
.skills-title{font-size:1.2rem; font-weight:900; text-align:center; margin-bottom:.75rem}
.skills-count{color:#e91e63; font-weight:800}
.skills-grid{display:flex; flex-wrap:wrap; gap:10px; justify-content:center; margin-top:1rem}
.skill-chip{
  background:linear-gradient(135deg,#e91e63 0%,#f06292 100%); color:#fff; padding:7px 14px;
  border-radius:26px; font-size:.9rem; font-weight:700; border:none; box-shadow:0 4px 14px rgba(233,30,99,.3);
  transition:transform .2s ease;
}
.skill-chip:hover{ transform:translateY(-2px) }

/* Inputs */
.stFileUploader > div{
  background:rgba(255,255,255,.05); border:2px dashed rgba(255,255,255,.3);
  border-radius:16px; padding:1.25rem; text-align:center;
}
.stTextArea > div > div > textarea{
  background:rgba(255,255,255,.05); border:2px solid rgba(255,255,255,.2);
  border-radius:16px; color:#fff; font-family:'Inter',sans-serif;
}
.stTextArea > div > div > textarea:focus{ border-color:#e91e63; box-shadow:0 0 0 3px rgba(233,30,99,.2) }

/* Hide Streamlit default chrome we don't need */
#MainMenu{visibility:hidden} footer{visibility:hidden} header{visibility:hidden} .stDeployButton{display:none}
.stAppViewContainer > .main > div > div > div > div {background: transparent;}
</style>
"""
st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)

# -------------------------------------------------------------------
# Compact Top Bar (no Home/About pages)
# -------------------------------------------------------------------
def render_navigation():
    st.markdown("""
    <div class="nav-container">
        <div class="logo"><span class="logo-icon">✨</span>RESUME MATCHER</div>
        <div class="nav-links">
            <a href="https://falidill-portfoliowebsite.vercel.app/" target="_blank" class="nav-link">Portfolio</a>
            <a href="https://www.linkedin.com/in/fali-dillys-honutse/" target="_blank" class="nav-link">LinkedIn</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

render_navigation()

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def extract_resume_text(uploaded_file) -> str:
    if not uploaded_file: return ""
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
        return "<p style='text-align:center;color:rgba(255,255,255,.65);'>No skills detected</p>"
    chips = "<div class='skills-grid'>"
    for s in skills[:20]:
        chips += f"<span class='skill-chip'>✓ {s}</span>"
    chips += "</div>"
    return chips

# -------------------------------------------------------------------
# Single-page App
# -------------------------------------------------------------------
st.markdown('<div class="main-content">', unsafe_allow_html=True)

# Session state
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

# Hero
if not st.session_state.analysis_done:
    st.markdown("""
    <div class="hero-section">
        <p class="tagline">Unlock Interview Opportunities with Resume Matcher</p>
        <h1 class="hero-title">
            Craft a Resume That<br>
            <span class="hero-title-gradient">Lands Interviews</span>
        </h1>
        <p class="hero-subtitle">Know exactly how well your resume fits the roles you want.</p>
        <p class="hero-description">
            Upload your resume and the job description. Resume Matcher analyzes keyword alignment,
            evidence quality, content similarity, and skills coverage—giving you a clear score
            and the exact keywords to strengthen.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # About blurb (on landing, short)
    st.markdown("""
    <div class="about-blurb">
        <strong>What is this?</strong> Resume Matcher is a free, open-source tool built to help job seekers tailor
        their resumes quickly and confidently. Your documents are processed in memory, and we don’t store them.
    </div>
    """, unsafe_allow_html=True)

    # Upload section
    st.markdown('<div class="upload-card"><div class="upload-title">Upload Your Documents</div></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("### 📄 Resume")
        resume_file = st.file_uploader("Upload your resume", type=["pdf","docx","txt"], label_visibility="collapsed",
                                       help="Supported formats: PDF, DOCX, TXT")
    with c2:
        st.markdown("### 📋 Job Description")
        jd_text = st.text_area("Paste the job description here", height=200, label_visibility="collapsed",
                               placeholder="Paste the complete job description here...")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    _, cbtn, _ = st.columns([1,2,1])
    with cbtn:
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

# Results
if st.session_state.analysis_done and "analysis_result" in st.session_state:
    result = st.session_state.analysis_result
    subs = result.get("subscores", {}) or {}
    kw  = subs.get("keyword_alignment", 0)
    ev  = subs.get("evidence", 0)
    emb = subs.get("embedding_similarity", 0)
    cov = subs.get("skills_coverage", 0)

    overall = round(0.30*kw + 0.30*ev + 0.25*emb + 0.15*cov, 1)
    score_i = int(round(overall))

    st.markdown(f"""
    <div class="score-container" style="background: linear-gradient(135deg, {'#22c55e' if score_i>=70 else '#f59e0b' if score_i>=40 else '#ef4444'} 0%, {'#16a34a' if score_i>=70 else '#d97706' if score_i>=40 else '#b91c1c'} 100%);">
        <div class="score-number">{score_i}%</div>
        <div class="score-label">Resume Match Score</div>
        <div class="score-description">
            {"Your resume aligns exceptionally well with this job opportunity!" if score_i >= 80
            else "Good match! Consider minor improvements for better alignment." if score_i >= 60
            else "Room for improvement. Focus on adding relevant skills and experience." if score_i >= 40
            else "Significant improvements needed. Consider major updates before applying."}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="metrics-grid">', unsafe_allow_html=True)
    for title, value, desc in [
        ("Keyword Alignment", kw,  "How well your resume keywords match job requirements"),
        ("Evidence Quality",  ev,  "Strength of examples and achievements in your resume"),
        ("Content Similarity", emb, "Overall semantic similarity with job description"),
        ("Skills Coverage",   cov, "Percentage of required skills present in your resume"),
    ]:
      st.markdown(f"""
      <div class="metric-card">
        <div class="metric-value">{value:.1f}%</div>
        <div class="metric-title">{title}</div>
        <div class="metric-description">{desc}</div>
      </div>
      """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    aligned = result.get("aligned_skills", [])
    if aligned:
        st.markdown(f"""
        <div class="skills-section">
            <div class="skills-title">Matched Skills & Keywords</div>
            <p style="text-align:center;color:rgba(255,255,255,.85);">
                <span class="skills-count">{len(aligned)} skills</span> from the job description were found in your resume
            </p>
            {render_skills_chips(aligned)}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    _, cbtn2, _ = st.columns([1,2,1])
    with cbtn2:
        if st.button("Analyze Another Resume", use_container_width=True):
            st.session_state.analysis_done = False
            st.session_state.analysis_result = {}
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)  # end main-content

# -------------------------------------------------------------------
# Footer (with separators •)
# -------------------------------------------------------------------
st.markdown("""
<hr style="border:none;border-top:1px solid rgba(255,255,255,.18); margin: 1.0rem 0 0.5rem;">
<div style="text-align:center; color:#cbd5e1; font-size:.98rem; padding:.5rem 0 1.25rem;">
  Built with ❤️ to help job seekers<br/>
  Created by <a href="https://www.linkedin.com/in/fali-dillys-honutse/" target="_blank" style="color:#22D3EE; text-decoration:none;">Fali Honutse</a>
  <span style="opacity:.7;"> • </span>
  <a href="https://falidill-portfoliowebsite.vercel.app/" target="_blank" style="color:#22D3EE; text-decoration:none;">Portfolio</a>
  <br/>
  <span style="color:#94a3b8;">Forked and modified from
    <a href="https://github.com/srbhr/Resume-Matcher" target="_blank" style="color:#94a3b8; text-decoration:none;">srbhr/Resume-Matcher</a>
    (Apache 2.0 License)</span>
</div>
""", unsafe_allow_html=True)
