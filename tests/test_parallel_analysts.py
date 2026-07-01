"""Unit tests for the concurrent-analyst execution path (TradingAgentsGraph._run_parallel).

These exercise the orchestration logic — dispatch, report merge, section
streaming, and message isolation — with fake compiled subgraphs, so no real
LLM/tool calls happen.
"""
import threading

import pytest

from tradingagents.graph.trading_graph import TradingAgentsGraph


class _FakeCompiled:
    """Stand-in for a compiled LangGraph: records inputs, returns fixed output."""

    def __init__(self, output: dict):
        self._output = output
        self.seen_states: list[dict] = []
        self._lock = threading.Lock()

    def invoke(self, state, **kwargs):
        with self._lock:
            self.seen_states.append(state)
        return dict(self._output)


def _make_graph(selected, analyst_subgraphs, downstream) -> TradingAgentsGraph:
    # Bypass __init__ (which builds real LLM clients) and inject the pieces
    # _run_parallel needs. _build_parallel_graphs() is a no-op once the
    # subgraphs are already set.
    g = TradingAgentsGraph.__new__(TradingAgentsGraph)
    g.selected_analysts = tuple(selected)
    g._analyst_subgraphs = analyst_subgraphs
    g._downstream_graph = downstream
    return g


@pytest.mark.unit
def test_report_key_maps_cover_all_analysts():
    assert set(TradingAgentsGraph._ANALYST_REPORT_KEY) == {
        "market", "social", "news", "fundamentals"}
    # Every analyst's report field has a report-tree path for streaming.
    for report_key in TradingAgentsGraph._ANALYST_REPORT_KEY.values():
        assert report_key in TradingAgentsGraph._REPORT_KEY_PATH


@pytest.mark.unit
def test_run_parallel_merges_reports_and_streams_sections():
    analysts = {
        "market": _FakeCompiled({"market_report": "MKT"}),
        "news": _FakeCompiled({"news_report": "NWS"}),
    }
    downstream = _FakeCompiled({"final_trade_decision": "BUY"})
    g = _make_graph(["market", "news"], analysts, downstream)

    streamed = []
    out = g._run_parallel(
        {"messages": [("human", "NVDA")], "company_of_interest": "NVDA"},
        {"config": {}},
        on_section=lambda path, content: streamed.append((path, content)),
    )

    # Returns the downstream pipeline's output.
    assert out == {"final_trade_decision": "BUY"}
    # Downstream received both analyst reports merged into its state.
    ds_state = downstream.seen_states[0]
    assert ds_state["market_report"] == "MKT"
    assert ds_state["news_report"] == "NWS"
    assert ds_state["company_of_interest"] == "NVDA"
    # A finished section was streamed for each analyst, keyed by report path.
    assert set(streamed) == {
        ("1_analysts/market.md", "MKT"),
        ("1_analysts/news.md", "NWS"),
    }


@pytest.mark.unit
def test_run_parallel_isolates_messages_between_analysts_and_downstream():
    analysts = {
        "market": _FakeCompiled({"market_report": "M"}),
        "news": _FakeCompiled({"news_report": "N"}),
    }
    downstream = _FakeCompiled({})
    g = _make_graph(["market", "news"], analysts, downstream)

    init = {"messages": [("human", "X")]}
    g._run_parallel(init, {}, on_section=None)

    # Each analyst gets an equal-but-separate messages list (no shared mutation).
    for fake in analysts.values():
        st = fake.seen_states[0]
        assert st["messages"] == [("human", "X")]
        assert st["messages"] is not init["messages"]
    # Downstream also gets a fresh human seed, not the analysts' cleared loop.
    ds_msgs = downstream.seen_states[0]["messages"]
    assert ds_msgs == [("human", "X")]
    assert ds_msgs is not init["messages"]


@pytest.mark.unit
def test_run_parallel_skips_streaming_empty_reports():
    analysts = {"market": _FakeCompiled({"market_report": ""})}
    downstream = _FakeCompiled({})
    g = _make_graph(["market"], analysts, downstream)

    streamed = []
    g._run_parallel({"messages": [("human", "X")]}, {},
                    on_section=lambda p, c: streamed.append(p))

    # No section streamed for an empty report...
    assert streamed == []
    # ...but the (empty) key is still merged for downstream consumption.
    assert downstream.seen_states[0]["market_report"] == ""


@pytest.mark.unit
def test_run_parallel_swallows_on_section_errors():
    analysts = {"market": _FakeCompiled({"market_report": "M"})}
    downstream = _FakeCompiled({"final_trade_decision": "HOLD"})
    g = _make_graph(["market"], analysts, downstream)

    def boom(path, content):
        raise ValueError("streaming sink is down")

    # A failing streaming callback must not fail the whole run.
    out = g._run_parallel({"messages": [("human", "X")]}, {}, on_section=boom)
    assert out == {"final_trade_decision": "HOLD"}
