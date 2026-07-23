"""Use a bounded LangChain agent only to formulate retrieval queries."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel

from app.llm import LLMProviderError

SearchCallback = Callable[[str], Awaitable[str]]


@dataclass(frozen=True, slots=True)
class AgentQueryPlan:
    """Retrieval queries actually executed by the agent's only tool."""

    queries: tuple[str, ...]


class QueryPlanningAgent:
    """Allow one read-only search tool and discard the model's final prose."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model

    async def plan(
        self,
        *,
        question: str,
        search: SearchCallback,
    ) -> AgentQueryPlan:
        """Run a short tool loop and return only server-observed search calls."""

        executed_queries: list[str] = []

        @tool("search_detected_pest_knowledge")
        async def search_detected_pest_knowledge(query: str) -> str:
            """Search reviewed knowledge only for pests in the detection task."""

            clean_query = query.strip()
            if not clean_query:
                return "The search query was empty."
            if len(executed_queries) >= 3:
                return "The maximum of three retrieval calls has been reached."
            executed_queries.append(clean_query)
            return await search(clean_query)

        runtime = create_agent(
            model=self._model,
            tools=[search_detected_pest_knowledge],
            system_prompt=(
                "你是农业知识检索规划器。必须调用唯一的检索工具来回答用户问题。"
                "工具范围已经由后端限制为当前检测任务中的害虫。"
                "不得请求其他实体，不得执行写入操作。"
                "你的最终自然语言回答不会被系统采用。"
            ),
        )
        try:
            await runtime.ainvoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": question,
                        }
                    ]
                },
                config={"recursion_limit": 6},
            )
        except Exception as exc:
            raise LLMProviderError(
                code="AGENT_QUERY_PLANNING_FAILED",
                message="The bounded retrieval agent could not plan a query.",
                retryable=False,
            ) from exc

        if not executed_queries:
            raise LLMProviderError(
                code="AGENT_DID_NOT_RETRIEVE",
                message="The bounded retrieval agent did not call its search tool.",
                retryable=False,
            )
        return AgentQueryPlan(queries=tuple(executed_queries))
