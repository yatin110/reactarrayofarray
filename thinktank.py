"""
Thinktank - Idea Management & Workflow Platform
UBS Investment Bank branded edition.
"""

import streamlit as st
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import uuid

# ==================== PAGE CONFIG ====================

st.set_page_config(
    page_title="UBS Thinktank | Innovation Platform",
    page_icon="🔴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== UBS CUSTOM STYLING ====================

custom_css = """
<style>
    /* ── Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons|Material+Symbols+Rounded');

    :root {
        --ubs-red:       #EC0000;
        --ubs-red-dark:  #B50000;
        --ubs-navy:      #1A1A2E;
        --ubs-navy-mid:  #252545;
        --ubs-white:     #FFFFFF;
        --ubs-offwhite:  #F4F4F4;
        --ubs-border:    #E2E2E2;
        --ubs-text:      #1A1A1A;
        --ubs-muted:     #6B6B6B;
        --ubs-green:     #007A4D;
        --ubs-amber:     #C47200;
        --ubs-orange:    #C44E00;
        color-scheme: light;
    }

    html, body, [data-testid="stAppViewContainer"], .stApp {
        background-color: var(--ubs-offwhite) !important;
        color: var(--ubs-text) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }

    /* ── Hide Streamlit chrome ── */
    #MainMenu, footer { visibility: hidden; }
    [data-testid="stDecoration"] { display: none; }

    /* ── Main content padding ── */
    [data-testid="stAppViewContainer"] > .main > .block-container {
        padding-top: 0 !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
        max-width: 1400px;
    }

    /* ══════════════════════════════
       SIDEBAR — dark navy rail
    ══════════════════════════════ */
    [data-testid="stSidebar"] {
        background: var(--ubs-navy) !important;
        border-right: 3px solid var(--ubs-red) !important;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
        font-family: 'Inter', sans-serif !important;
    }
    [data-testid="stSidebar"] .stTextInput > div > div > input {
        background: rgba(255,255,255,0.08) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        color: #FFFFFF !important;
        border-radius: 4px !important;
    }
    [data-testid="stSidebar"] .stTextInput > div > div > input::placeholder {
        color: rgba(255,255,255,0.45) !important;
    }
    [data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: var(--ubs-red) !important;
        font-size: 1.4rem !important;
        font-weight: 700 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMetricLabel"] {
        color: rgba(255,255,255,0.65) !important;
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.12) !important;
    }
    [data-testid="stSidebar"] label {
        color: rgba(255,255,255,0.75) !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* ══════════════════════════════
       HEADER BANNER
    ══════════════════════════════ */
    .ubs-header {
        background: var(--ubs-white);
        padding: 1.8rem 2.5rem 1.4rem;
        margin: 0 -2.5rem 2rem;
        border-bottom: 4px solid var(--ubs-red);
        display: flex;
        align-items: center;
        gap: 1.4rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        animation: slideDown 0.5s ease-out;
    }
    @keyframes slideDown {
        from { opacity: 0; transform: translateY(-12px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .ubs-logo-mark {
        background: var(--ubs-red);
        color: #fff;
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: -1px;
        padding: 0.35rem 0.8rem;
        border-radius: 3px;
        line-height: 1;
        font-family: 'Inter', sans-serif;
        flex-shrink: 0;
    }
    .ubs-header-text {}
    .ubs-header-title {
        font-size: 1.55rem;
        font-weight: 700;
        color: var(--ubs-text) !important;
        margin: 0;
        letter-spacing: -0.5px;
        line-height: 1.1;
    }
    .ubs-header-subtitle {
        font-size: 0.82rem;
        color: var(--ubs-muted) !important;
        margin: 0.2rem 0 0;
        font-weight: 400;
        letter-spacing: 0.2px;
    }
    .ubs-header-divider {
        width: 1px;
        height: 40px;
        background: var(--ubs-border);
        margin: 0 0.5rem;
    }
    .ubs-header-tagline {
        font-size: 0.78rem;
        color: var(--ubs-muted) !important;
        font-weight: 400;
        border-left: 2px solid var(--ubs-red);
        padding-left: 0.8rem;
        line-height: 1.4;
    }

    /* ══════════════════════════════
       STAT CARDS
    ══════════════════════════════ */
    .stat-card {
        background: var(--ubs-white);
        border: 1px solid var(--ubs-border);
        border-top: 4px solid var(--ubs-red);
        border-radius: 4px;
        padding: 1.4rem 1.2rem;
        text-align: center;
        box-shadow: 0 1px 6px rgba(0,0,0,0.06);
        transition: box-shadow 0.25s ease, transform 0.25s ease;
        animation: fadeUp 0.5s ease-out backwards;
    }
    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(10px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    .stat-card:hover {
        box-shadow: 0 6px 20px rgba(0,0,0,0.10);
        transform: translateY(-3px);
    }
    .stat-number {
        font-size: 2.1rem;
        font-weight: 800;
        color: var(--ubs-red) !important;
        letter-spacing: -1.5px;
        line-height: 1;
    }
    .stat-label {
        font-size: 0.7rem;
        color: var(--ubs-muted) !important;
        margin-top: 0.45rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }

    /* ══════════════════════════════
       IDEA CARDS
    ══════════════════════════════ */
    /* Card container — uses st.container(border=True) wrapper */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--ubs-white) !important;
        border: 1px solid var(--ubs-border) !important;
        border-left: 4px solid var(--ubs-red) !important;
        border-radius: 4px !important;
        margin-bottom: 1.2rem !important;
        box-shadow: 0 1px 5px rgba(0,0,0,0.06) !important;
        transition: box-shadow 0.25s ease, transform 0.25s ease !important;
        padding: 0 !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.10) !important;
        transform: translateY(-2px) !important;
    }
    /* Inner content padding */
    [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] {
        padding: 1.4rem 1.6rem 1rem !important;
    }
    /* Expander inside card — flush, no outer border */
    [data-testid="stVerticalBlockBorderWrapper"] .stExpander {
        border: none !important;
        border-top: 1px solid var(--ubs-border) !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        margin: 0.5rem -1.6rem 0 !important;
        padding: 0 1.6rem !important;
    }
    .idea-card {
        padding: 0;
        margin: 0;
    }
    .idea-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: var(--ubs-text) !important;
        margin-bottom: 0.3rem;
        letter-spacing: -0.3px;
    }
    .idea-meta {
        font-size: 0.78rem;
        color: var(--ubs-muted) !important;
        margin-bottom: 0.9rem;
        display: flex;
        gap: 0.6rem;
        align-items: center;
    }
    .idea-description {
        font-size: 0.92rem;
        color: #3a3a3a !important;
        line-height: 1.65;
        margin-bottom: 1.1rem;
    }
    .idea-stats-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.8rem;
        padding-top: 1rem;
        border-top: 1px solid var(--ubs-border);
    }
    .idea-stat-item {
        text-align: center;
    }
    .idea-stat-num {
        font-size: 1.3rem;
        font-weight: 700;
    }
    .idea-stat-label {
        font-size: 0.68rem;
        color: var(--ubs-muted) !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 500;
        margin-top: 0.2rem;
    }

    /* ══════════════════════════════
       BADGES / PILLS
    ══════════════════════════════ */
    .badge {
        display: inline-block;
        background: #F0F0F0;
        color: var(--ubs-text) !important;
        padding: 0.28rem 0.7rem;
        border-radius: 3px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.3px;
        border: 1px solid var(--ubs-border);
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
    }
    .badge-status-implemented {
        background: #E6F4EE !important;
        color: var(--ubs-green) !important;
        border-color: var(--ubs-green) !important;
    }
    .badge-status-in-progress {
        background: #FFF3E0 !important;
        color: var(--ubs-orange) !important;
        border-color: var(--ubs-orange) !important;
    }
    .badge-status-pending {
        background: #FFF8E6 !important;
        color: var(--ubs-amber) !important;
        border-color: var(--ubs-amber) !important;
    }

    /* ══════════════════════════════
       BUTTONS
    ══════════════════════════════ */
    .stButton > button,
    [data-testid="stFormSubmitButton"] > button {
        background: #FFFFFF !important;
        color: var(--ubs-red) !important;
        border: 1px solid var(--ubs-red) !important;
        border-radius: 3px !important;
        padding: 0.35rem 1.1rem !important;
        font-weight: 600 !important;
        font-size: 0.78rem !important;
        font-family: 'Inter', sans-serif !important;
        letter-spacing: 0.2px !important;
        transition: background 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease !important;
        box-shadow: 0 1px 4px rgba(236,0,0,0.1) !important;
        min-width: 100px;
        max-width: 180px;
        white-space: nowrap;
    }
    .stButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        background: #F8F8F8 !important;
        box-shadow: 0 3px 10px rgba(236,0,0,0.15) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button:active,
    [data-testid="stFormSubmitButton"] > button:active { transform: translateY(0) !important; }
    .stButton > button:disabled {
        background: #F9F9F9 !important;
        color: #A0A0A0 !important;
        border: 1px solid #DDDDDD !important;
        box-shadow: none !important;
        transform: none !important;
    }
    /* Right-align button rows */
    .btn-row-right {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        margin-top: 0.5rem;
    }

    /* ══════════════════════════════
       TABS
    ══════════════════════════════ */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 2px solid var(--ubs-border) !important;
        gap: 0 !important;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: var(--ubs-muted) !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.85rem 1.4rem !important;
        border-bottom: 3px solid transparent !important;
        background: transparent !important;
        transition: color 0.2s, border-color 0.2s !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--ubs-red) !important;
        border-bottom: 3px solid var(--ubs-red) !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--ubs-red) !important;
        background: rgba(236,0,0,0.04) !important;
    }

    /* ══════════════════════════════
       FORM INPUTS
    ══════════════════════════════ */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border: 1px solid var(--ubs-border) !important;
        border-radius: 3px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9rem !important;
        color: var(--ubs-text) !important;
        background: #FFFFFF !important;
        transition: border-color 0.2s !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--ubs-red) !important;
        box-shadow: 0 0 0 3px rgba(236,0,0,0.10) !important;
    }
    .stSelectbox > div > div {
        border: 1px solid var(--ubs-border) !important;
        border-radius: 3px !important;
        background: #FFFFFF !important;
        color: var(--ubs-text) !important;
    }

    /* ══════════════════════════════
       EXPANDER
    ══════════════════════════════ */
    .stExpander {
        background: var(--ubs-white) !important;
        border: 1px solid var(--ubs-border) !important;
        border-left: 4px solid var(--ubs-red) !important;
        border-radius: 4px !important;
        transition: box-shadow 0.25s !important;
    }
    .stExpander:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
    }

    /* ══════════════════════════════
       PROGRESS BAR
    ══════════════════════════════ */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--ubs-red), var(--ubs-red-dark)) !important;
    }

    /* ══════════════════════════════
       METRICS (main area)
    ══════════════════════════════ */
    [data-testid="stMetricValue"] {
        color: var(--ubs-red) !important;
        font-weight: 700 !important;
    }

    /* ══════════════════════════════
       TYPOGRAPHY
    ══════════════════════════════ */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        color: var(--ubs-text) !important;
        font-weight: 700 !important;
        letter-spacing: -0.3px !important;
    }
    p, div, label {
        font-family: 'Inter', sans-serif !important;
    }
    /* Restore Material Icons font for Streamlit icon spans (expander arrow, etc.) */
    [data-testid="stSidebar"] .material-symbols-rounded,
    [data-testid="stSidebar"] .material-icons,
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="stExpanderToggleIcon"],
    [data-testid="stExpanderToggleIcon"] span,
    .material-icons, .material-symbols-outlined, .material-symbols-rounded {
        font-family: 'Material Icons', 'Material Symbols Rounded' !important;
        font-size: 1.2rem !important;
        font-style: normal !important;
        font-weight: normal !important;
        text-rendering: optimizeLegibility !important;
        -webkit-font-smoothing: antialiased !important;
    }
    hr {
        border-color: var(--ubs-border) !important;
        opacity: 1 !important;
    }

    /* ══════════════════════════════
       COMMENT CARD
    ══════════════════════════════ */
    .comment-card {
        background: #FAFAFA;
        border-left: 3px solid var(--ubs-red);
        border-radius: 3px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.75rem;
    }
    .comment-author {
        font-weight: 600;
        font-size: 0.82rem;
        color: var(--ubs-text) !important;
        margin-bottom: 0.3rem;
    }
    .comment-text {
        font-size: 0.88rem;
        color: #3a3a3a !important;
        line-height: 1.55;
    }

    /* ══════════════════════════════
       ALERT / INFO BOXES
    ══════════════════════════════ */
    [data-testid="stAlert"] {
        border-radius: 4px !important;
        font-family: 'Inter', sans-serif !important;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

dark_css = """
<style>
:root {
    --ubs-white:     #1E1E24 !important;
    --ubs-offwhite:  #121212 !important;
    --ubs-border:    #333333 !important;
    --ubs-text:      #F0F0F0 !important;
    --ubs-muted:     #999999 !important;
}
.idea-description { color: #E0E0E0 !important; }
.comment-card { background: #18181A !important; }
.badge { background: #333333 !important; color: #FFFFFF !important; border-color: #444444 !important; }
.badge-status-implemented { background: rgba(0, 122, 77, 0.2) !important; color: #4CAF50 !important; border-color: transparent !important; }
.badge-status-in-progress { background: rgba(196, 78, 0, 0.2) !important; color: #FFA726 !important; border-color: transparent !important; }
.badge-status-pending { background: rgba(196, 114, 0, 0.2) !important; color: #FFCA28 !important; border-color: transparent !important; }
.stat-card {
    background: #1E1E24 !important;
    border: 1px solid #333333 !important;
    box-shadow: 0 1px 6px rgba(0,0,0,0.6) !important;
}
.ubs-header { background: #1E1E24 !important; border-bottom: 4px solid var(--ubs-red); }
.stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div {
    background: #1E1E24 !important; 
    color: #F0F0F0 !important; 
    border-color: #444444 !important; 
}
[data-testid="stVerticalBlockBorderWrapper"] { background: #1E1E24 !important; border-color: #333333 !important; box-shadow: 0 1px 5px rgba(0,0,0,0.6) !important;}
.stExpander { background: #1E1E24 !important; border-color: #333333 !important;}
</style>
"""

# ==================== DATA MANAGEMENT ====================

DATA_FILE = "thinktank_data.json"

def load_data() -> Dict[str, Any]:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"ideas": [], "users": []}

def save_data(data: Dict[str, Any]):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_or_create_user(username: str) -> str:
    data = load_data()
    for user in data.get("users", []):
        if user["name"].lower() == username.lower():
            return user["id"]
    user_id = str(uuid.uuid4())[:8]
    data["users"].append({
        "id": user_id,
        "name": username,
        "created_at": datetime.now().isoformat()
    })
    save_data(data)
    return user_id

def create_idea(title: str, problem_statement: str, idea_description: str, initial_thoughts: str, category: str, submitter: str) -> str:
    data = load_data()
    idea_id = str(uuid.uuid4())[:8]
    idea = {
        "id": idea_id,
        "title": title,
        "description": idea_description,
        "problem_statement": problem_statement,
        "initial_thoughts": initial_thoughts,
        "category": category,
        "submitter": submitter,
        "submitter_id": get_or_create_user(submitter),
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "votes": [],
        "comments": [],
        "team_members": [],
    }
    data["ideas"].append(idea)
    save_data(data)
    return idea_id

def get_idea(idea_id: str) -> Dict[str, Any] | None:
    data = load_data()
    for idea in data.get("ideas", []):
        if idea["id"] == idea_id:
            return idea
    return None

def update_idea(idea_id: str, updates: Dict[str, Any]):
    data = load_data()
    for idea in data.get("ideas", []):
        if idea["id"] == idea_id:
            idea.update(updates)
            save_data(data)
            return
    save_data(data)

def vote_on_idea(idea_id: str, user: str, vote_type: str) -> bool:
    data = load_data()
    user_id = get_or_create_user(user)
    for idea in data.get("ideas", []):
        if idea["id"] == idea_id:
            idea["votes"] = [v for v in idea.get("votes", []) if v["user_id"] != user_id]
            if vote_type in ["upvote", "downvote"]:
                idea["votes"].append({
                    "user_id": user_id,
                    "user": user,
                    "type": vote_type,
                    "timestamp": datetime.now().isoformat()
                })
            save_data(data)
            return True
    return False

def add_comment(idea_id: str, user: str, comment_text: str) -> bool:
    data = load_data()
    user_id = get_or_create_user(user)
    for idea in data.get("ideas", []):
        if idea["id"] == idea_id:
            idea["comments"].append({
                "id": str(uuid.uuid4())[:8],
                "user_id": user_id,
                "user": user,
                "text": comment_text,
                "timestamp": datetime.now().isoformat()
            })
            save_data(data)
            return True
    return False

def add_team_member(idea_id: str, user: str, role: str) -> bool:
    data = load_data()
    user_id = get_or_create_user(user)
    for idea in data.get("ideas", []):
        if idea["id"] == idea_id:
            for member in idea.get("team_members", []):
                if member["user_id"] == user_id:
                    return False
            idea["team_members"].append({
                "user_id": user_id,
                "user": user,
                "role": role,
                "joined_at": datetime.now().isoformat()
            })
            save_data(data)
            return True
    return False

def remove_team_member(idea_id: str, user: str) -> bool:
    data = load_data()
    user_id = get_or_create_user(user)
    for idea in data.get("ideas", []):
        if idea["id"] == idea_id:
            initial_count = len(idea.get("team_members", []))
            idea["team_members"] = [m for m in idea.get("team_members", []) if m["user_id"] != user_id]
            if len(idea["team_members"]) < initial_count:
                save_data(data)
                return True
            return False
    return False

def get_all_ideas() -> List[Dict[str, Any]]:
    data = load_data()
    ideas = data.get("ideas", [])
    return sorted(ideas, key=lambda x: x["created_at"], reverse=True)

def get_ideas_by_category(category: str) -> List[Dict[str, Any]]:
    return [idea for idea in get_all_ideas() if idea["category"].lower() == category.lower()]

def get_ideas_by_status(status: str) -> List[Dict[str, Any]]:
    return [idea for idea in get_all_ideas() if idea["status"].lower() == status.lower()]

# ==================== UI COMPONENTS ====================

def render_header():
    st.markdown("""
    <div class="ubs-header">
        <div class="ubs-logo-mark">UBS</div>
        <div class="ubs-header-text">
            <div class="ubs-header-title">Thinktank</div>
            <div class="ubs-header-subtitle">Platform Efficiency, Risk Insights</div>
        </div>
        <div class="ubs-header-divider"></div>
        <div class="ubs-header-tagline">
            Collaborate · Innovate · Execute
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_idea_card(idea: Dict[str, Any], show_actions: bool = True):
    upvotes = len([v for v in idea.get("votes", []) if v["type"] == "upvote"])
    comments_count = len(idea.get("comments", []))
    team_count = len(idea.get("team_members", []))

    user_id = get_or_create_user(st.session_state.current_user)
    user_has_upvoted = any(
        v["user_id"] == user_id and v["type"] == "upvote"
        for v in idea.get("votes", [])
    )
    user_in_team = any(
        m["user_id"] == user_id
        for m in idea.get("team_members", [])
    )

    status_class = f"badge-status-{idea['status']}"
    created_date = datetime.fromisoformat(idea["created_at"]).strftime("%d %b %Y")

    upvote_color = "#007A4D"
    comment_color = "#C47200"
    team_color = "#1353A0"

    comments_html = ""
    for comment in idea.get("comments", []):
        comment_date = comment.get('timestamp', '')[:10]
        comments_html += f"""
        <div class="comment-card">
            <div class="comment-author">&#128100; {comment['user']} &nbsp;&middot;&nbsp; {comment_date}</div>
            <div class="comment-text">{comment['text']}</div>
        </div>"""

    team_members_html = ""
    if idea.get("team_members"):
        team_names = ", ".join(m["user"] for m in idea["team_members"])
        team_members_html = f"""
        <div style="font-size:0.8rem; color:#6B6B6B; margin-bottom:0.4rem; padding: 0.5rem 0.8rem; background:#F9F9F9; border-left:3px solid {team_color}; border-radius:3px;">
            <strong>Current Team:</strong> {team_names}
        </div>
        """

    upvoters_html = ""
    upvoters = [v["user"] for v in idea.get("votes", []) if v["type"] == "upvote"]
    if upvoters:
        upvoters_names = ", ".join(upvoters)
        upvoters_html = f"""
        <div style="font-size:0.8rem; color:#6B6B6B; margin-bottom:0.9rem; padding: 0.5rem 0.8rem; background:#F9F9F9; border-left:3px solid {upvote_color}; border-radius:3px;">
            <strong>Upvoted by:</strong> {upvoters_names}
        </div>
        """

    # Normalize "approved" to "implemented" just for display incase of legacy data
    display_status = "implemented" if idea.get('status', '').lower() == "approved" else idea.get('status', 'pending').lower()

    # ── Everything inside one bordered container = one card ──
    with st.container(border=True):
        # Static info rendered as HTML
        st.html(f"""
        <div style="padding:0;">
            <div class="idea-title">{idea['title']}</div>
            <div class="idea-meta">
                &#128100; <strong>{idea['submitter']}</strong>
                &nbsp;&middot;&nbsp; &#128197; {created_date}
            </div>
            <div style="margin-bottom:0.9rem; display:flex; align-items:center; flex-wrap:wrap;">
                <span class="badge">{idea['category']}</span>
                <span class="badge {status_class}" style="margin-right:0.8rem;">{display_status.upper()}</span>
                <span style="font-size:0.85rem; font-weight:600; color:{upvote_color}; margin-right:0.6rem;">
                    &#128077; {upvotes} Upvotes
                </span>
                <span style="font-size:0.85rem; font-weight:600; color:{team_color};">
                    &#128101; {team_count} Team
                </span>
            </div>
            {f'''<div class="idea-description" style="margin-top: 0.5rem;">
                <strong>Problem Statement:</strong><br/>
                {idea.get('problem_statement')}
            </div>''' if idea.get('problem_statement') else ''}
            
            {f'''<div class="idea-description" style="margin-top: 0.5rem;">
                <strong>Idea Description:</strong><br/>
                {idea.get('description')}
            </div>''' if idea.get('description') else ''}

            {f'''<div class="idea-description" style="margin-top: 0.5rem;">
                <strong>Initial Thoughts:</strong><br/>
                {idea.get('initial_thoughts')}
            </div>''' if idea.get('initial_thoughts') else ''}
            {team_members_html}
            {upvoters_html}
        </div>
        """)

        # Comments expander — inside the card container
        expander_label = f"&#128172; {comments_count} Comment(s)" if comments_count else "&#128172; Comments"
        with st.expander(expander_label, expanded=False):
            if comments_html:
                st.html(f"<div>{comments_html}</div>")
            else:
                st.markdown(
                    "<p style='color:#6B6B6B;font-size:0.85rem;margin:0.4rem 0 0.8rem;'>"
                    "No comments yet &#8212; be the first!</p>",
                    unsafe_allow_html=True
                )
            with st.form(key=f"inline_comment_{idea['id']}", clear_on_submit=True):
                new_comment = st.text_area(
                    "comment",
                    placeholder="Share your thoughts, suggestions, or questions\u2026",
                    height=80,
                    label_visibility="collapsed"
                )
                _, btn_col = st.columns([3, 1])
                with btn_col:
                    if st.form_submit_button("Post Comment", use_container_width=True):
                        if new_comment.strip():
                            add_comment(idea['id'], st.session_state.current_user, new_comment.strip())
                            st.success("Comment posted!", icon="\u2705")
                            st.rerun()
                        else:
                            st.warning("Please enter a comment before posting.")

        # Action buttons — inside the card, right-aligned
        if show_actions:
            sp, col1, col2 = st.columns([4, 1, 1], gap="small")
            with col1:
                label = "Upvoted" if user_has_upvoted else "Upvote"
                if st.button(label, key=f"upvote_{idea['id']}", use_container_width=True, disabled=user_has_upvoted):
                    vote_on_idea(idea['id'], st.session_state.current_user, "upvote")
                    st.success("Vote recorded!", icon="\u2705")
                    st.rerun()
            with col2:
                if user_in_team:
                    if st.button("Leave Team", key=f"join_{idea['id']}", use_container_width=True):
                        remove_team_member(idea['id'], st.session_state.current_user)
                        st.success("You've left the team.", icon="🗑️")
                        st.rerun()
                else:
                    if st.button("Join Team", key=f"join_{idea['id']}", use_container_width=True):
                        add_team_member(idea['id'], st.session_state.current_user, "Contributor")
                        st.success("You've joined the team!", icon="\u2705")
                        st.rerun()


def render_stats():
    all_ideas = get_all_ideas()
    pending_ideas   = get_ideas_by_status("pending")
    in_progress     = get_ideas_by_status("in-progress")
    implemented     = get_ideas_by_status("implemented") + get_ideas_by_status("approved")
    total_users     = len(load_data().get("users", []))
    total_votes     = sum(len(idea.get("votes", [])) for idea in all_ideas)
    total_comments  = sum(len(idea.get("comments", [])) for idea in all_ideas)

    with st.expander("View Platform Statistics", expanded=False):
        st.markdown("### Platform Overview")
        c1, c2, c3, c4 = st.columns(4)
        cards = [
            (c1, len(all_ideas),    "Total Ideas",       "#EC0000"),
            (c2, total_users,       "Contributors",      "#EC0000"),
            (c3, total_votes,       "Total Votes",       "#EC0000"),
            (c4, total_comments,    "Discussions",       "#EC0000"),
        ]
        for col, num, label, color in cards:
            with col:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-number" style="color:{color};">{num}</div>
                    <div class="stat-label">{label}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
        st.markdown("### Status Statistics")
        s1, s2, s3 = st.columns(3)
        status_cards = [
            (s1, len(pending_ideas), "Pending Review",  "#C47200", "#FFF8E6"),
            (s2, len(in_progress),  "In Progress",     "#C44E00", "#FFF3E0"),
            (s3, len(implemented),  "Implemented",     "#007A4D", "#E6F4EE"),
        ]
        for col, num, label, color, bg in status_cards:
            with col:
                st.markdown(f"""
                <div class="stat-card" style="border-top-color:{color}; background:{bg};">
                    <div class="stat-number" style="color:{color};">{num}</div>
                    <div class="stat-label" style="color:{color};">{label}</div>
                </div>""", unsafe_allow_html=True)
        st.write("")
        st.write("")

# ==================== MAIN APP ====================

def main():
    if "current_user" not in st.session_state:
        st.session_state.current_user = "User_" + str(uuid.uuid4())[:4]
    if "selected_idea_for_team" not in st.session_state:
        st.session_state.selected_idea_for_team = None

    # ── Sidebar ──────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style='text-align:center; padding: 1rem 0 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.12); margin-bottom:1.2rem;'>
            <div style='font-size:0.68rem; color:rgba(255,255,255,0.55); text-transform:uppercase; letter-spacing:1.5px; margin-top:0.1rem;'>Thinktank </div>
        </div>
        """, unsafe_allow_html=True)

        st.session_state.current_user = "yatin.mehta@ubs.com"

        st.markdown("---")
        st.markdown("**Your Activity**")

        all_ideas = get_all_ideas()
        my_ideas    = [i for i in all_ideas if i["submitter"].lower() == st.session_state.current_user.lower()]
        my_votes    = sum(len([v for v in i.get("votes", []) if v["user"] == st.session_state.current_user]) for i in all_ideas)
        my_comments = sum(len([c for c in i.get("comments", []) if c["user"] == st.session_state.current_user]) for i in all_ideas)

        c1, c2 = st.columns(2)
        with c1:
            st.metric("My Ideas", len(my_ideas))
        with c2:
            st.metric("My Votes", my_votes)
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Comments", my_comments)
        with c2:
            st.metric("Contributors", len(load_data().get("users", [])))

        st.markdown("---")

    # ── Top Right Theme Toggle ──
    _, col_theme = st.columns([9, 1])
    with col_theme:
        is_dark = st.toggle("🌙 Dark", key="theme_toggle")
    
    if is_dark:
        st.markdown(dark_css, unsafe_allow_html=True)


    # ── Header & Stats ────────────────────────────────
    render_header()
    render_stats()
    st.markdown("---")

    # ── Main Tabs ─────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "All Ideas",
        "Submit Idea",
        "Manage"
    ])

    # ── TAB 1: ALL IDEAS ─────────────────────────────
    with tab1:
        st.markdown("### Latest Ideas")
        ideas = get_all_ideas()

        if not ideas:
            st.info("No ideas yet — be the first! Click **Submit Idea** to get started.", icon="💡")
        else:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                search_query = st.text_input(
                    "Search",
                    placeholder="Search keywords...",
                    key="filter_search"
                )
            with col2:
                category_filter = st.selectbox(
                    "Filter by Category",
                    options=["All Categories"] + sorted(list(set([i["category"] for i in ideas]))),
                    key="filter_category"
                )
            with col3:
                status_filter = st.selectbox(
                    "Filter by Status",
                    options=["All Status", "pending", "in-progress", "implemented"],
                    key="filter_status"
                )
            with col4:
                sort_option = st.selectbox(
                    "Sort by",
                    options=["Newest", "Most Voted", "Most Discussed"],
                    key="sort_option"
                )

            filtered_ideas = ideas
            if search_query:
                filtered_ideas = [
                    i for i in filtered_ideas
                    if search_query.lower() in i["title"].lower()
                    or search_query.lower() in i.get("description", "").lower()
                    or search_query.lower() in i.get("problem_statement", "").lower()
                    or search_query.lower() in i.get("initial_thoughts", "").lower()
                ]
            if category_filter != "All Categories":
                filtered_ideas = [i for i in filtered_ideas if i["category"] == category_filter]
            if status_filter != "All Status":
                filtered_ideas = [i for i in filtered_ideas if i["status"] == status_filter]
            if sort_option == "Most Voted":
                filtered_ideas = sorted(filtered_ideas, key=lambda x: len(x.get("votes", [])), reverse=True)
            elif sort_option == "Most Discussed":
                filtered_ideas = sorted(filtered_ideas, key=lambda x: len(x.get("comments", [])), reverse=True)

            if not filtered_ideas:
                st.info("No ideas match your filters.", icon="🔍")
            else:
                st.markdown(f"<p style='color:#6B6B6B; font-size:0.85rem; margin-bottom:1rem;'>Showing <strong>{len(filtered_ideas)}</strong> of <strong>{len(ideas)}</strong> ideas</p>", unsafe_allow_html=True)
                for idea in filtered_ideas:
                    render_idea_card(idea)

    # ── TAB 2: SUBMIT IDEA ───────────────────────────
    with tab2:
        st.markdown("### Submit a New Idea")
        st.markdown("<p style='color:#6B6B6B; margin-bottom:1.5rem;'>Share your innovative ideas with the team. Great ideas drive UBS forward.</p>", unsafe_allow_html=True)

        with st.form("submit_idea_form", border=True):
            col_t, col_c = st.columns([2, 1])
            with col_t:
                title = st.text_input(
                    "Idea Title *",
                    placeholder="Give your idea a clear, concise title…",
                    help="Make it memorable and descriptive"
                )
            with col_c:
                cat_list = [
                    "Business benefit", "Technology improvement", "Developer experience",
                    "Time to market", "Performance improvement", "Data Quality", "process", "Other"
                ]
                category = st.selectbox(
                    "Category *",
                    options=cat_list,
                    help="Choose the most relevant category"
                )

            problem_statement = st.text_area(
                "Problem Statement",
                placeholder="What exactly is the problem you are trying to solve?",
                height=100
            )
            idea_description = st.text_area(
                "Idea Description *",
                placeholder="Describe your idea in detail...",
                height=100
            )
            initial_thoughts = st.text_area(
                "Initial thoughts on how this can be implemented",
                placeholder="How do you envision this solution coming to life?",
                height=100
            )
            
            _, col_btn = st.columns([3, 1])
            with col_btn:
                submitted = st.form_submit_button("Submit Idea", use_container_width=True)

            if submitted:
                if not title.strip() or not idea_description.strip():
                    st.error("Please fill in all required fields (Idea Title and Idea Description).")
                else:
                    idea_id = create_idea(title.strip(), problem_statement.strip(), idea_description.strip(), initial_thoughts.strip(), category, st.session_state.current_user)
                    st.success(f"Idea submitted successfully! Reference: `{idea_id}`", icon="✅")

    # ── TAB 3: MANAGE ────────────────────────────────
    with tab3:
        st.markdown("### Manage Ideas")
        all_ideas = get_all_ideas()
        current_uid = get_or_create_user(st.session_state.current_user)

        my_ideas = [i for i in all_ideas if get_or_create_user(i["submitter"]) == current_uid]
        my_team_ideas = [
            i for i in all_ideas
            if any(m.get("user_id") == current_uid for m in i.get("team_members", []))
        ]

        col1, col2 = st.columns(2, gap="large")

        with col1:
            st.markdown(f"#### My Submitted Ideas &nbsp; `{len(my_ideas)}`")
            if my_ideas:
                for idea in my_ideas:
                    with st.expander(f" {idea['title']} — {idea['status'].upper()}", expanded=False):
                        st.markdown(f"**Submitted by:** {idea['submitter']}")
                        st.markdown(f"**Category:** {idea['category']}")
                        ci, cj, ck = st.columns(3)
                        with ci:
                            st.metric("Team", len(idea.get('team_members', [])))
                        with cj:
                            st.metric("Comments", len(idea.get('comments', [])))
                        with ck:
                            st.metric("Votes", len(idea.get('votes', [])))
                            
                        st.markdown("**Update Status**")
                        status_options = ["pending", "in-progress", "implemented", "approved"]
                        display_status = "implemented" if idea["status"] == "approved" else idea["status"]
                        current_status_idx = status_options.index(display_status) if display_status in status_options else 0
                        new_status = st.radio(
                            "Change status to",
                            options=["pending", "in-progress", "implemented"],
                            index=min(current_status_idx, 2),
                            key=f"my_status_radio_{idea['id']}",
                            horizontal=True
                        )
                        if st.button("Save Status", use_container_width=True, key=f"my_save_status_{idea['id']}"):
                            update_idea(idea["id"], {"status": new_status})
                            st.success("Status updated successfully!", icon="✅")
                            st.rerun()
            else:
                st.info("You haven't submitted any ideas yet. Use the **Submit Idea** tab to get started.", icon="💡")

        with col2:
            st.markdown(f"#### Team Ideas &nbsp; `{len(my_team_ideas)}`")
            if my_team_ideas:
                for idea in my_team_ideas:
                    with st.expander(f" {idea['title']} — {idea['status'].upper()}", expanded=False):
                        st.markdown(f"**Submitted by:** {idea['submitter']}")
                        st.markdown(f"**Category:** {idea['category']}")
                        ci, cj, ck = st.columns(3)
                        with ci:
                            st.metric("Team", len(idea['team_members']))
                        with cj:
                            st.metric("Comments", len(idea['comments']))
                        with ck:
                            st.metric("Votes", len(idea['votes']))
                            
                        st.markdown("**Update Status**")
                        status_options = ["pending", "in-progress", "implemented", "approved"]
                        display_status = "implemented" if idea["status"] == "approved" else idea["status"]
                        current_status_idx = status_options.index(display_status) if display_status in status_options else 0
                        new_status = st.radio(
                            "Change status to",
                            options=["pending", "in-progress", "implemented"],
                            index=min(current_status_idx, 2),
                            key=f"team_status_radio_{idea['id']}",
                            horizontal=True
                        )
                        if st.button("💾 Save Status", use_container_width=True, key=f"team_save_status_{idea['id']}"):
                            update_idea(idea["id"], {"status": new_status})
                            st.success("Status updated successfully!", icon="✅")
                            st.rerun()
            else:
                st.info("You're not part of any team yet. Click **Join Team** on an idea to get involved.", icon="👥")

if __name__ == "__main__":
    main()
