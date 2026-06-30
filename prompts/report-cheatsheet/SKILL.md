---
name: report-cheatsheet
description: Turn a TradingAgents report into a beginner-friendly cheatsheet a new trader can actually act on — one-line verdict, the exact numbers (entry/target/stop), step-by-step plan, plain-language "why", risks, and a jargon decoder. Use when the user wants a simple, actionable summary of a generated report, asks "what do I actually do with this report?", or says summarize/cheatsheet/给我一个速查表 for a stock report.
argument-hint: [report-dir-or-symbol] [shares-held] [cost-basis]
allowed-tools: Read Glob Write Bash(ls *) Bash(find *)
---

# Report → Beginner Cheatsheet

Your job: take ONE TradingAgents report and turn it into a single-page cheatsheet that a brand-new trader can read in two minutes and act on with confidence. You are a **translator, not an analyst** — the trading judgment already lives in the report. You make it legible. You do not add your own market opinion.

## Step 1 — Find the report

The argument (`$ARGUMENTS`) may contain: a report locator (directory path or ticker symbol, can be empty) + optional **holdings** (shares held, and optional cost basis).

- **A directory path** (e.g. `reports/WDC_20260630_120612`) → use it directly.
- **A bare symbol** (e.g. `WDC`) → find the newest matching folder: `ls -td reports/<SYMBOL>_*/ | head -1`.
- **Empty** → use the most recently generated report overall: `ls -td reports/*/ | head -1`. Tell the user which one you picked.

If no `reports/` folder or no match exists, say so and stop — do not invent a report.

**Holdings**: pick up the user's current position from the arguments or conversation (e.g. "I hold 80 shares at $610", "0 shares", "no position"). This decides how Step 3's plan is written (see "Position-aware logic"). If the user says nothing, treat holdings as "not provided" — **do not assume or invent a position.**

## Step 2 — Read the source files (and ONLY these)

Read these role files from the report directory. **Do not** read `complete_report.md` (it's ~1500 lines and redundant) unless the role files below are missing.

| Priority | File | What you pull from it |
|---|---|---|
| 1 | `5_portfolio/decision.md` | Final **Rating**, executive summary, **Price Target**, **Time Horizon**, thesis |
| 2 | `3_trading/trader.md` | **Action** (Buy/Sell/Hold), **Stop Loss**, **Position Sizing**, `FINAL TRANSACTION PROPOSAL` |
| 3 | `2_research/manager.md` | **Recommendation** + numbered **Strategic Actions** (the staged plan) |
| 4 | `1_analysts/market.md` | Key support/resistance prices, indicators (MACD, RSI, 均线, 布林带, ATR) |
| 5 | `key_levels_cheatsheet.md` | If present, reuse its price levels & trigger table — don't recompute them |
| 6 (skim) | `1_analysts/sentiment.md`, `1_analysts/news.md` | Catalysts & dates to watch |
| 7 (skim) | `2_research/bull.md`, `2_research/bear.md` | The bull vs bear case, to explain "why" simply |

## Step 3 — Write the cheatsheet

Write in the **same language as the report** (these reports are usually Simplified Chinese — match it). Keep it to roughly one page. Use these exact sections, in order:

1. **一句话结论 / Bottom line** — Buy/Sell/Hold + the rating (e.g. Underweight/减仓) + the single most important reason, in one sentence a beginner gets. Then a tight line: 当前价 · 目标价 · 时间周期.
2. **数字速查 / Key numbers** — A small table: 当前价, 建仓/加仓区, 目标价, 硬止损, 仓位建议. **Every number quoted verbatim from the report.**
3. **怎么做：分步操作 / The plan, step by step** — The heart of the cheatsheet. Numbered, concrete actions with their trigger conditions, lifted from `trader.md` Position Sizing and `manager.md` Strategic Actions. Write each step as **"trigger → concrete action → why"** so a beginner can just follow it. Then apply the **Position-aware logic below** to decide the section's angle and the actual "sell/buy how much" numbers.
4. **为什么 / Why (in plain words)** — 2–4 bullets: the bull case in one line, the bear case in one line, and which side the report sided with. No jargon left unexplained.
5. **风险 & 可能出错的地方 / Risks** — What could blow up the plan (e.g. 跳空击穿止损、财报反转、利润率均值回归). Always include a position-sizing / risk caveat.
6. **报告没告诉你的 / What this report does NOT cover** — The honest section. The open questions, assumptions the report rests on, and 2–3 things the *reader* must decide for themselves (e.g. "55%净利率是结构性还是周期性?"). This replaces fabricated advice.
7. **名词速查 / Jargon decoder** — One plain line each, ONLY for terms that actually appear (e.g. MACD死叉、布林带、ATR、FCF收益率、Underweight). Skip terms not used.
8. **免责声明 / Disclaimer** — One line: this is a plain-language summary of a model-generated report, a snapshot for the report's date, NOT investment advice; prices are time-sensitive.

### Position-aware logic (decides how section 3 is written)

The plan takes a different angle depending on the user's holdings. **State the assumed position in one line at the top of section 3** (e.g. "Assumes: you currently hold 80 shares at $610" or "Assumes: you currently hold no position (0 shares)") so the reader sees the premise.

- **Has a position (shares > 0)** → after each step, compute the **actual share count**: e.g. "cut to 50% → sell `round(shares×0.5)` shares, keep `shares − sold`". Sell the high-cost, thin-profit lots first. If a cost basis was given, show the current per-share P&L (price − cost) and roughly what each step realizes. Use the user's real share count — don't round to numbers unrelated to it.
- **No position (0 shares / flat)** → the report's reduce/sell plan is written for someone who **already holds**; it doesn't apply directly. **Rewrite from a would-be-buyer's angle**, grounded in the report:
  1. **Should you buy now**: translate the report's verdict (if it's reduce/sell, or the target is below the current price → usually "don't chase here", and say why the odds skew down).
  2. **Buy plan**: use the report's own **re-entry / trigger conditions** as the buy signals (e.g. pull back to the target zone on rising volume, MACD re-cross above a key MA, an earnings print that confirms the thesis).
  3. **Buy stop**: give a suggested exit price (the report's hard stop, or a fixed % below the entry/trigger).
  - Label it clearly: this translates the report's *exit logic* into an *entry view*; it is not the report's own words.
- **Not provided** → use percentages (cut to X%) and may append a one-line worked example per step ("e.g. holding 100 shares → sell 50"), clearly marked as **illustration/education**.

## Step 4 — Save and present

Write the cheatsheet to `beginner_cheatsheet.md` **inside the same report directory**, then show it to the user inline and tell them the path.

## Hard rules (do not break these)

1. **Never invent numbers.** Every price, target, stop, percentage, and date comes from the report. If the report doesn't state it, write "报告未给出" — never estimate.
2. **Never override the call.** The Buy/Sell/Hold and the rating are the report's. Don't soften, flip, or second-guess them with your own view. If `trader.md` and `decision.md` disagree, surface BOTH and say they differ — don't pick a winner.
3. **General trading education is allowed, but fenced off and labeled.** If you explain a general concept (how a stop-loss works, what 减仓 means for a beginner), keep it in the Jargon decoder or clearly mark it as 一般知识/教育, never as a specific recommendation. Do not generate new strategies that aren't grounded in the report.
4. **Always keep the risk + stop + position-sizing caveats.** A cheatsheet without a stop loss and sizing is dangerous — never drop them.
5. **Plain language.** Every piece of jargon gets decoded. Assume the reader has never traded before.
6. **One report at a time, one page.** If the user points at multiple reports, do them one at a time.
7. **Never invent holdings.** If the user gives no share count, treat it as "not provided" — never assume a specific position. The would-be-buyer plan for a flat account must be grounded in the report's trigger conditions and labeled "exit logic translated into an entry view" — not the report's own words, and not a new strategy you made up. The buy stop reuses the report's stop or a clearly-labeled fixed %.
