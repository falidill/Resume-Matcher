# streamlit_app.py — improved UX + accuracy fixes (JD cleaning, ontology guard, coverage fallback)

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
st.set_page_config(page_title="Resume ⇄ JD Match Tool", page_icon="🧠", layout="wide")

# -------------------------------------------------------------------
# Styles (chips + score bar)
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
# Hero
# -------------------------------------------------------------------
st.markdown(
    """
<div style="padding:1.6rem; background:linear-gradient(90deg,#2c3e50,#8e44ad); border-radius:16px; text-align:center; margin-bottom:1rem">
  <h1 style="color:#fff; margin:0 0 .3rem 0">🧠 Resume Matcher</h1>
  <p style="color:#e6e6e6; margin:0">No more guessing — see how well your resume matches the job description.</p>
</div>
""",
    unsafe_allow_html=True
)

# -------------------------------------------------------------------
# Sidebar
# -------------------------------------------------------------------
with st.sidebar:
    st.header("Options")
    privacy = st.checkbox("Delete processed text after scoring (privacy-first)", value=True)
    show_ats = st.checkbox("Run ATS-lite checks", value=True)
    show_history = st.checkbox("Keep session history (last 5)", value=True)
    st.caption("We do not store your documents by default. Keep the Apache-2.0 license & attribution from the base repo.")

# Warn early if ontology is missing (prevents confusing 0 coverage)
if not ONTOLOGY_PATH.exists():
    st.warning("Skills ontology not found at: " + str(ONTOLOGY_PATH) + " — coverage metrics may be inaccurate.")

# -------------------------------------------------------------------
# Inputs
# -------------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    resume_file = st.file_uploader("📄 Upload Resume (PDF / DOCX / TXT)", type=["pdf", "docx", "txt"], help="Prefer a one-column ATS-friendly layout.")
with col2:
    jd_text = st.text_area("📋 Paste Job Description", height=280, placeholder="Paste the full job description here…")

# -------------------------------------------------------------------
# Helpers
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
    if not missing_terms:
        return "No suggestions — strong match."
    
    out = []
    templates = [
        "Implemented {term} to improve reporting speed by X%.",
        "Built {term} workflows for stakeholders, reducing manual effort by X%.",
        "Analyzed {term} data to inform decisions, resulting in measurable impact.",
        "Automated {term}-related tasks using Python, cutting cycle time by X%."
    ]
    
    # Take only the first 12 missing terms to avoid overwhelming output
    limited_terms = missing_terms[:12]
    
    for i, term in enumerate(limited_terms):
        # Handle both string and dict formats
        if isinstance(term, dict):
            term_text = term.get("term", term.get("skill", str(term)))
        else:
            term_text = str(term)
        
        suggestion = templates[i % len(templates)].format(term=term_text)
        out.append(f"• {suggestion}")
    
    return "\n".join(out)

# Enhanced ontology helpers
def load_ontology_terms(path: Path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        terms = []
        
        if isinstance(data, dict):
            if "skills" in data:
                skills = data["skills"]
                if isinstance(skills, list):
                    terms = [str(s).lower().strip() for s in skills if s]
                elif isinstance(skills, dict):
                    # Handle nested skill categories
                    for category, skill_list in skills.items():
                        if isinstance(skill_list, list):
                            terms.extend([str(s).lower().strip() for s in skill_list if s])
            else:
                # Try to extract from any list values in the dict
                for value in data.values():
                    if isinstance(value, list):
                        terms.extend([str(s).lower().strip() for s in value if s])
        elif isinstance(data, list):
            terms = [str(s).lower().strip() for s in data if s]
        
        # Remove empty strings and duplicates
        return list(set([t for t in terms if t]))
        
    except Exception as e:
        st.error(f"Error loading ontology: {e}")
        return []

def extract_skills_simple(text: str, terms):
    if not text or not terms:
        return set()
        
    t = text.lower()
    # Normalize common variants
    normalizations = {
        "scikit learn": "scikit-learn",
        "sci-kit learn": "scikit-learn", 
        "sklearn": "scikit-learn",
        "tensorflow": "tensorflow",
        "tensor flow": "tensorflow",
        "pytorch": "pytorch",
        "torch": "pytorch",  # Be careful with this one
        "powerbi": "power bi",
        "power-bi": "power bi",
        "nodejs": "node.js",
        "node js": "node.js",
        "reactjs": "react",
        "react js": "react"
    }
    
    for old, new in normalizations.items():
        t = t.replace(old, new)
    
    found = set()
    for term in terms:
        # Use word boundaries for better matching
        pattern = rf"\b{re.escape(term)}\b"
        if re.search(pattern, t, re.IGNORECASE):
            found.add(term)
    
    return found

def find_missing_skills(jd_text, resume_text, ontology_terms):
    """Find skills that are in JD but not in resume"""
    if not jd_text or not resume_text or not ontology_terms:
        return []
    
    jd_skills = extract_skills_simple(jd_text, ontology_terms)
    resume_skills = extract_skills_simple(resume_text, ontology_terms)
    missing = jd_skills - resume_skills
    
    return list(missing)

# Real copy-to-clipboard button
def copy_to_clipboard_button(text: str, label="📋 Copy suggestions to clipboard"):
    from streamlit.components.v1 import html
    safe = (text or "").replace("\\", "\\\\").replace("`", "\\`").replace("</", "<\\/")
    html(f"""
        <button onclick="navigator.clipboard.writeText(`{safe}`)"
                style="background:#111827;border:1px solid #2b2f36;color:#e5e7eb;border-radius:12px;padding:10px 14px;cursor:pointer;margin:6px 0;">
            {label}
        </button>
        """, height=46)

# Session history
if "history" not in st.session_state:
    st.session_state.history = []

# -------------------------------------------------------------------
# Action
# -------------------------------------------------------------------
run = st.button("⚡ Check Match", type="primary", use_container_width=True)
if run:
    if not resume_file or not jd_text.strip():
        st.error("Please upload a resume and paste a job description.")
        st.stop()

    # Clean JD (this was missing and can tank coverage)
    jd_text_clean = clean_text(jd_text or "")

    # Status block instead of fake progress loop
    with st.status("Analyzing your resume against the job description…", expanded=False) as status:
        resume_text = extract_resume_text(resume_file)
        if not resume_text:
            status.update(label="Parsing failed", state="error")
            st.stop()

        # Core scoring
        result = compute_score(resume_text, jd_text_clean, ONTOLOGY_PATH)
        status.update(label="Done! Scroll to see your results.", state="complete")

    # ---------------- Results ----------------
    st.markdown("### 📊 Match Results")

    # Load ontology terms for improved missing skill detection
    ontology_terms = load_ontology_terms(ONTOLOGY_PATH) if ONTOLOGY_PATH.exists() else []

    # Subscores & potential fallback coverage
    subs = result.get("subscores", {}) or {}
    skills_cov = subs.get("skills_coverage", 0)
    aligned = [s for s in result.get("aligned_skills", []) if s]
    
    # Get missing skills from result, but also compute our own
    raw_missing = result.get("missing_skills", [])
    
    # Compute missing skills using ontology
    computed_missing = []
    if ontology_terms:
        computed_missing = find_missing_skills(jd_text_clean, resume_text, ontology_terms)
    
    # Use computed missing if the original is empty or seems wrong
    if not raw_missing and computed_missing:
        raw_missing = computed_missing
    elif len(computed_missing) > len(raw_missing):
        # If we found more missing skills, use the computed ones
        raw_missing = computed_missing

    # If coverage is 0 but we clearly matched terms, compute a display-side fallback
    fallback_used = False
    if skills_cov == 0 and (aligned or ontology_terms):
        if ontology_terms:
            jd_terms = extract_skills_simple(jd_text_clean, ontology_terms)
            res_terms = extract_skills_simple(resume_text, ontology_terms)
            inter = jd_terms & res_terms
            denom = len(jd_terms) or 1
            fallback_cov = round(100 * len(inter) / denom, 1)
            subs["skills_coverage"] = fallback_cov
            result["subscores"] = subs
            skills_cov = fallback_cov
            fallback_used = True

    # Optional: recompute a displayed total so the bar matches the patched subscores
    kw   = subs.get("keyword_alignment", 0)
    ev   = subs.get("evidence", 0)
    emb  = subs.get("embedding_similarity", 0)
    cov  = subs.get("skills_coverage", 0)

    # These weights are just display-side; your backend still controls real scoring logic
    display_total = round(0.30*kw + 0.30*ev + 0.25*emb + 0.15*cov, 1)
    score = int(round(display_total))

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

    # Show subscores
    if isinstance(subs, dict) and subs:
        df = pd.DataFrame([{"Area": k, "Score": v} for k, v in subs.items()]).sort_values("Score", ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
        if fallback_used:
            st.caption("ℹ️ Skills coverage was adjusted using a lightweight fallback because the original coverage appeared as 0 despite matches.")
    else:
        st.caption("No subscore breakdown available.")

    # Extract missing terms properly
    missing_terms = []
    for m in raw_missing:
        if isinstance(m, dict):
            # Try different possible keys
            term = m.get("term") or m.get("skill") or m.get("name") or str(m)
        else:
            term = str(m)
        if term and term != "{}":  # Avoid empty or string representations of empty dict
            missing_terms.append(term)

    # Matched vs Missing
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### ✅ Matched skills/keywords")
        render_chips(aligned, ok=True)
    with c2:
        st.markdown("#### ⚠ Missing or weakly covered")
        render_chips(missing_terms, ok=False)

    # Debug info (remove in production)
    if st.sidebar.checkbox("Show debug info", value=False):
        st.markdown("#### 🐛 Debug Info")
        st.write(f"Ontology terms loaded: {len(ontology_terms)}")
        st.write(f"Raw missing from result: {raw_missing[:5]}...")  # Show first 5
        st.write(f"Processed missing terms: {missing_terms[:10]}")  # Show first 10
        if ontology_terms:
            jd_skills = extract_skills_simple(jd_text_clean, ontology_terms)
            resume_skills = extract_skills_simple(resume_text, ontology_terms)
            st.write(f"JD skills found: {len(jd_skills)}")
            st.write(f"Resume skills found: {len(resume_skills)}")

    # Suggestions
    st.markdown("#### ✍️ Quick bullet ideas (use only if accurate)")
    suggestions_text = quick_suggestions(missing_terms)
    st.text_area("Copy suggestions", value=suggestions_text, height=170)
    copy_to_clipboard_button(suggestions_text)

    # ATS-lite
    if show_ats:
        st.markdown("#### 🧪 ATS-lite checks")
        hints = ats_lite_findings(resume_text)
        if hints:
            for h in hints:
                st.write("•", h)
        else:
            st.write("Looks ATS-friendly at a glance.")

    # Download
    if suggestions_text and suggestions_text.strip() and suggestions_text != "No suggestions — strong match.":
        st.download_button(
            "⬇️ Download suggestions.txt",
            data=suggestions_text.encode("utf-8"),
            file_name="resume_match_suggestions.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # History
    if show_history:
        st.session_state.history.insert(0, {
            "Time": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Score": score,
            "Matched": len(aligned),
            "Missing": len(missing_terms),
            "Resume": resume_file.name,
        })
        st.session_state.history = st.session_state.history[:5]
        with st.expander("🕘 Recent matches (this session)"):
            st.table(pd.DataFrame(st.session_state.history))

    # Privacy: clear in-memory text
    if privacy:
        resume_text = ""
        suggestions_text = ""

# -------------------------------------------------------------------
# Footer
# -------------------------------------------------------------------
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