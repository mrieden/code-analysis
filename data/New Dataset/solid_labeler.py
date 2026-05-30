"""
SOLID Principles Labeling Tool
--------------------------------
- Starts with no labels (all blank)
- Label each snippet one by one
- Auto-saves after every label → resume exactly where you left off
- Export final labeled Excel at any time

Usage:
    streamlit run solid_labeler.py
"""

import streamlit as st
import pandas as pd
import json
import os
import html as htmllib
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
SOURCE_FILE   = "python-codes-unlabeled.xlsx"   # original, never modified
PROGRESS_FILE = "labeling_progress.json"         # auto-saved progress (resume here)
EXPORT_FILE   = "python-codes-labeled.xlsx"      # final export

PRINCIPLES = ["SRP", "OCP", "LSP", "ISP", "DIP"]
OPTIONS    = ["Pass", "Violation"]

PRINCIPLE_HELP = {
    "SRP": "Each class/function has ONE reason to change. Violation: a class handles multiple unrelated concerns.",
    "OCP": "Open for extension, closed for modification. Violation: adding features requires editing existing if/elif chains.",
    "LSP": "Subclasses can replace base classes without breaking behaviour. Violation: subclass changes/removes base behaviour.",
    "ISP": "Interfaces are focused; clients only depend on what they use. Violation: classes implement methods they don't need.",
    "DIP": "High-level modules depend on abstractions, not concrete classes. Violation: direct instantiation of low-level classes.",
}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SOLID Labeler",
    page_icon="🏷️",
    layout="wide",
)

st.markdown("""
<style>
.code-box {
    background: #1e1e1e;
    color: #d4d4d4;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    padding: 18px 20px;
    border-radius: 10px;
    white-space: pre;
    overflow: auto;
    max-height: 460px;
    line-height: 1.55;
}
.badge-pass      { background:#d4edda; color:#155724; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:600; margin-right:6px; }
.badge-violation { background:#f8d7da; color:#721c24; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:600; margin-right:6px; }
.badge-empty     { background:#e9ecef; color:#6c757d; padding:4px 12px; border-radius:20px; font-size:12px; margin-right:6px; }
.row-counter     { font-size:15px; color:#6c757d; text-align:center; margin:0; }
</style>
""", unsafe_allow_html=True)


# ── Load source data (read-only, cached) ──────────────────────────────────────
@st.cache_data
def load_source():
    df = pd.read_excel(SOURCE_FILE, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    df["code"] = df["code"].fillna("")
    df["id"]   = df["id"].astype(str)
    return df.reset_index(drop=True)


# ── Progress helpers ──────────────────────────────────────────────────────────
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"labels": {}, "current_pos": 0, "saved_at": None}


def persist(labels: dict, pos: int):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({
            "labels":      labels,
            "current_pos": pos,
            "saved_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }, f, indent=2)


# ── Bootstrap session state ───────────────────────────────────────────────────
if "labels" not in st.session_state:
    saved = load_progress()
    st.session_state.labels      = saved.get("labels", {})
    st.session_state.current_pos = saved.get("current_pos", 0)
    st.session_state.last_saved  = saved.get("saved_at", None)

source_df = load_source()
total     = len(source_df)
labels    = st.session_state.labels
labeled_n = len(labels)

# Clamp position
st.session_state.current_pos = max(0, min(st.session_state.current_pos, total - 1))
pos = st.session_state.current_pos


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏷️ SOLID Labeler")
    st.markdown("---")

    # Progress
    pct = labeled_n / total if total else 0
    st.metric("Labeled", f"{labeled_n} / {total}")
    st.progress(pct)
    st.caption(f"{pct * 100:.1f}% complete")
    if st.session_state.last_saved:
        st.caption(f"💾 Last saved: {st.session_state.last_saved}")

    st.markdown("---")

    # Jump to row
    jump = st.number_input("Jump to row #", min_value=1, max_value=total,
                           value=pos + 1, step=1)
    if st.button("Go", use_container_width=True):
        st.session_state.current_pos = int(jump) - 1
        st.rerun()

    st.markdown("---")

    # Manual save
    if st.button("💾 Save progress", use_container_width=True):
        persist(labels, pos)
        st.session_state.last_saved = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.success("Saved!")

    st.markdown("---")

    # Export
    if st.button("📥 Export labeled Excel", use_container_width=True):
        export_df = source_df.copy()
        for p in PRINCIPLES:
            c = p.lower()
            export_df[c] = [
                labels.get(str(i), {}).get(c, "") for i in range(total)
            ]
        export_df.to_excel(EXPORT_FILE, index=False)
        with open(EXPORT_FILE, "rb") as fh:
            st.download_button(
                "⬇️ Download Excel",
                data=fh,
                file_name="python-codes-labeled.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    st.markdown("---")

    # Per-principle counts
    st.markdown("**Label distribution**")
    for p in PRINCIPLES:
        c = p.lower()
        n_pass = sum(1 for v in labels.values() if v.get(c) == "Pass")
        n_viol = sum(1 for v in labels.values() if v.get(c) == "Violation")
        st.caption(f"{p}: ✅ Pass {n_pass}   ❌ Violation {n_viol}")


# ── Main: current row ─────────────────────────────────────────────────────────
row     = source_df.iloc[pos]
row_key = str(pos)
existing = labels.get(row_key, {})

# Header
st.markdown(
    f"<p class='row-counter'>"
    f"Row <strong>{pos + 1}</strong> of {total} &nbsp;·&nbsp; "
    f"ID: <code>{row.get('id','?')}</code> &nbsp;·&nbsp; "
    f"Language: <code>{row.get('language','?')}</code>"
    f"</p>",
    unsafe_allow_html=True,
)
st.markdown("---")

col_code, col_label = st.columns([3, 2], gap="large")

# ── Code panel ────────────────────────────────────────────────────────────────
with col_code:
    st.subheader("📄 Code Snippet")
    raw      = str(row.get("code", ""))
    rendered = raw.replace("\\n", "\n").replace("\\t", "\t")
    st.markdown(
        f'<div class="code-box">{htmllib.escape(rendered)}</div>',
        unsafe_allow_html=True,
    )

# ── Label panel ───────────────────────────────────────────────────────────────
with col_label:
    st.subheader("🏷️ Label this snippet")

    # Show "already labeled" notice
    if existing:
        st.info("✏️ This row already has labels — you can update them.")

    new_vals = {}
    for p in PRINCIPLES:
        c   = p.lower()
        cur = existing.get(c, "Pass")
        idx = OPTIONS.index(cur) if cur in OPTIONS else 0
        st.markdown(
            f"**{p}** &ensp;<span style='color:#888;font-size:12px'>{PRINCIPLE_HELP[p]}</span>",
            unsafe_allow_html=True,
        )
        new_vals[c] = st.radio(
            label=p,
            options=OPTIONS,
            index=idx,
            horizontal=True,
            key=f"r_{pos}_{p}",
            label_visibility="collapsed",
        )
        st.markdown("")

    st.markdown("")
    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("✅ Save & Next", type="primary", use_container_width=True):
            labels[row_key]              = new_vals
            nxt                          = min(pos + 1, total - 1)
            st.session_state.labels      = labels
            st.session_state.current_pos = nxt
            persist(labels, nxt)                           # auto-save every time
            st.session_state.last_saved  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.rerun()

    with b2:
        if st.button("💾 Save only", use_container_width=True):
            labels[row_key]         = new_vals
            st.session_state.labels = labels
            persist(labels, pos)
            st.session_state.last_saved = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.rerun()

    with b3:
        if st.button("⏭ Skip", use_container_width=True):
            st.session_state.current_pos = min(pos + 1, total - 1)
            st.rerun()


# ── Current label badge strip ─────────────────────────────────────────────────
st.markdown("---")
badge_html = "**This row:** &nbsp;"
for p in PRINCIPLES:
    val = existing.get(p.lower(), "")
    if val == "Pass":
        badge_html += f'<span class="badge-pass">{p} ✅</span>'
    elif val == "Violation":
        badge_html += f'<span class="badge-violation">{p} ❌</span>'
    else:
        badge_html += f'<span class="badge-empty">{p} —</span>'
st.markdown(badge_html, unsafe_allow_html=True)

# ── Navigation bar ────────────────────────────────────────────────────────────
st.markdown("")
nav_l, nav_mid, nav_r = st.columns([1, 4, 1])

with nav_l:
    if st.button("◀ Prev", disabled=(pos == 0), use_container_width=True):
        st.session_state.current_pos = pos - 1
        st.rerun()

with nav_mid:
    filled  = int((labeled_n / total) * 32) if total else 0
    bar_str = "█" * filled + "░" * (32 - filled)
    st.markdown(
        f"<p style='text-align:center;font-family:monospace;font-size:13px;"
        f"color:#6c757d;margin:6px 0'>{bar_str} &nbsp; {labeled_n}/{total}</p>",
        unsafe_allow_html=True,
    )

with nav_r:
    if st.button("Next ▶", disabled=(pos == total - 1), use_container_width=True):
        st.session_state.current_pos = pos + 1
        st.rerun()
