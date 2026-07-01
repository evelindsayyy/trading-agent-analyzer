# TradingAgents/graph/setup.py

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from tradingagents.agents import (
    create_aggressive_debator,
    create_bear_researcher,
    create_bull_researcher,
    create_conservative_debator,
    create_fundamentals_analyst,
    create_market_analyst,
    create_msg_delete,
    create_neutral_debator,
    create_news_analyst,
    create_portfolio_manager,
    create_research_manager,
    create_sentiment_analyst,
    create_trader,
)
from tradingagents.agents.utils.agent_states import AgentState

from .analyst_execution import ANALYST_NODE_SPECS, build_analyst_execution_plan
from .conditional_logic import ConditionalLogic


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: Any,
        deep_thinking_llm: Any,
        tool_nodes: dict[str, ToolNode],
        conditional_logic: ConditionalLogic,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes
        self.conditional_logic = conditional_logic

    def setup_graph(
        self, selected_analysts=("market", "social", "news", "fundamentals")
    ):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
        """
        plan = build_analyst_execution_plan(selected_analysts)
        analyst_factories = self._analyst_factories()

        # Create workflow
        workflow = StateGraph(AgentState)

        # Add analyst nodes to the graph
        for spec in plan.specs:
            workflow.add_node(spec.agent_node, analyst_factories[spec.key]())
            workflow.add_node(spec.clear_node, create_msg_delete())
            workflow.add_node(spec.tool_node, self.tool_nodes[spec.key])

        # Add the post-analyst pipeline (researchers → trader → risk → PM).
        self._add_downstream_nodes(workflow)

        # Define edges
        # Start with the first analyst
        workflow.add_edge(START, plan.specs[0].agent_node)

        # Connect analysts in sequence
        for i, spec in enumerate(plan.specs):
            self._wire_analyst_loop(workflow, spec)

            # Connect to next analyst or to Bull Researcher if this is the last analyst
            if i < len(plan.specs) - 1:
                workflow.add_edge(spec.clear_node, plan.specs[i + 1].agent_node)
            else:
                workflow.add_edge(spec.clear_node, "Bull Researcher")

        # Add remaining edges
        self._add_downstream_edges(workflow)

        return workflow

    def _analyst_factories(self) -> dict:
        """Factories that build a fresh analyst node bound to the quick LLM."""
        return {
            "market": lambda: create_market_analyst(self.quick_thinking_llm),
            "social": lambda: create_sentiment_analyst(self.quick_thinking_llm),
            "news": lambda: create_news_analyst(self.quick_thinking_llm),
            "fundamentals": lambda: create_fundamentals_analyst(self.quick_thinking_llm),
        }

    def _wire_analyst_loop(self, workflow, spec) -> None:
        """Wire one analyst's tool-calling loop: analyst → (tools → analyst)* → clear."""
        workflow.add_conditional_edges(
            spec.agent_node,
            getattr(self.conditional_logic, f"should_continue_{spec.key}"),
            [spec.tool_node, spec.clear_node],
        )
        workflow.add_edge(spec.tool_node, spec.agent_node)

    def _add_downstream_nodes(self, workflow) -> None:
        """Add the researcher/trader/risk/PM nodes shared by every entry path."""
        workflow.add_node("Bull Researcher", create_bull_researcher(self.quick_thinking_llm))
        workflow.add_node("Bear Researcher", create_bear_researcher(self.quick_thinking_llm))
        workflow.add_node("Research Manager", create_research_manager(self.deep_thinking_llm))
        workflow.add_node("Trader", create_trader(self.quick_thinking_llm))
        workflow.add_node("Aggressive Analyst", create_aggressive_debator(self.quick_thinking_llm))
        workflow.add_node("Neutral Analyst", create_neutral_debator(self.quick_thinking_llm))
        workflow.add_node("Conservative Analyst", create_conservative_debator(self.quick_thinking_llm))
        workflow.add_node("Portfolio Manager", create_portfolio_manager(self.deep_thinking_llm))

    def _add_downstream_edges(self, workflow) -> None:
        """Add the debate/risk conditional edges shared by every entry path."""
        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_edge("Research Manager", "Trader")
        workflow.add_edge("Trader", "Aggressive Analyst")
        workflow.add_conditional_edges(
            "Aggressive Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Conservative Analyst": "Conservative Analyst",
                "Portfolio Manager": "Portfolio Manager",
            },
        )
        workflow.add_conditional_edges(
            "Conservative Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Neutral Analyst": "Neutral Analyst",
                "Portfolio Manager": "Portfolio Manager",
            },
        )
        workflow.add_conditional_edges(
            "Neutral Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Aggressive Analyst": "Aggressive Analyst",
                "Portfolio Manager": "Portfolio Manager",
            },
        )
        workflow.add_edge("Portfolio Manager", END)

    def setup_analyst_subgraph(self, analyst_key: str):
        """Compile a standalone graph for ONE analyst: agent + tool loop + clear.

        Used by the parallel execution path. Each analyst runs in its own thread
        on its own state, so the shared ``messages`` channel never interleaves
        across analysts. Flow: ``START → agent → (tools → agent)* → clear → END``.
        The analyst writes its ``*_report`` field, which the caller merges into
        the downstream graph's state.
        """
        spec = ANALYST_NODE_SPECS[analyst_key]
        factories = self._analyst_factories()

        workflow = StateGraph(AgentState)
        workflow.add_node(spec.agent_node, factories[spec.key]())
        workflow.add_node(spec.clear_node, create_msg_delete())
        workflow.add_node(spec.tool_node, self.tool_nodes[spec.key])

        workflow.add_edge(START, spec.agent_node)
        self._wire_analyst_loop(workflow, spec)
        workflow.add_edge(spec.clear_node, END)
        return workflow

    def setup_downstream_graph(self):
        """Compile the post-analyst pipeline as a standalone graph.

        Entry is the Bull Researcher; the four ``*_report`` fields must already
        be populated in the initial state (the parallel path fills them from the
        analyst subgraphs before invoking this).
        """
        workflow = StateGraph(AgentState)
        self._add_downstream_nodes(workflow)
        workflow.add_edge(START, "Bull Researcher")
        self._add_downstream_edges(workflow)
        return workflow
