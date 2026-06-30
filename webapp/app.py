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

from webapp import cheatsheet, config, job_manager, report_store, storage  # noqa: E402

st.set_page_config(page_title="AI 股票分析助手", page_icon="📈", layout="wide")
try:
    storage.init()  # ensure dirs + (when DATABASE_URL is set) the runs table
except Exception as exc:  # noqa: BLE001 — show a friendly message, not a stack trace
    st.error(
        "数据库连接失败 / Database connection failed. 请检查 DATABASE_URL 是否正确。\n\n"
        f"{type(exc).__name__}: {exc}"
    )
    st.stop()


# --------------------------------------------------------------------------- #
# Auth gate (simple shared password for an internal deployment)
# --------------------------------------------------------------------------- #
def check_password() -> bool:
    if not config.APP_PASSWORD:
        return True  # open mode (localhost-only use)
    if st.session_state.get("authed"):
        return True
    st.title("🔒 AI 股票分析助手")
    st.caption("请输入访问口令进入（向分享给你的人索取）。")
    pw = st.text_input("访问口令", type="password")
    if st.button("进入"):
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
# Sidebar navigation
# --------------------------------------------------------------------------- #
st.sidebar.title("📈 AI 股票分析助手")
PAGES = ["❓ 使用帮助", "🚀 新建分析", "📋 运行记录", "📄 报告 & 速查表"]
page = st.sidebar.radio("导航", PAGES)
if storage.db_enabled():
    st.sidebar.caption("💾 运行记录已永久保存")
else:
    st.sidebar.caption("⚠️ 临时存储：应用重启后记录会丢失")


# --------------------------------------------------------------------------- #
# Page: Help / instruction manual
# --------------------------------------------------------------------------- #
def page_help() -> None:
    st.header("❓ 使用帮助")
    st.markdown(
        """
### 这个工具是做什么的？
它是一个 **AI 股票分析助手**。你给它一个股票代码，它会自动派出多个 AI「分析师」
（看**技术面、消息面、基本面、市场情绪**），让「多头」和「空头」互相辩论，再做风险
评估，最后给出一个明确的结论（**买入 / 卖出 / 持有 / 加仓 / 减仓**），还能把复杂报告
变成新手也能看懂的「**速查表**」。

### 三步上手
**第 1 步 · 发起分析** — 左侧点「🚀 新建分析」，输入股票代码（例如美股 `NVDA`、
`AAPL`、`TSLA`），选好日期，点「开始分析」。

**第 2 步 · 等待结果** — 点「📋 运行记录」看进度。分析需要**几分钟**（AI 要查很多
资料并辩论），页面会自动刷新，状态变成 ✅ **完成** 就好了。

**第 3 步 · 看结果** — 点「📄 报告 & 速查表」，选中你的那条记录：
- **完整报告**：分章节的详细分析（技术面、情绪面、多空辩论、最终决策等）。
- **新手速查表**：一页纸的大白话总结，直接告诉你「**结论是什么、关键价位、分几步
  怎么做**」。可切换中文 / English；填上你的持仓还能算「卖 / 买多少股」。

### 常见名词
| 词 | 意思 |
|---|---|
| **评级** | AI 的总结论：买入 / 加仓(看好) / 持有 / 减仓(看淡) / 卖出 |
| **速查表** | 把专业报告翻译成新手能照做的「该怎么办」 |
| **持仓股数** | 你现在手里有多少股；填 `0` 表示空仓（还没买） |
| **止损** | 跌到某个价就卖出，用来控制亏损 |

### ⚠️ 重要提醒（请务必阅读）
- 本工具**仅供学习和参考，不构成任何投资建议**。AI 会犯错，所有盈亏由你自己负责。
- 每次分析会消耗一点 API 费用、耗时几分钟，请**不要重复狂点**。
- 报告是**分析当天的快照**，市场价格随时会变，过几天就可能过时。
"""
    )
    if st.button("🚀 我知道了，去发起第一次分析", type="primary"):
        st.session_state["goto_new"] = True
        st.rerun()


# --------------------------------------------------------------------------- #
# Page: New analysis
# --------------------------------------------------------------------------- #
def page_new_analysis() -> None:
    st.header("🚀 新建分析")
    st.caption("输入股票代码 → 点「开始分析」。分析需要几分钟，提交后在「📋 运行记录」里看进度。"
               "第一次使用建议先看左侧「❓ 使用帮助」。")

    col1, col2 = st.columns(2)
    with col1:
        ticker = st.text_input("股票代码", value="NVDA",
                               help="美股代码，如 NVDA、AAPL、TSLA").strip().upper()
    with col2:
        trade_date = st.date_input("分析日期", value=date.today(),
                                   help="分析截至的日期，一般选今天")

    st.subheader("分析师团队")
    st.caption("默认四位全选即可（最全面）。想更快可取消其中几位。")
    selected = []
    cols = st.columns(len(config.ANALYST_CHOICES))
    for (key, label), c in zip(config.ANALYST_CHOICES.items(), cols, strict=True):
        if c.checkbox(label, value=True, key=f"an_{key}"):
            selected.append(key)

    with st.expander("⚙️ 高级设置（辩论深度，可不动）"):
        debate_rounds = st.slider("研究辩论轮数", 1, 3, 1,
                                  help="多头/空头来回的轮数，越多越深入，也越慢越贵")
        risk_rounds = st.slider("风险讨论轮数", 1, 3, 1,
                                help="风险评估的来回轮数，越多越深入")

    if st.button("▶️ 开始分析", type="primary", disabled=not (ticker and selected)):
        job_id = job_manager.manager.start_run(
            ticker=ticker,
            date=trade_date.strftime("%Y-%m-%d"),
            analysts=selected,
            debate_rounds=debate_rounds,
            risk_rounds=risk_rounds,
        )
        st.success(f"✅ 已提交：{ticker} —— 请去左侧「📋 运行记录」查看进度。")
        st.balloons()
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
        analysts_zh = "、".join(
            config.ANALYST_SHORT_ZH.get(a, a) for a in j["analysts"])
        with st.container(border=True):
            top = st.columns([2, 1, 2, 1])
            top[0].markdown(f"**{j['ticker']}** · {j['date']}")
            top[1].markdown(badge)
            top[2].caption(f"分析师：{analysts_zh}")
            if j["status"] == "done" and j.get("signal"):
                rating = config.RATING_ZH.get(j["signal"], j["signal"])
                top[3].markdown(f"**{rating}**")

            if j["status"] == "running":
                st.caption(f"开始于 {j['started_at']}　·　分析需要几分钟，请耐心等待")
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
def _run_label(run: report_store.Run) -> str:
    """Readable option label, e.g. 'NVDA · 2026-06-30 14:07'."""
    s = run.timestamp
    # s is YYYYMMDD_HHMMSS → 'YYYY-MM-DD HH:MM'
    pretty = f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[9:11]}:{s[11:13]}" if len(s) >= 13 else s
    return f"{run.ticker} · {pretty}"


def page_report() -> None:
    st.header("📄 报告 & 速查表")
    runs = report_store.list_runs()
    if not runs:
        st.info("还没有完成的报告。请先去左侧「🚀 新建分析」发起一次分析，"
                "完成后回到这里查看。")
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

    tab_report, tab_cheat = st.tabs(["📑 完整报告", "🎯 新手速查表（推荐新手先看）"])

    with tab_report:
        st.caption("AI 分析师团队的详细报告，按章节查看。看不懂可切到「新手速查表」。")
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
elif st.session_state.pop("goto_new", False):
    page = "🚀 新建分析"

if page == "❓ 使用帮助":
    page_help()
elif page == "🚀 新建分析":
    page_new_analysis()
elif page == "📋 运行记录":
    page_runs()
else:
    page_report()

# Footer disclaimer — shown at the bottom of every page.
st.divider()
st.caption(config.DISCLAIMER)
