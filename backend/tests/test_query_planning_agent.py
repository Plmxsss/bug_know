"""Tests for the read-only LangChain query-planning boundary."""

from unittest.mock import Mock, patch

import pytest

from app.agent import QueryPlanningAgent
from app.llm import LLMProviderError


class FakeAgentRuntime:
    """Invoke the captured LangChain tool without any real language model."""

    def __init__(self, search_tool, *, invoke_tool: bool = True) -> None:
        self._search_tool = search_tool
        self._invoke_tool = invoke_tool

    async def ainvoke(self, _input, config):
        assert config["recursion_limit"] == 6
        if self._invoke_tool:
            await self._search_tool.ainvoke({"query": "  稻纵卷叶螟 危害  "})
        return {"messages": []}


async def test_agent_returns_only_queries_observed_by_server_tool() -> None:
    """The model's final prose is absent from the planner's public result."""

    callback_queries: list[str] = []

    async def search(query: str) -> str:
        callback_queries.append(query)
        return '{"point_id":"trusted-point"}'

    def fake_create_agent(*, model, tools, system_prompt):
        assert model is not None
        assert "最终自然语言回答不会被系统采用" in system_prompt
        return FakeAgentRuntime(tools[0])

    with patch(
        "app.agent.query_planner.create_agent",
        side_effect=fake_create_agent,
    ):
        plan = await QueryPlanningAgent(Mock()).plan(
            question="它怎样危害水稻？",
            search=search,
        )

    assert plan.queries == ("稻纵卷叶螟 危害",)
    assert callback_queries == ["稻纵卷叶螟 危害"]


async def test_agent_must_call_the_read_only_retrieval_tool() -> None:
    """A direct model answer is rejected because it has no trusted evidence."""

    async def search(_query: str) -> str:
        raise AssertionError("Search should not be called in this scenario.")

    with patch(
        "app.agent.query_planner.create_agent",
        return_value=FakeAgentRuntime(Mock(), invoke_tool=False),
    ):
        with pytest.raises(LLMProviderError) as exc_info:
            await QueryPlanningAgent(Mock()).plan(
                question="直接回答",
                search=search,
            )

    assert exc_info.value.code == "AGENT_DID_NOT_RETRIEVE"
