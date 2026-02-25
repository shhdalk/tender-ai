import os
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

import streamlit as st
from dotenv import load_dotenv

from tenderai.config import load_settings
from tenderai.utils import safe_filename
from tenderai.agents.parse_agent import ParseAgent
from tenderai.agents.requirements_agent import RequirementsAgent
from tenderai.agents.evaluate_agent import EvaluateAgent
from tenderai.schemas import ProposalEvaluation, RequirementsDoc

load_dotenv()


def _process_one_proposal(
    uploaded_file,
    requirements_doc: RequirementsDoc,
    parse_agent: ParseAgent,
    eval_agent: EvaluateAgent,
    save_upload_fn,
) -> ProposalEvaluation:
    path = save_upload_fn(uploaded_file)
    proposal_text = parse_agent.parse_file(path)
    vendor_name = os.path.splitext(safe_filename(uploaded_file.name))[0]
    return eval_agent.evaluate_proposal(
        vendor_name=vendor_name,
        requirements_doc=requirements_doc,
        proposal_text=proposal_text,
    )


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TenderAI — RFP Intelligence",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400;1,600&family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --ink:        #22263A;
  --ink-60:     #6E748A;
  --ink-30:     #B4B9CC;
  --surface:    #F0F2F8;
  --card:       #FFFFFF;
  --border:     #E2E6F0;
  --accent:     #5B6CF5;
  --accent-lt:  #EAECFE;
  --green:      #27A06E;
  --green-lt:   #D4F3E7;
  --red:        #DC5B68;
  --red-lt:     #FCEAEC;
  --amber:      #C8841E;
  --amber-lt:   #FCF0D8;
  --sidebar-w:  240px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
  background: var(--surface) !important;
  font-family: 'Outfit', sans-serif !important;
  color: var(--ink) !important;
}
section[data-testid="stMain"] > div { background: transparent !important; }

/* ── Sidebar (light) ── */
[data-testid="stSidebar"] {
  background: #FFFFFF !important;
  border-right: 1px solid var(--border) !important;
  width: var(--sidebar-w) !important;
}
[data-testid="stSidebar"] * { color: var(--ink) !important; }
[data-testid="stSidebarContent"] { padding: 0 !important; }

.sidebar-logo {
  padding: 1.75rem 1.5rem 1.25rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.5rem;
}
.sidebar-logo .wordmark {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--ink) !important;
  letter-spacing: -0.02em;
  line-height: 1;
}
.sidebar-logo .wordmark em { font-style: italic; color: var(--accent) !important; }
.sidebar-logo .tagline {
  font-size: 0.64rem;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-30) !important;
  margin-top: 4px;
}

/* ── Nav radio ── */
[data-testid="stRadio"] > div { gap: 2px !important; padding: 0 0.75rem !important; }
[data-testid="stRadio"] label {
  padding: 0.55rem 0.85rem !important;
  border-radius: 8px !important;
  font-size: 0.84rem !important;
  font-weight: 500 !important;
  cursor: pointer !important;
  color: var(--ink-60) !important;
  transition: all 0.12s !important;
  width: 100% !important;
}
[data-testid="stRadio"] label:hover {
  background: var(--surface) !important;
  color: var(--ink) !important;
}
[data-testid="stRadio"] [aria-checked="true"] {
  background: var(--accent-lt) !important;
  color: var(--accent) !important;
  font-weight: 600 !important;
}
[data-testid="stRadio"] [data-testid="stMarkdownContainer"] { display: none !important; }

/* ── Main content ── */
.block-container {
  padding: 2rem 2.5rem 4rem !important;
  max-width: 1400px !important;
}

/* ── Page header ── */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 2rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid var(--border);
}
.page-title {
  font-family: 'Playfair Display', serif;
  font-size: 1.9rem;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: -0.03em;
  line-height: 1.1;
}
.page-title em { font-style: italic; color: var(--accent); }
.page-subtitle {
  font-size: 0.84rem;
  color: var(--ink-60);
  margin-top: 4px;
}

/* ── Cards ── */
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 1.25rem 1.5rem;
}
.card-header {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-30);
  margin-bottom: 0.6rem;
}
.card-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 0.25rem;
}
.card-desc {
  font-size: 0.82rem;
  color: var(--ink-60);
  line-height: 1.55;
}

/* ── Step cards ── */
.step-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 0;
  overflow: hidden;
  margin-bottom: 1rem;
}
.step-card-accent { height: 3px; background: var(--accent); opacity: 0.6; }
.step-card-body { padding: 1.1rem 1.4rem 1.4rem; }
.step-number {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.63rem;
  font-weight: 500;
  letter-spacing: 0.08em;
  color: var(--accent);
  margin-bottom: 5px;
}

/* ── KPI strip ── */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 1.5rem;
}
.kpi-cell { background: var(--card); padding: 1.25rem 1.5rem; }
.kpi-value {
  font-family: 'Playfair Display', serif;
  font-size: 1.9rem;
  font-weight: 700;
  color: var(--ink);
  line-height: 1;
  letter-spacing: -0.03em;
}
.kpi-value.green { color: var(--green); }
.kpi-value.gold  { color: var(--accent); }
.kpi-label {
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-30);
  margin-top: 5px;
}

/* ── Table ── */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
  margin-bottom: 1.5rem;
}
.data-table thead tr { background: var(--surface); }
.data-table thead th {
  padding: 11px 16px;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  text-align: left;
  color: var(--ink-60);
  white-space: nowrap;
  border-bottom: 1px solid var(--border);
}
.data-table tbody tr { border-bottom: 1px solid var(--border); }
.data-table tbody tr:last-child { border-bottom: none; }
.data-table tbody tr:hover { background: #F6F7FB; }
.data-table tbody td {
  padding: 13px 16px;
  color: var(--ink);
  vertical-align: middle;
}
.td-vendor { font-weight: 600; }

/* ── Score bar ── */
.score-bar-wrap { display: flex; align-items: center; gap: 10px; }
.score-bar-track {
  flex: 1; height: 5px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
  min-width: 80px;
}
.score-bar-fill {
  height: 100%; border-radius: 3px;
  background: var(--accent);
}
.score-bar-fill.high { background: var(--green); }
.score-bar-fill.low  { background: var(--red); }
.score-num {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.78rem;
  font-weight: 500;
  min-width: 34px;
  color: var(--ink-60);
}

/* ── Badges ── */
.badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: 20px;
  font-size: 0.71rem;
  font-weight: 600;
  white-space: nowrap;
}
.badge-green { background: var(--green-lt);  color: var(--green); }
.badge-amber { background: var(--amber-lt);  color: var(--amber); }
.badge-red   { background: var(--red-lt);    color: var(--red); }
.badge-ink   { background: var(--surface);   color: var(--ink-60); border: 1px solid var(--border); }

/* ── Vendor summary ── */
.vendor-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 1rem;
}
.vendor-name-lg {
  font-family: 'Playfair Display', serif;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--ink);
}
.vendor-summary {
  font-size: 0.85rem;
  color: var(--ink-60);
  line-height: 1.7;
  padding: 0.75rem 1rem;
  background: var(--surface);
  border-radius: 10px;
  border-left: 3px solid var(--accent);
  margin-bottom: 1.25rem;
}

/* ── Requirement rows ── */
.req-item {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  gap: 12px;
  align-items: start;
  padding: 13px 0;
  border-bottom: 1px solid var(--border);
}
.req-item:last-child { border-bottom: none; }
.req-id-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.63rem;
  color: var(--accent);
  letter-spacing: 0.05em;
  margin-bottom: 3px;
}
.req-justification {
  font-size: 0.83rem;
  color: var(--ink);
  line-height: 1.55;
}
.req-evidence {
  margin-top: 7px;
  padding: 7px 11px;
  background: var(--surface);
  border-left: 2px solid var(--accent);
  border-radius: 0 6px 6px 0;
  font-size: 0.77rem;
  color: var(--ink-60);
  font-style: italic;
  line-height: 1.5;
}
.req-evidence-loc {
  font-style: normal;
  font-weight: 600;
  font-size: 0.65rem;
  color: var(--accent);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 2px;
}
.req-confidence {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: var(--ink-30);
  padding-top: 2px;
}

/* ── Expanders ── */
details[data-testid="stExpander"] {
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  background: var(--card) !important;
  margin-bottom: 0.5rem !important;
  overflow: hidden !important;
}
details[data-testid="stExpander"] summary {
  font-family: 'Outfit', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.85rem !important;
  color: var(--ink) !important;
  padding: 13px 16px !important;
  background: var(--card) !important;
}
details[data-testid="stExpander"] > div { padding: 0 16px 16px !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  border: 1.5px dashed var(--border) !important;
  border-radius: 12px !important;
  background: var(--card) !important;
}
[data-testid="stFileUploader"]:hover {
  border-color: var(--accent) !important;
  background: var(--accent-lt) !important;
}

/* ── Buttons ── */
.stButton > button {
  border-radius: 9px !important;
  font-family: 'Outfit', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.85rem !important;
  border: none !important;
  background: var(--accent) !important;
  color: #FFFFFF !important;
  padding: 0.6rem 1.25rem !important;
  transition: opacity 0.15s !important;
}
.stButton > button:hover { opacity: 0.88 !important; }
.stButton > button:disabled {
  background: var(--border) !important;
  color: var(--ink-30) !important;
}

/* ── Misc ── */
[data-testid="stAlert"] { border-radius: 10px !important; }
hr {
  border: none !important;
  border-top: 1px solid var(--border) !important;
  margin: 1.5rem 0 !important;
}
.info-box {
  background: var(--accent-lt);
  border: 1px solid #C4CAFD;
  border-radius: 10px;
  padding: 11px 14px;
  font-size: 0.82rem;
  color: var(--accent);
  line-height: 1.5;
}
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: var(--ink-60);
}
.empty-icon { font-size: 2.5rem; margin-bottom: 1rem; opacity: 0.4; }
.empty-title {
  font-family: 'Playfair Display', serif;
  font-size: 1.1rem;
  color: var(--ink);
  margin-bottom: 0.5rem;
}
.empty-desc { font-size: 0.82rem; line-height: 1.6; }
.chip {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.71rem;
  font-weight: 600;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--ink-60);
}
.section-label {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--ink-30);
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-label::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}
.page-badge {
  background: var(--accent-lt);
  color: var(--accent);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 3px 10px;
  border-radius: 20px;
  display: inline-block;
}
</style>
""", unsafe_allow_html=True)


# ── Agents ─────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_agents():
    settings = load_settings()
    parse_agent = ParseAgent(settings.llama_cloud_api_key)
    req_agent = RequirementsAgent(settings.openai_api_key, settings.openai_model)
    eval_agent = EvaluateAgent(settings.openai_api_key, settings.openai_model)
    return settings, parse_agent, req_agent, eval_agent


try:
    settings, parse_agent, req_agent, eval_agent = get_agents()
    agents_ok = True
except Exception as e:
    agents_ok = False
    agent_error = str(e)


def _save_upload(uploaded_file) -> str:
    suffix = os.path.splitext(uploaded_file.name)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        return tmp.name


# ── Sidebar navigation ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div class="sidebar-logo">
  <div class="wordmark">Tender<em>AI</em></div>
  <div class="tagline">RFP Intelligence Platform</div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="nav-section-label">Navigation</div>', unsafe_allow_html=True)

    page = st.radio(
        "nav",
        ["⬡  Dashboard", "📄  Import RFP", "🏢  Evaluate Proposals", "📊  Results & Analysis"],
        label_visibility="collapsed",
    )

    # Status indicators
    has_rfp = "requirements_doc" in st.session_state
    has_results = "evaluations" in st.session_state and len(st.session_state["evaluations"]) > 0

    st.markdown(f"""
<div style="padding: 1rem 1.5rem; margin-top: 1rem;">
  <div style="font-size:0.62rem; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; 
       color:var(--ink-30); margin-bottom:0.75rem;">Workflow Status</div>
  <div style="display:flex; flex-direction:column; gap:8px;">
    <div style="display:flex; align-items:center; gap:8px; font-size:0.78rem; 
         color:{'#27A06E' if agents_ok else '#DC5B68'};">
      <span>{'✓' if agents_ok else '✗'}</span>
      <span>{'AI agents connected' if agents_ok else 'Connection error'}</span>
    </div>
    <div style="display:flex; align-items:center; gap:8px; font-size:0.78rem; 
         color:{'#27A06E' if has_rfp else 'var(--ink-30)'};">
      <span>{'✓' if has_rfp else '○'}</span>
      <span>{'RFP loaded' if has_rfp else 'No RFP loaded'}</span>
    </div>
    <div style="display:flex; align-items:center; gap:8px; font-size:0.78rem; 
         color:{'#27A06E' if has_results else 'var(--ink-30)'};">
      <span>{'✓' if has_results else '○'}</span>
      <span>{'Proposals evaluated' if has_results else 'No evaluations yet'}</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Helper renderers ───────────────────────────────────────────────────────────
def _badge(pct):
    if pct >= 75:
        return f'<span class="badge badge-green">● {pct:.1f}%</span>'
    elif pct >= 50:
        return f'<span class="badge badge-amber">● {pct:.1f}%</span>'
    else:
        return f'<span class="badge badge-red">● {pct:.1f}%</span>'


def _rec_badge(rec):
    rec = rec or "—"
    for k, cls in [("Recommend", "badge-green"), ("Consider", "badge-amber"), ("Reject", "badge-red")]:
        if k.lower() in rec.lower():
            return f'<span class="badge {cls}">{rec}</span>'
    return f'<span class="badge badge-ink">{rec}</span>'


def _score_bar(pct):
    cls = "high" if pct >= 75 else ("low" if pct < 50 else "")
    return f"""
<div class="score-bar-wrap">
  <div class="score-bar-track">
    <div class="score-bar-fill {cls}" style="width:{min(pct,100):.1f}%"></div>
  </div>
  <span class="score-num">{pct:.0f}%</span>
</div>"""


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "⬡  Dashboard":
    st.markdown("""
<div class="page-header">
  <div>
    <div class="page-title">Overview <em>Dashboard</em></div>
    <div class="page-subtitle">Monitor your RFP evaluation pipeline at a glance.</div>
  </div>
  <div class="page-badge">Live</div>
</div>
""", unsafe_allow_html=True)

    if not agents_ok:
        st.error(f"⚠ Agent initialisation failed: {agent_error}")

    # KPI strip
    rfp_loaded = "requirements_doc" in st.session_state
    total_reqs = len(st.session_state["requirements_doc"].requirements) if rfp_loaded else 0
    evs = st.session_state.get("evaluations", [])
    top_score = f"{max(e.match_percentage for e in evs):.0f}%" if evs else "—"
    winners = [e for e in evs if (getattr(e, "recommendation", "") or "").lower().startswith("recommend")]

    st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-cell">
    <div class="kpi-value {'gold' if rfp_loaded else ''}">{total_reqs if rfp_loaded else '—'}</div>
    <div class="kpi-label">Requirements extracted</div>
  </div>
  <div class="kpi-cell">
    <div class="kpi-value">{len(evs)}</div>
    <div class="kpi-label">Proposals evaluated</div>
  </div>
  <div class="kpi-cell">
    <div class="kpi-value {'green' if top_score != '—' else ''}">{top_score}</div>
    <div class="kpi-label">Top match score</div>
  </div>
  <div class="kpi-cell">
    <div class="kpi-value">{len(winners)}</div>
    <div class="kpi-label">Shortlisted vendors</div>
  </div>
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns([1.2, 1], gap="large")

    with col1:
        st.markdown('<div class="section-label">Workflow steps</div>', unsafe_allow_html=True)

        steps = [
            ("01", "Import RFP", "Upload a PDF or DOCX tender document. LlamaParse extracts the full text, then an LLM identifies and structures every requirement.", rfp_loaded),
            ("02", "Evaluate Proposals", "Upload vendor proposals for parallel AI scoring. Each requirement is checked for evidence, with confidence scores and citations.", bool(evs)),
            ("03", "Review Analysis", "Ranked leaderboard, per-requirement breakdowns, evidence citations, and final shortlist recommendations.", bool(evs)),
        ]

        for num, title, desc, done in steps:
            status_bar = '<div class="step-card-accent"></div>' if done else '<div style="height:3px;background:#E4E7EE;"></div>'
            done_badge = '<span class="badge badge-green" style="float:right;margin-top:-2px;">Complete</span>' if done else '<span class="badge badge-ink" style="float:right;margin-top:-2px;">Pending</span>'
            st.markdown(f"""
<div class="step-card">
  {status_bar}
  <div class="step-card-body">
    <div class="step-number">STEP {num} {done_badge}</div>
    <div class="card-title" style="margin-bottom:6px;">{title}</div>
    <div class="card-desc">{desc}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-label">Quick actions</div>', unsafe_allow_html=True)

        st.markdown('<div class="card" style="margin-bottom:1rem;">', unsafe_allow_html=True)
        st.markdown("""
<div class="card-header">Getting started</div>
<div class="card-desc" style="line-height:1.7;">
  Begin by uploading your RFP document on the <b>Import RFP</b> page. 
  Once requirements are extracted, move to <b>Evaluate Proposals</b> to score 
  vendor submissions in parallel. Results appear in the <b>Results & Analysis</b> tab.
</div>
""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if evs:
            st.markdown('<div class="section-label" style="margin-top:1rem;">Top vendors</div>', unsafe_allow_html=True)
            sorted_evs = sorted(evs, key=lambda e: e.match_percentage, reverse=True)[:3]
            medals = ["🥇", "🥈", "🥉"]
            for i, ev in enumerate(sorted_evs):
                met = sum(1 for s in ev.scores if s.met)
                st.markdown(f"""
<div style="display:flex; align-items:center; justify-content:space-between; 
     padding:12px 0; border-bottom:1px solid var(--border);">
  <div style="display:flex; align-items:center; gap:10px;">
    <span style="font-size:1.1rem;">{medals[i]}</span>
    <div>
      <div style="font-weight:600; font-size:0.86rem; color:var(--ink);">{ev.vendor_name}</div>
      <div style="font-size:0.74rem; color:var(--ink-60);">{met}/{len(ev.scores)} requirements met</div>
    </div>
  </div>
  {_badge(ev.match_percentage)}
</div>
""", unsafe_allow_html=True)
        else:
            st.markdown("""
<div class="info-box">
  ℹ No evaluations yet. Complete the import and evaluation steps to see vendor rankings here.
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: IMPORT RFP
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📄  Import RFP":
    st.markdown("""
<div class="page-header">
  <div>
    <div class="page-title">Import <em>RFP</em></div>
    <div class="page-subtitle">Upload your Request for Proposal and extract structured requirements.</div>
  </div>
</div>
""", unsafe_allow_html=True)

    if not agents_ok:
        st.error(f"⚠ {agent_error}")
        st.stop()

    col_upload, col_info = st.columns([1.4, 1], gap="large")

    with col_upload:
        st.markdown('<div class="section-label">Document upload</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="step-card" style="margin-bottom:1rem;">
  <div class="step-card-accent"></div>
  <div class="step-card-body">
    <div class="step-number">STEP 01</div>
    <div class="card-title">Select RFP document</div>
    <div class="card-desc">Supports PDF and DOCX files. Text is extracted via LlamaParse for high-fidelity parsing of complex layouts.</div>
  </div>
</div>
""", unsafe_allow_html=True)

        rfp_file = st.file_uploader(
            "Drop your RFP here or click to browse",
            type=["pdf", "docx"],
            key="rfp",
        )

        if rfp_file:
            fsize = len(rfp_file.getbuffer()) / 1024
            st.markdown(f"""
<div style="display:flex; align-items:center; gap:10px; margin:0.75rem 0; padding:10px 14px;
     background:var(--green-lt); border-radius:8px; border:1px solid #A8DEC4;">
  <span>📎</span>
  <div style="flex:1;">
    <div style="font-weight:600; font-size:0.84rem; color:var(--green);">{rfp_file.name}</div>
    <div style="font-size:0.72rem; color:var(--green); opacity:0.7;">{fsize:.1f} KB · Ready to parse</div>
  </div>
</div>
""", unsafe_allow_html=True)

        parse_rfp = st.button(
            "Extract Requirements →",
            disabled=rfp_file is None,
            use_container_width=True,
        )

    with col_info:
        st.markdown('<div class="section-label">How it works</div>', unsafe_allow_html=True)
        for step, icon, desc in [
            ("Parse document", "🔍", "LlamaParse converts your PDF/DOCX into clean markdown, preserving tables and structure."),
            ("Identify requirements", "🧠", "GPT-4 reads the full text and extracts each requirement with ID, category, priority, and description."),
            ("Structure output", "📋", "Requirements are stored as a typed schema ready for proposal comparison."),
        ]:
            st.markdown(f"""
<div style="display:flex; gap:12px; padding:14px 0; border-bottom:1px solid var(--border);">
  <div style="font-size:1.2rem; flex-shrink:0; padding-top:2px;">{icon}</div>
  <div>
    <div style="font-weight:600; font-size:0.85rem; margin-bottom:3px;">{step}</div>
    <div style="font-size:0.8rem; color:var(--ink-60); line-height:1.5;">{desc}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Processing ──
    if parse_rfp and rfp_file is not None:
        with st.spinner("Parsing document with LlamaParse…"):
            rfp_path = _save_upload(rfp_file)
            rfp_text = parse_agent.parse_file(rfp_path)
        with st.spinner("Extracting structured requirements…"):
            requirements_doc = req_agent.extract_requirements(rfp_text)
        st.session_state["rfp_text"] = rfp_text
        st.session_state["requirements_doc"] = requirements_doc
        st.success(f"✓ Successfully extracted {len(requirements_doc.requirements)} requirements from the document.")

    # ── Requirements preview ──
    if "requirements_doc" in st.session_state:
        rd = st.session_state["requirements_doc"]
        st.divider()
        st.markdown('<div class="section-label">Extracted requirements</div>', unsafe_allow_html=True)

        total = len(rd.requirements)
        # Group by category or priority if available
        cats = {}
        for r in rd.requirements:
            cat = getattr(r, "category", None) or getattr(r, "priority", None) or "General"
            cats.setdefault(cat, []).append(r)

        # Summary chips
        chips_html = "".join(f'<span class="chip">{cat} ({len(v)})</span> ' for cat, v in cats.items())
        st.markdown(f"""
<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem;">
  <div style="font-size:0.85rem; color:var(--ink-60);">{total} requirements identified</div>
  <div style="display:flex; gap:6px; flex-wrap:wrap;">{chips_html}</div>
</div>
""", unsafe_allow_html=True)

        col_json, col_text = st.columns([1, 1], gap="large")
        with col_json:
            with st.expander("📋 Requirements JSON", expanded=True):
                st.json(rd.model_dump())
        with col_text:
            with st.expander("📄 RFP text preview", expanded=True):
                preview = st.session_state.get("rfp_text", "")[:5000]
                st.text_area("RFP text preview", value=preview, height=340, label_visibility="collapsed")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: EVALUATE PROPOSALS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏢  Evaluate Proposals":
    st.markdown("""
<div class="page-header">
  <div>
    <div class="page-title">Evaluate <em>Proposals</em></div>
    <div class="page-subtitle">Score vendor submissions against extracted RFP requirements in parallel.</div>
  </div>
</div>
""", unsafe_allow_html=True)

    if not agents_ok:
        st.error(f"⚠ {agent_error}")
        st.stop()

    if "requirements_doc" not in st.session_state:
        st.markdown("""
<div class="empty-state">
  <div class="empty-icon">📄</div>
  <div class="empty-title">No RFP loaded</div>
  <div class="empty-desc">Please go to the <b>Import RFP</b> page first to extract requirements before evaluating proposals.</div>
</div>
""", unsafe_allow_html=True)
        st.stop()

    rd = st.session_state["requirements_doc"]

    col_up, col_cfg = st.columns([1.4, 1], gap="large")

    with col_up:
        st.markdown(f"""
<div style="display:flex; gap:10px; align-items:center; margin-bottom:1rem; padding:12px 16px;
     background:var(--green-lt); border:1px solid #A8DEC4; border-radius:10px;">
  <span>✓</span>
  <div style="font-size:0.84rem; color:var(--green);">
    <b>RFP loaded</b> — {len(rd.requirements)} requirements ready for comparison
  </div>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="section-label">Upload proposals</div>', unsafe_allow_html=True)

        proposal_files = st.file_uploader(
            "Drop proposal PDFs/DOCX files here",
            type=["pdf", "docx"],
            accept_multiple_files=True,
            key="props",
        )

        if proposal_files:
            st.markdown(f"""
<div style="margin:0.75rem 0; padding:10px 14px; background:var(--accent-lt);
     border-radius:8px; border:1px solid #E8C87A; font-size:0.83rem; color:var(--accent);">
  📁 <b>{len(proposal_files)} file(s)</b> selected for evaluation
</div>
""", unsafe_allow_html=True)

        run_eval = st.button(
            "Run Evaluation →",
            disabled=not proposal_files,
            use_container_width=True,
        )

    with col_cfg:
        st.markdown('<div class="section-label">Evaluation config</div>', unsafe_allow_html=True)
        st.markdown(f"""
<div class="card">
  <div class="card-header">Settings</div>
  <div style="display:flex; flex-direction:column; gap:10px;">
    <div style="display:flex; justify-content:space-between; font-size:0.83rem; padding:8px 0; border-bottom:1px solid var(--border);">
      <span style="color:var(--ink-60);">Model</span>
      <span class="chip">{settings.openai_model}</span>
    </div>
    <div style="display:flex; justify-content:space-between; font-size:0.83rem; padding:8px 0; border-bottom:1px solid var(--border);">
      <span style="color:var(--ink-60);">Max parallel workers</span>
      <span class="chip">4</span>
    </div>
    <div style="display:flex; justify-content:space-between; font-size:0.83rem; padding:8px 0;">
      <span style="color:var(--ink-60);">Requirements to check</span>
      <span class="chip">{len(rd.requirements)}</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Processing ──
    if run_eval and proposal_files:
        total = len(proposal_files)
        progress_bar = st.progress(0.0, text=f"Evaluating 0 / {total} proposals…")
        results = [None] * total

        with ThreadPoolExecutor(max_workers=min(total, 4)) as executor:
            future_to_idx = {
                executor.submit(
                    _process_one_proposal, pf, rd, parse_agent, eval_agent, _save_upload
                ): i
                for i, pf in enumerate(proposal_files)
            }
            done = 0
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = e
                done += 1
                progress_bar.progress(done / total, text=f"Evaluating {done} / {total} proposals…")

        progress_bar.empty()

        evaluations, failed = [], []
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                failed.append((proposal_files[i].name, r))
            else:
                evaluations.append(r)

        if failed:
            with st.expander("⚠ Some proposals failed", expanded=True):
                for name, err in failed:
                    st.error(f"{name}: {err}")

        st.session_state["evaluations"] = evaluations
        st.success(f"✓ Evaluation complete — {len(evaluations)} proposal(s) scored. Visit **Results & Analysis** to view rankings.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: RESULTS & ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊  Results & Analysis":
    st.markdown("""
<div class="page-header">
  <div>
    <div class="page-title">Results & <em>Analysis</em></div>
    <div class="page-subtitle">Ranked vendor scorecards with per-requirement evidence and citations.</div>
  </div>
</div>
""", unsafe_allow_html=True)

    if "evaluations" not in st.session_state or not st.session_state["evaluations"]:
        st.markdown("""
<div class="empty-state">
  <div class="empty-icon">📊</div>
  <div class="empty-title">No results yet</div>
  <div class="empty-desc">Complete the <b>Import RFP</b> and <b>Evaluate Proposals</b> steps to see ranked results here.</div>
</div>
""", unsafe_allow_html=True)
        st.stop()

    evs = sorted(st.session_state["evaluations"], key=lambda e: e.match_percentage, reverse=True)

    # ── Summary KPIs ──
    avg_score = sum(e.match_percentage for e in evs) / len(evs)
    top_vendor = evs[0].vendor_name
    shortlisted = sum(1 for e in evs if "recommend" in (getattr(e, "recommendation", "") or "").lower())

    st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-cell">
    <div class="kpi-value">{len(evs)}</div>
    <div class="kpi-label">Vendors scored</div>
  </div>
  <div class="kpi-cell">
    <div class="kpi-value gold">{evs[0].match_percentage:.0f}%</div>
    <div class="kpi-label">Highest match</div>
  </div>
  <div class="kpi-cell">
    <div class="kpi-value">{avg_score:.0f}%</div>
    <div class="kpi-label">Average match</div>
  </div>
  <div class="kpi-cell">
    <div class="kpi-value green">{shortlisted}</div>
    <div class="kpi-label">Shortlisted</div>
  </div>
</div>
""", unsafe_allow_html=True)

    # ── Leaderboard table ──
    st.markdown('<div class="section-label">Vendor leaderboard</div>', unsafe_allow_html=True)

    rank_icons = {0: "🥇", 1: "🥈", 2: "🥉"}
    rows_html = ""
    for i, ev in enumerate(evs):
        met = sum(1 for s in ev.scores if s.met)
        not_met = len(ev.scores) - met
        rec = getattr(ev, "recommendation", "—")
        rank_html = f'{rank_icons.get(i, f"#{i+1}")} '
        rows_html += f"""
<tr>
  <td style="font-size:1.1rem; width:40px; text-align:center;">{rank_icons.get(i, f"<span style='color:var(--ink-60);font-size:0.8rem;'>#{i+1}</span>")}</td>
  <td class="td-vendor">{ev.vendor_name}</td>
  <td>{_score_bar(ev.match_percentage)}</td>
  <td class="td-score"><span style="color:var(--green); font-weight:600;">{met}</span> / {len(ev.scores)}</td>
  <td>{_badge(ev.match_percentage)}</td>
  <td>{_rec_badge(rec)}</td>
</tr>"""

    st.markdown(f"""
<table class="data-table">
  <thead>
    <tr>
      <th>#</th>
      <th>Vendor</th>
      <th>Match score</th>
      <th>Requirements met</th>
      <th>Rating</th>
      <th>Recommendation</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
""", unsafe_allow_html=True)

    # ── Per-vendor detail ──
    st.markdown('<div class="section-label">Detailed scorecards</div>', unsafe_allow_html=True)

    for i, ev in enumerate(evs):
        met_count = sum(1 for s in ev.scores if s.met)
        not_met_count = len(ev.scores) - met_count
        rec = getattr(ev, "recommendation", "—")
        rank_prefix = {0: "🥇 ", 1: "🥈 ", 2: "🥉 "}.get(i, "")

        label = f"{rank_prefix}{ev.vendor_name}   ·   {ev.match_percentage:.1f}% match   ·   {met_count}/{len(ev.scores)} met   ·   {rec}"

        with st.expander(label, expanded=(i == 0)):
            # Vendor header
            st.markdown(f"""
<div class="vendor-header">
  <div class="vendor-name-lg">{ev.vendor_name}</div>
  <div style="display:flex; gap:8px; flex-wrap:wrap;">
    {_badge(ev.match_percentage)}
    {_rec_badge(rec)}
    <span class="badge badge-ink">✅ {met_count} met · ❌ {not_met_count} unmet</span>
  </div>
</div>
""", unsafe_allow_html=True)

            if ev.summary:
                st.markdown(f'<div class="vendor-summary">{ev.summary}</div>', unsafe_allow_html=True)

            # Tabs for met / unmet / all
            tab_all, tab_met, tab_unmet = st.tabs([f"All ({len(ev.scores)})", f"✅ Met ({met_count})", f"❌ Unmet ({not_met_count})"])

            def _render_req_list(scores):
                if not scores:
                    st.markdown('<div style="padding:1rem; color:var(--ink-60); font-size:0.84rem;">No requirements in this category.</div>', unsafe_allow_html=True)
                    return
                rows = ""
                for s in scores:
                    icon = "✅" if s.met else "❌"
                    evidence_html = ""
                    if s.evidences:
                        for e in s.evidences:
                            loc = f'<div class="req-evidence-loc">{e.location}</div>' if getattr(e, "location", None) else ""
                            evidence_html += f'<div class="req-evidence">{loc}"{e.quote}"</div>'
                    else:
                        evidence_html = '<div class="req-evidence" style="font-style:normal; color:var(--ink-30);">No supporting evidence found.</div>'
                    rows += f"""
<div class="req-item">
  <div class="req-icon">{icon}</div>
  <div class="req-body">
    <div class="req-id-tag">{s.requirement_id}</div>
    <div class="req-justification">{s.justification}</div>
    {evidence_html}
  </div>
  <div class="req-confidence">conf {s.confidence:.2f}</div>
</div>"""
                st.markdown(f'<div class="req-list">{rows}</div>', unsafe_allow_html=True)

            with tab_all:
                _render_req_list(ev.scores)
            with tab_met:
                _render_req_list([s for s in ev.scores if s.met])
            with tab_unmet:
                _render_req_list([s for s in ev.scores if not s.met])

        st.write("")