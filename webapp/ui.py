"""Visual layer for the 智析 design: global CSS + HTML render helpers.

Streamlit can't fully reproduce a custom HTML design, so we (1) theme the
widgets via CSS and (2) render the presentational parts (brand, cards, guide,
summary) as HTML, keeping Streamlit widgets for the interactive bits.
"""
from __future__ import annotations

# Design palette
TEAL = "#1C6E66"
TEAL_DARK = "#155049"
TEAL_SOFT_BG = "#E6F0EE"
TEAL_SOFT_BORDER = "#CFE2DD"
CREAM = "#FBFAF6"
SIDEBAR = "#F4F2EA"
BORDER = "#E6E2D8"
INK = "#23211C"
MUTED = "#7C7869"
FAINT = "#9A958B"
SELL = "#B4533B"
AMBER = "#B57A2E"
BUY = "#2E7D5B"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700&family=Noto+Serif+SC:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

/* base — Noto SC first, then a robust CJK fallback stack (so Chinese still
   renders cleanly if Google Fonts fails to load) */
html, body, .stApp, [data-testid="stAppViewContainer"],
.stMarkdown, [data-testid="stMarkdownContainer"], button, input, textarea, select {
  font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, "Segoe UI",
    "PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", "Noto Sans CJK SC",
    "Source Han Sans SC", sans-serif;
  color: #23211C;
}
.stMarkdown p, .stMarkdown li, [data-testid="stMarkdownContainer"] p { line-height: 1.75; }
.stApp { background: #FBFAF6; }
.block-container { max-width: 860px; padding-top: 2.6rem; padding-bottom: 4rem; }

/* hide Streamlit chrome for a cleaner branded look */
[data-testid="stToolbar"], #MainMenu, header[data-testid="stHeader"], footer { visibility: hidden; height: 0; }

/* headings → serif */
h1, h2, h3, [data-testid="stHeading"] h1, [data-testid="stHeading"] h2, [data-testid="stHeading"] h3 {
  font-family: 'Noto Serif SC', "Songti SC", "Noto Serif CJK SC", serif !important;
  color: #23211C; letter-spacing: .01em;
}

/* monospace for code & tickers */
code, kbd, pre, .mono { font-family: 'IBM Plex Mono', monospace !important; }

/* sidebar */
[data-testid="stSidebar"] { background: #F4F2EA; border-right: 1px solid #E6E2D8; }
[data-testid="stSidebar"] .block-container { padding-top: 1.4rem; }
/* Keep the "reopen sidebar" control reachable — and obvious — after collapse.
   We hide the whole header above (visibility:hidden), and on Streamlit >=1.5x the
   reopen button (stExpandSidebarButton) lives INSIDE that header, so the hidden
   state cascades to it and there is no way to reopen the sidebar. Force it (and
   the older stSidebarCollapsedControl) visible, and render a clear white pill so
   it isn't the faint low-contrast default glyph. Both testids are covered so the
   fix holds across Streamlit versions. */
[data-testid="stExpandSidebarButton"],
[data-testid="stExpandSidebarButton"] *,
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"] * {
  visibility: visible !important; opacity: 1 !important;
}
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapsedControl"] button {
  display: flex !important; align-items: center !important; justify-content: center !important;
  background: #FFFFFF !important; border: 1px solid #E6E2D8 !important;
  border-radius: 9px !important; color: #1C6E66 !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, .10) !important;
  width: 38px !important; height: 38px !important;
}
[data-testid="stExpandSidebarButton"]:hover,
[data-testid="stSidebarCollapsedControl"] button:hover {
  background: #E6F0EE !important; border-color: #1C6E66 !important;
}
[data-testid="stExpandSidebarButton"] svg,
[data-testid="stSidebarCollapsedControl"] svg {
  color: #1C6E66 !important; fill: #1C6E66 !important;
  width: 20px !important; height: 20px !important;
}

/* sidebar radio → nav pills */
[data-testid="stSidebar"] div[role="radiogroup"] { gap: 4px; display: flex; flex-direction: column; }
[data-testid="stSidebar"] div[role="radiogroup"] label {
  border: 1px solid transparent; border-radius: 11px; padding: 9px 12px; margin: 0;
  cursor: pointer; transition: background .12s, border-color .12s;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:hover { background: #ECE9DF; }
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
  background: #E6F0EE; border-color: #CFE2DD;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p { color: #155049; font-weight: 600; }
[data-testid="stSidebar"] div[role="radiogroup"] input { display: none; }
[data-testid="stSidebar"] div[role="radiogroup"] p { font-size: 14px; }

/* buttons */
.stButton > button {
  border-radius: 11px; font-weight: 600; font-family: 'Noto Sans SC', sans-serif;
  border: 1px solid #D9D4C6; background: #fff; color: #3A372F; padding: .5rem 1.1rem;
  transition: background .12s, border-color .12s;
}
.stButton > button:hover { border-color: #1C6E66; color: #155049; }
.stButton > button[kind="primary"] { background: #1C6E66; border: none; color: #fff; }
.stButton > button[kind="primary"]:hover { background: #175a53; color: #fff; }
.stDownloadButton > button { border-radius: 10px; }

/* inputs */
.stTextInput input, .stDateInput input, [data-baseweb="select"] > div, .stSelectbox > div > div {
  border-radius: 11px !important; border-color: #D9D4C6 !important; background: #fff !important;
}
.stTextInput input { font-family: 'IBM Plex Mono', monospace; font-size: 16px; }

/* section-chip radio (horizontal) */
div[role="radiogroup"][aria-orientation="horizontal"] { gap: 8px; flex-wrap: wrap; }
div[role="radiogroup"][aria-orientation="horizontal"] label {
  border: 1px solid #DCD7C9; border-radius: 20px; padding: 5px 14px; background: #fff; margin: 0;
}
div[role="radiogroup"][aria-orientation="horizontal"] label:has(input:checked) {
  background: #1C6E66; border-color: #1C6E66;
}
div[role="radiogroup"][aria-orientation="horizontal"] label:has(input:checked) p { color: #fff; font-weight: 600; }
div[role="radiogroup"][aria-orientation="horizontal"] input { display: none; }

/* tabs */
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid #E6E2D8; }
.stTabs [data-baseweb="tab"] { font-family: 'Noto Sans SC', sans-serif; font-weight: 500; }
.stTabs [aria-selected="true"] { color: #1C6E66 !important; font-weight: 600; }

/* bordered containers → cards */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px !important; border-color: #E6E2D8 !important; background: #fff; }

/* misc */
hr { border-color: #E6E2D8; }
a { color: #1C6E66; }
</style>
"""


def brand_header() -> str:
    return f"""
<div style="display:flex;align-items:center;gap:11px;padding:2px 4px 16px;">
  <div style="width:34px;height:34px;border-radius:9px;background:{TEAL};display:flex;align-items:center;justify-content:center;">
    <div style="width:13px;height:13px;background:#fff;transform:rotate(45deg);border-radius:2px;"></div>
  </div>
  <div style="display:flex;flex-direction:column;line-height:1.15;">
    <span style="font-family:'Noto Serif SC',serif;font-size:17px;font-weight:600;color:{INK};">智析</span>
    <span style="font-size:10.5px;color:{FAINT};letter-spacing:.03em;">AI 股票分析助手</span>
  </div>
</div>
"""


def storage_pill(saved: bool, usage_mb: float | None = None,
                 cap_mb: int | None = None) -> str:
    if saved:
        dot, text, bg = BUY, "运行记录已永久保存", "#EEEAE0"
    else:
        dot, text, bg = AMBER, "临时存储 · 重启会丢失", "#F6EEDD"
    sub = ""
    if saved and usage_mb is not None and cap_mb:
        sub = (f'<div style="font-size:10px;color:#9A958B;margin:4px 0 0 15px;">'
               f'已用 {usage_mb:.1f} / {cap_mb} MB · 满了自动清理最旧的记录</div>')
    return (f'<div style="padding:10px 12px;border-radius:11px;background:{bg};margin-top:14px;">'
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<span style="width:7px;height:7px;border-radius:50%;background:{dot};"></span>'
            f'<span style="font-size:11px;color:#6B675D;">{text}</span></div>{sub}</div>')


def eyebrow(text: str) -> str:
    return (f'<div style="font-family:\'IBM Plex Mono\',monospace;font-size:11px;'
            f'letter-spacing:.18em;color:{TEAL};margin-bottom:8px;">{text}</div>')


def guide_html() -> str:
    step = ('<div style="border:1px solid {b};border-radius:14px;padding:20px;background:#fff;">'
            '<div style="font-family:\'Noto Serif SC\',serif;font-size:27px;color:{t};margin-bottom:10px;">{n}</div>'
            '<div style="font-size:15px;font-weight:600;margin-bottom:7px;">{title}</div>'
            '<div style="font-size:13px;line-height:1.7;color:{m};">{body}</div></div>')
    steps = "".join(step.format(b=BORDER, t=TEAL, m=MUTED, n=n, title=ti, body=bo) for n, ti, bo in [
        ("01", "发起分析", "输入股票代码、选好分析师，点「开始分析」。"),
        ("02", "等待几分钟", "AI 查资料、互相辩论，记录页会自动刷新进度。"),
        ("03", "看结论", "打开完整报告，或先看一页「新手速查表」。"),
    ])
    term = ('<div style="border-left:3px solid {t};padding:5px 0 5px 14px;">'
            '<div style="font-size:14px;font-weight:600;">{k}</div>'
            '<div style="font-size:12.5px;color:{m};line-height:1.65;margin-top:2px;">{v}</div></div>')
    terms = "".join(term.format(t=TEAL, m=MUTED, k=k, v=v) for k, v in [
        ("评级", "AI 的总结论：买入 / 加仓 / 持有 / 减仓 / 卖出。"),
        ("速查表", "把专业报告翻成新手能照做的「该怎么办」。"),
        ("持仓股数", "你现在手里有多少股；填 0 表示还没买。"),
        ("止损", "跌到某个价就卖出，用来控制亏损。"),
    ])
    return f"""
{eyebrow("GETTING STARTED")}
<h1 style="font-family:'Noto Serif SC',serif;font-size:33px;font-weight:600;margin:0 0 12px;">三步，看懂一只股票</h1>
<p style="font-size:15.5px;line-height:1.8;color:#615E55;max-width:660px;margin:0 0 30px;">
给它一个股票代码，AI 分析师团队会从技术面、消息面、基本面、情绪面分头研究，再让多空双方辩论，
最后给你一个明确结论，外加一页新手也能照做的「速查表」。</p>
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:36px;">{steps}</div>
<h2 style="font-family:'Noto Serif SC',serif;font-size:19px;font-weight:600;margin:0 0 5px;">常见名词，先认个脸熟</h2>
<p style="font-size:13px;color:{FAINT};margin:0 0 16px;">看到不懂的词，这里都有一句话的大白话解释。</p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:30px;">{terms}</div>
<div style="display:flex;gap:12px;align-items:flex-start;background:#FBF5EA;border:1px solid #ECDFC6;border-radius:12px;padding:16px 18px;">
  <span style="font-size:16px;line-height:1;">⚠️</span>
  <p style="font-size:13px;line-height:1.75;color:#7A6A44;margin:0;">仅供学习参考，<b>不构成投资建议</b>。AI 会犯错，盈亏自负。报告是分析当天的快照，行情随时会变。</p>
</div>
"""


_STATUS_STYLE = {
    "done": (BUY, "#E5F1EA", "●", "完成"),
    "running": (AMBER, "#FBF1DF", "◐", "运行中"),
    "queued": (FAINT, "#EEEAE0", "○", "排队中"),
    "failed": (SELL, "#F7E9E4", "✕", "失败"),
}


def run_card_html(ticker: str, date: str, status: str, analysts: str,
                  rating: str | None, is_buy: bool) -> str:
    color, bg, dot, label = _STATUS_STYLE.get(status, (FAINT, "#EEEAE0", "○", status))
    pill = (f'<span style="font-size:12px;font-weight:600;color:{color};background:{bg};'
            f'padding:3px 11px;border-radius:20px;">{dot} {label}</span>')
    head = (f'<div style="display:flex;align-items:center;gap:14px;">'
            f'<span class="mono" style="font-size:19px;font-weight:600;color:{INK};">{ticker}</span>{pill}'
            f'<span class="mono" style="font-size:12.5px;color:{FAINT};margin-left:auto;">{date}</span></div>'
            f'<div style="font-size:12px;color:{FAINT};margin-top:9px;">分析师：{analysts}</div>')
    body = ""
    if status == "done" and rating:
        rcolor = BUY if is_buy else SELL
        body = (f'<div style="margin-top:13px;padding-top:13px;border-top:1px solid #F0ECE2;font-size:13.5px;">'
                f'结论评级：<b style="color:{rcolor};">{rating}</b></div>')
    elif status == "running":
        body = ('<div style="margin-top:12px;height:4px;border-radius:4px;background:#F0ECE2;overflow:hidden;">'
                f'<div style="width:58%;height:100%;background:{AMBER};"></div></div>'
                f'<div style="margin-top:8px;font-size:12px;color:{AMBER};">分析进行中，约几分钟，页面会自动刷新…</div>')
    return (f'<div style="border:1px solid {BORDER};border-radius:14px;padding:18px 20px;'
            f'background:#fff;margin-bottom:14px;">{head}{body}</div>')


def summary_card_html(ticker: str, date: str, rating: str | None, is_buy: bool) -> str:
    accent = BUY if is_buy else SELL
    bg = "#F1F7F3" if is_buy else "#FBF6EE"
    rating_html = ""
    if rating:
        rating_html = (f'<div style="display:flex;align-items:center;gap:12px;">'
                       f'<span style="font-size:12px;color:{FAINT};">最终结论</span>'
                       f'<span style="font-size:16px;font-weight:700;color:{accent};">{rating}</span></div>')
    return (f'<div style="border:1px solid #ECDFC6;border-radius:15px;overflow:hidden;display:flex;margin-bottom:18px;">'
            f'<div style="width:6px;background:{accent};"></div>'
            f'<div style="flex:1;padding:18px 22px;background:{bg};">'
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:{"10px" if rating else "0"};">'
            f'<span class="mono" style="font-size:14px;font-weight:600;">{ticker}</span>'
            f'<span class="mono" style="font-size:12.5px;color:{FAINT};">{date}</span></div>'
            f'{rating_html}</div></div>')
