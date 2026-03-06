from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.core.callbacks import ConsoleLLMCallback
from app.core.config import load_config
from app.models.user import User
from app.services.context_builder import ContextBuilder
from app.services.memory_service import MemoryService
from app.services.prompt_builder import build_messages
from app.tools import get_all_tools


config = load_config()


class AgentService:
    def __init__(self) -> None:
        self.memory_service = MemoryService()
        self.context_builder = ContextBuilder()

    def _build_llm(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=config.llm.model,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )

    def build_agent(self):
        """构建 LangChain 1.x 的 create_agent 图（带工具循环）。系统内容由 Prompt Builder 放入 messages，此处不再重复。"""
        llm = self._build_llm()
        tools = get_all_tools()
        graph = create_agent(
            model=llm,
            tools=tools,
            system_prompt="",
        )
        return graph

    def chat(self, user: User, session_uuid: str, message: str) -> str:
        # Pipeline: User Input → Build Context Data → Build Prompt Messages → Call LLM → Save
        context_data = self.context_builder.build_context(
            user=user,
            session_uuid=session_uuid,
            user_question=message,
        )
        messages = build_messages(context_data)
        graph = self.build_agent()
        result = graph.invoke(
            {"messages": messages},
            config={"callbacks": [ConsoleLLMCallback()]},
        )
        # 取最后一条 AI 消息作为回复
        result_messages = result.get("messages", [])
        last_ai = None
        for m in reversed(result_messages):
            if isinstance(m, AIMessage):
                last_ai = m
                break
        response_text = last_ai.content if last_ai and last_ai.content else str(result)

        human = HumanMessage(content=message)
        ai = AIMessage(content=response_text)
        self.memory_service.add_messages(
            user_id=user.id,
            session_uuid=session_uuid,
            messages=[human, ai],
        )
        return response_text

