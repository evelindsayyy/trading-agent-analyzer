"""TradingAgents web app (Streamlit).

Run from the repo root:  streamlit run webapp/app.py

Lets you (and a few friends) generate analyses, browse reports, and produce the
beginner cheatsheet — all without the terminal.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# Make `webapp` importable when launched via `streamlit run webapp/app.py`.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import streamlit as st  # noqa: E402

from webapp import cheatsheet, config, job_manager, report_store  # noqa: E402

st.set_page_config(page_title="TradingAgents", page_icon="📈", layout="wide")
config.ensure_dirs()


# --------------------------------------------------------------------------- #
# Auth gate (simple shared password for an internal deployment)
# --------------------------------------------------------------------------- #
def check_password() -> bool:
    if not config.APP_PASSWORD:
        return True  # open mode (localhost-only use)
    if st.session_state.get("authed"):
        return True
    st.title("🔒 TradingAgents")
    pw = st.text_input("访问口令", type="password")
    if st.button("进入"):
        if pw == config.APP_PASSWORD:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("口令错误")
    return False


if not check_password():
    st.stop()


# --------------------------------------------------------------------------- #
# Sidebar navigation
# --------------------------------------------------------------------------- #
PAGES = ["🚀 新建分析", "📋 运行记录", "📄 报告 & 速查表"]
page = st.sidebar.radio("导航", PAGES)
st.sidebar.caption(f"报告目录：{config.REPORTS_ROOT}")


# --------------------------------------------------------------------------- #
# Page: New analysis
# --------------------------------------------------------------------------- #
def page_new_analysis() -> None:
    st.header("🚀 新建分析")
    st.caption("一次完整分析需要数分钟、会调用很多次 LLM。提交后在「运行记录」里看进度。")

    col1, col2 = st.columns(2)
    with col1:
        ticker = st.text_input("股票代码", value="NVDA").strip().upper()
    with col2:
        trade_date = st.date_input("分析日期", value=date.today())

    st.subheader("分析师团队")
    selected = []
    cols = st.columns(len(config.ANALYST_CHOICES))
    for (key, label), c in zip(config.ANALYST_CHOICES.items(), cols, strict=True):
        if c.checkbox(label, value=True, key=f"an_{key}"):
            selected.append(key)

    with st.expander("高级设置（辩论深度）"):
        debate_rounds = st.slider("研究辩论轮数", 1, 3, 1,
                                  help="多头/空头来回的轮数，越多越深也越贵")
        risk_rounds = st.slider("风险讨论轮数", 1, 3, 1)

    if st.button("▶️ 开始分析", type="primary", disabled=not (ticker and selected)):
        job_id = job_manager.manager.start_run(
            ticker=ticker,
            date=trade_date.strftime("%Y-%m-%d"),
            analysts=selected,
            debate_rounds=debate_rounds,
            risk_rounds=risk_rounds,
        )
        st.success(f"已提交：{job_id} —— 去「运行记录」看进度。")
        st.session_state["last_job"] = job_id


# --------------------------------------------------------------------------- #
# Page: Run records
# --------------------------------------------------------------------------- #
_STATUS_BADGE = {
    "queued": "🕒 排队中", "running": "⏳ 运行中",
    "done": "✅ 完成", "failed": "❌ 失败",
}


def _render_runs_list() -> None:
    """Render the job cards. Re-run on its own (as a fragment) so only this list
    refreshes — no whole-page rerun, no flicker/dimming."""
    jobs = job_manager.list_jobs()
    if not jobs:
        st.info("还没有运行记录。去「新建分析」提交第一个。")
        return

    for j in jobs:
        badge = _STATUS_BADGE.get(j["status"], j["status"])
        with st.container(border=True):
            top = st.columns([2, 1, 2, 1])
            top[0].markdown(f"**{j['ticker']}** · {j['date']}")
            top[1].markdown(badge)
            top[2].caption(f"分析师：{', '.join(j['analysts'])}")
            if j["status"] == "done" and j.get("signal"):
                top[3].markdown(f"**{j['signal']}**")

            if j["status"] == "running":
                st.caption(f"开始于 {j['started_at']}")
            if j["status"] == "failed" and j.get("error"):
                with st.expander("错误详情"):
                    st.code(j["error"])
            if (j["status"] == "done" and j.get("report_dir")
                    and st.button("查看报告 →", key=f"view_{j['id']}")):
                st.session_state["selected_run"] = j["report_dir"]
                st.session_state["goto_report"] = True
                st.rerun()  # full rerun to switch pages

    # Once every job has finished, settle: a one-shot full rerun drops the
    # fragment's run_every timer (set to None on the next render) so we stop
    # polling. The session flag prevents this from looping when already idle.
    if not job_manager.has_active_jobs() and st.session_state.get("_runs_refreshing"):
        st.session_state["_runs_refreshing"] = False
        st.rerun()


def page_runs() -> None:
    st.header("📋 运行记录")
    active = job_manager.has_active_jobs()
    st.session_state["_runs_refreshing"] = active
    # Only attach the 3s timer while something is running; idle = render once.
    st.fragment(run_every=3 if active else None)(_render_runs_list)()


# --------------------------------------------------------------------------- #
# Page: Report viewer + cheatsheet
# --------------------------------------------------------------------------- #
def page_report() -> None:
    st.header("📄 报告 & 速查表")
    runs = report_store.list_runs()
    if not runs:
        st.info("还没有完成的报告。")
        return

    names = [r.name for r in runs]
    default_idx = 0
    if st.session_state.get("selected_run") in names:
        default_idx = names.index(st.session_state["selected_run"])
    chosen = st.selectbox("选择一份报告", names, index=default_idx)
    run = report_store.get_run(chosen)
    if run is None:
        st.error("找不到该报告。")
        return

    tab_report, tab_cheat = st.tabs(["📑 完整报告", "🎯 新手速查表"])

    with tab_report:
        sections = report_store.available_sections(run)
        labels = [label for _, label, _ in sections]
        picked = st.radio("章节", labels, horizontal=True)
        for _, label, content in sections:
            if label == picked:
                st.markdown(content)

    with tab_cheat:
        _cheatsheet_ui(run)


def _cheatsheet_ui(run: report_store.Run) -> None:
    c1, c2, c3 = st.columns([1, 1, 1])
    lang_label = c1.radio("语言", ["中文", "English"], horizontal=True)
    lang = "zh" if lang_label == "中文" else "en"
    shares = c2.text_input("持仓股数（可选）", value="", placeholder="如 80；空仓填 0")
    cost = c3.text_input("成本价（可选）", value="", placeholder="如 $610")

    existing = report_store.existing_cheatsheet(run, lang)
    btn_label = "重新生成速查表" if existing else "生成速查表"
    if st.button(f"🎯 {btn_label}", type="primary"):
        with st.spinner("正在生成速查表…"):
            try:
                md = cheatsheet.generate(run, lang=lang, shares=shares, cost=cost)
                st.session_state[f"cheat_{run.name}_{lang}"] = md
            except Exception as exc:  # noqa: BLE001
                st.error(f"生成失败：{exc}")
                return

    md = st.session_state.get(f"cheat_{run.name}_{lang}") or existing
    if md:
        st.markdown(md)
        fname = "beginner_cheatsheet_zh.md" if lang == "zh" else "beginner_cheatsheet.md"
        st.download_button("⬇️ 下载 Markdown", md, file_name=fname)
    else:
        st.caption("点上面的按钮生成。持仓留空＝按「未提供」处理；填 0＝空仓视角。")


# --------------------------------------------------------------------------- #
# Router
# --------------------------------------------------------------------------- #
if st.session_state.pop("goto_report", False):
    page = "📄 报告 & 速查表"

if page == "🚀 新建分析":
    page_new_analysis()
elif page == "📋 运行记录":
    page_runs()
else:
    page_report()
