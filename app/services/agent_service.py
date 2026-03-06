"""
Agent 服务：组装上下文（ContextBuilder）→ 构建消息（PromptBuilder）→ 调用 LangChain Agent（LLM+工具）→ 写入记忆并更新摘要。
单轮对话入口为 chat()，内部完成「读 SQL/Milvus → 拼 prompt → 调用图 → 存 SQL、可选 Milvus、更新 summary」。
"""
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.core.callbacks import ConsoleLLMCallback
from app.core.config import load_config
from app.models.user import User
from app.context.context_builder import ContextBuilder
from app.manager.memory_manager import MemoryManager
from app.prompt.prompt_builder import build_messages
from app.tools import get_all_tools


config = load_config()


class AgentService:
    """对话流水线：上下文构建 → 消息构建 → Agent 调用 → 记忆与摘要持久化。"""

    def __init__(self) -> None:
        self.memory_manager = MemoryManager()
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

    def chat(self, user: User, session_uuid: str, message: str, db: Session) -> str:
        # Pipeline: Build Context (SQL + Milvus) → Build Messages → LLM → 存 SQL，必要时存 Milvus、更新 Summary
        context_data = self.context_builder.build_context(
            user=user,
            session_uuid=session_uuid,
            user_question=message,
            db=db,
        )
        messages = build_messages(context_data)
        graph = self.build_agent()
        result = graph.invoke(
            {"messages": messages},
            config={"callbacks": [ConsoleLLMCallback()]},
        )
        result_messages = result.get("messages", [])
        last_ai = None
        for m in reversed(result_messages):
            if isinstance(m, AIMessage):
                last_ai = m
                break
        response_text = last_ai.content if last_ai and last_ai.content else str(result)

        # 写入流程：1. 存 SQL chat_message  2. 重要可在此存 Milvus  3. 更新 summary（若 >10 条）
        human = HumanMessage(content=message)
        ai = AIMessage(content=response_text)
        self.memory_manager.add_chat_messages(db, session_uuid, [human, ai])
        # 若需将本条视为重要记忆，可调用：self.memory_manager.add_important_memory(user.id, session_uuid, message, "chat")
        llm = self._build_llm()
        self.memory_manager.update_summary_if_needed(db, session_uuid, llm=llm)
        return response_text

