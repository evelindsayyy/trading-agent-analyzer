"""智析 · AI 股票分析助手 — Streamlit app.

Run from the repo root:  streamlit run webapp/app.py
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

from webapp import cheatsheet, cjk, config, job_manager, report_store, storage, ui  # noqa: E402

st.set_page_config(page_title="智析 · AI 股票分析助手", page_icon="📈", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(ui.CSS, unsafe_allow_html=True)
try:
    storage.init()  # ensure dirs + (when DATABASE_URL is set) the runs table
except Exception as exc:  # noqa: BLE001 — friendly message, not a stack trace
    st.error("数据库连接失败 / Database connection failed. 请检查 DATABASE_URL 是否正确。\n\n"
             f"{type(exc).__name__}: {exc}")
    st.stop()


# --------------------------------------------------------------------------- #
# Auth gate
# --------------------------------------------------------------------------- #
def check_password() -> bool:
    if not config.APP_PASSWORD or st.session_state.get("authed"):
        return True
    st.markdown(ui.brand_header(), unsafe_allow_html=True)
    st.title("欢迎使用")
    st.caption("请输入访问口令进入（向分享给你的人索取）。")
    pw = st.text_input("访问口令", type="password", label_visibility="collapsed",
                       placeholder="访问口令")
    if st.button("进入", type="primary"):
        if pw == config.APP_PASSWORD:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("口令错误，请重试。")
    st.divider()
    st.caption(config.DISCLAIMER)
    return False


if not check_password():
    st.stop()


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def page_guide() -> None:
    st.markdown(ui.guide_html(), unsafe_allow_html=True)
    st.write("")
    if st.button("我知道了，去发起第一次分析 →", type="primary"):
        st.session_state["goto_new"] = True
        st.rerun()


def page_new_analysis() -> None:
    st.markdown("<h1 style='font-family:\"Noto Serif SC\",serif;'>新建分析</h1>",
                unsafe_allow_html=True)
    st.caption("输入股票代码 → 点「开始分析」。分析需要几分钟，提交后到「分析记录」看进度。")

    c1, c2, c3 = st.columns([1.3, 1, 1])
    with c1:
        ticker = st.text_input("股票代码", value="NVDA",
                               help="美股代码，如 NVDA、AAPL、TSLA").strip().upper()
        st.markdown(
            '<div style="font-size:12px;color:#9A958B;margin-top:-6px;">试试 '
            '<span class="mono" style="color:#1C6E66;background:#E6F0EE;padding:2px 8px;border-radius:6px;">NVDA</span> '
            '<span class="mono" style="background:#EEEAE0;padding:2px 8px;border-radius:6px;">AAPL</span> '
            '<span class="mono" style="background:#EEEAE0;padding:2px 8px;border-radius:6px;">TSLA</span></div>',
            unsafe_allow_html=True)
    with c2:
        trade_date = st.date_input("分析日期", value=date.today(),
                                   help="一般选今天即可")
    with c3:
        lang_labels = list(config.REPORT_LANGUAGES.keys())
        report_lang_label = st.selectbox("报告语言", lang_labels, index=0,
                                         help="生成的报告用哪种语言书写")
        output_language = config.REPORT_LANGUAGES[report_lang_label]

    selected = []
    items = list(config.ANALYST_CHOICES.items())
    st.write("")
    cols = st.columns(2)
    for i, (key, label) in enumerate(items):
        with cols[i % 2], st.container(border=True):
            if st.checkbox(label, value=True, key=f"an_{key}"):
                selected.append(key)
    st.markdown(
        f'<div style="font-size:13px;color:#1C6E66;font-weight:600;margin:2px 0 4px;">'
        f'已选 {len(selected)} / 4 位分析师</div>'
        '<div style="font-size:12.5px;color:#9A958B;">默认四位全选最全面；取消其中几位可更快。</div>',
        unsafe_allow_html=True)

    with st.expander("⚙️ 高级设置 · 辩论深度（可不动）"):
        debate_rounds = st.slider("研究辩论轮数", 1, 3, 1,
                                  help="多头/空头来回的轮数，越多越深入，也越慢越贵")
        risk_rounds = st.slider("风险讨论轮数", 1, 3, 1,
                                help="风险评估的来回轮数，越多越深入")

    st.write("")
    if st.button("▶ 开始分析", type="primary", disabled=not (ticker and selected)):
        job_id = job_manager.manager.start_run(
            ticker=ticker, date=trade_date.strftime("%Y-%m-%d"),
            analysts=selected, debate_rounds=debate_rounds,
            risk_rounds=risk_rounds, output_language=output_language)
        st.success(f"✅ 已提交：{ticker} —— 请去左侧「分析记录」查看进度。")
        st.balloons()
        st.session_state["last_job"] = job_id


def _render_runs_list() -> None:
    jobs = job_manager.list_jobs()
    if not jobs:
        st.info("还没有分析记录。请去左侧「新建分析」发起第一个。")
        return
    for j in jobs:
        analysts_zh = " · ".join(config.ANALYST_SHORT_ZH.get(a, a) for a in j["analysts"])
        rating = config.RATING_ZH.get(j.get("signal"), j.get("signal")) if j.get("signal") else None
        is_buy = j.get("signal") in ("Buy", "Overweight")
        st.markdown(ui.run_card_html(j["ticker"], j["date"], j["status"],
                                     analysts_zh, rating, is_buy),
                    unsafe_allow_html=True)
        if j["status"] == "failed" and j.get("error"):
            with st.expander("错误详情"):
                st.code(j["error"])
        if (j["status"] == "done" and j.get("report_dir")
                and st.button("查看报告 →", key=f"view_{j['id']}")):
            st.session_state["selected_run"] = j["report_dir"]
            st.session_state["goto_report"] = True
            st.rerun()
    if not job_manager.has_active_jobs() and st.session_state.get("_runs_refreshing"):
        st.session_state["_runs_refreshing"] = False
        st.rerun()


def page_runs() -> None:
    st.markdown("<h1 style='font-family:\"Noto Serif SC\",serif;'>分析记录</h1>",
                unsafe_allow_html=True)
    st.caption("分析需要几分钟，运行中的会自动刷新。状态变成「完成」就能查看报告。")
    active = job_manager.has_active_jobs()
    st.session_state["_runs_refreshing"] = active
    st.fragment(run_every=3 if active else None)(_render_runs_list)()


def _run_label(run: report_store.Run) -> str:
    s = run.timestamp
    pretty = f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[9:11]}:{s[11:13]}" if len(s) >= 13 else s
    return f"{run.ticker} · {pretty}"


def page_report() -> None:
    st.markdown("<h1 style='font-family:\"Noto Serif SC\",serif;'>报告 &amp; 速查表</h1>",
                unsafe_allow_html=True)
    runs = report_store.list_runs()
    if not runs:
        st.info("还没有完成的报告。请先去「新建分析」发起一次分析。")
        return

    names = [r.name for r in runs]
    name_labels = {r.name: _run_label(r) for r in runs}
    default_idx = 0
    if st.session_state.get("selected_run") in names:
        default_idx = names.index(st.session_state["selected_run"])
    chosen = st.selectbox("选择一份报告", names, index=default_idx,
                          format_func=lambda n: name_labels.get(n, n))
    run = report_store.get_run(chosen)
    if run is None:
        st.error("找不到该报告。")
        return

    rating = config.RATING_ZH.get(run.signal, run.signal) if run.signal else None
    is_buy = run.signal in ("Buy", "Overweight")
    st.markdown(ui.summary_card_html(run.ticker, _run_label(run).split("· ")[-1],
                                     rating, is_buy), unsafe_allow_html=True)

    # A still-running run streams its analyst sections in as they finish — poll
    # every few seconds so they appear without a manual refresh, and flip to the
    # full report + cheatsheet view once the pipeline completes.
    if not run.is_done:
        st.info("⏳ 分析进行中，各章节会陆续出现。完整报告与速查表将在完成后就绪。")

        @st.fragment(run_every=4)
        def _live_sections() -> None:
            fresh = report_store.get_run(run.name)
            if fresh is not None and fresh.is_done:
                st.rerun()  # full rerun → render the finished report + cheatsheet
                return
            _render_sections(run)

        _live_sections()
        return

    tab_report, tab_cheat = st.tabs(["完整报告", "新手速查表 · 推荐"])
    with tab_report:
        _render_sections(run)
    with tab_cheat:
        _cheatsheet_ui(run)


def _render_sections(run: report_store.Run) -> None:
    sections = report_store.available_sections(run)
    if not sections:
        st.info("该报告暂无可显示的章节。" if run.is_done else "正在生成第一批章节…")
        return
    labels = [label for _, label, _ in sections]
    picked = st.radio("章节", labels, horizontal=True, label_visibility="collapsed")
    for _, label, content in sections:
        if label == picked:
            st.markdown(cjk.clean_markdown(content))


def _cheatsheet_ui(run: report_store.Run) -> None:
    c1, c2, c3 = st.columns([1, 1, 1])
    lang_label = c1.radio("语言", ["中文", "English"], horizontal=True)
    lang = "zh" if lang_label == "中文" else "en"
    shares = c2.text_input("持仓股数（可选）", value="", placeholder="如 80；空仓填 0")
    cost = c3.text_input("成本价（可选）", value="", placeholder="如 $610")

    existing = report_store.existing_cheatsheet(run, lang)
    btn_label = "重新生成速查表" if existing else "生成速查表"
    if st.button(f"🎯 {btn_label}", type="primary"):
        try:
            # Stream tokens straight into the page instead of blocking on a
            # spinner; st.write_stream returns the full text once complete.
            md = st.write_stream(
                cheatsheet.stream(run, lang=lang, shares=shares, cost=cost))
        except Exception as exc:  # noqa: BLE001
            st.error(f"生成失败：{exc}")
            return
        storage.save_cheatsheet(run.name, lang, (md or "").strip())
        st.session_state[f"cheat_{run.name}_{lang}"] = md
        # Rerun so the polished, CJK-cleaned cached copy replaces the raw stream.
        st.rerun()

    md = st.session_state.get(f"cheat_{run.name}_{lang}") or existing
    if md:
        st.markdown(cjk.clean_markdown(md))
        fname = "beginner_cheatsheet_zh.md" if lang == "zh" else "beginner_cheatsheet.md"
        st.download_button("⬇️ 下载 Markdown", md, file_name=fname)
    else:
        st.caption("点上面的按钮生成。持仓留空＝按「未提供」处理；填 0＝空仓视角。")


# --------------------------------------------------------------------------- #
# Sidebar nav + router
# --------------------------------------------------------------------------- #
NAV = {"① 上手指南": "guide", "② 新建分析": "new",
       "③ 分析记录": "runs", "④ 报告 & 速查表": "report"}
_LABEL_FOR = {v: k for k, v in NAV.items()}

# Pending programmatic navigation (set the radio value before it's created).
if st.session_state.pop("goto_report", False):
    st.session_state["nav"] = _LABEL_FOR["report"]
elif st.session_state.pop("goto_new", False):
    st.session_state["nav"] = _LABEL_FOR["new"]

st.sidebar.markdown(ui.brand_header(), unsafe_allow_html=True)
nav = st.sidebar.radio("导航", list(NAV), key="nav", label_visibility="collapsed")
_usage_mb = storage.data_bytes() / 1024 / 1024 if storage.db_enabled() else None
st.sidebar.markdown(
    ui.storage_pill(storage.db_enabled(), _usage_mb, config.DB_SOFT_LIMIT_MB),
    unsafe_allow_html=True)
page = NAV[nav]

if page == "guide":
    page_guide()
elif page == "new":
    page_new_analysis()
elif page == "runs":
    page_runs()
else:
    page_report()

# Footer disclaimer on every page.
st.divider()
st.caption(config.DISCLAIMER)
