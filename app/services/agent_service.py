from typing import List

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.core.config import load_config
from app.models.user import User
from app.services.memory_service import MemoryService
from app.services.skill_service import SkillService
from app.tools import get_all_tools


config = load_config()


class AgentService:
    def __init__(self) -> None:
        self.memory_service = MemoryService()
        self.skill_service = SkillService()

    def _build_llm(self) -> ChatOpenAI:
        """
        根据配置构建 LLM。

        - OpenAI 官方：provider = \"openai\"，base_url 为空，使用默认 OpenAI 端点
        - DeepSeek 等 OpenAI 兼容服务：
          - provider = \"deepseek\"
          - model = \"deepseek-chat\"
          - base_url = \"https://api.deepseek.com/v1\"
        """
        llm_cfg = config.llm
        kwargs: dict = {
            "model": llm_cfg.model,
            "api_key": llm_cfg.api_key,
            "temperature": llm_cfg.temperature,
        }
        if llm_cfg.max_tokens is not None:
            kwargs["max_tokens"] = llm_cfg.max_tokens
        # 对于 DeepSeek 等 OpenAI 兼容服务，通过 base_url 指向其 API 网关
        if llm_cfg.base_url:
            kwargs["base_url"] = llm_cfg.base_url
        return ChatOpenAI(**kwargs)

    def build_agent(self):
        """构建 LangChain 1.x 的 create_agent 图（带工具循环）。"""
        system_fragment = self.skill_service.build_system_message_fragment()
        system_prompt = (
            "你是一个智能体平台助手，能够利用提供的技能帮助用户完成任务。\n"
            f"{system_fragment}\n"
            "你拥有细粒度工具：文件与目录的读写与列举、Markdown/JSON 读写、数据库 SQL 查询、"
            "PDF/Word/Excel/CSV 加载、网页抓取、搜索引擎、HTML 解析等。请组合这些工具完成创建技能、"
            "加载技能文档、查询数据、抓取网页等操作。"
        )

        llm = self._build_llm()

        tools = get_all_tools()
        graph = create_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
        )
        return graph

    def _build_augmented_query(
        self,
        user_id: int,
        session_uuid: str,
        message: str,
    ) -> str:
        """
        使用 Milvus 中基于向量相似度检索到的 TopK 历史对话，拼接成上下文 + 当前问题。
        """
        history_pairs = self.memory_service.query_history(
            user_id=user_id,
            session_uuid=session_uuid,
            query_text=message,
        )
        if not history_pairs:
            return message

        history_lines: List[str] = []
        for role, content in history_pairs:
            prefix = "用户" if role == "human" else "助手"
            history_lines.append(f"{prefix}：{content}")

        history_block = "\n".join(history_lines)
        augmented = (
            "下面是与当前问题最相关的历史对话片段，请在回答时充分参考这些上下文：\n"
            f"{history_block}\n\n"
            f"当前用户问题：{message}"
        )
        return augmented

    def chat(self, user: User, session_uuid: str, message: str) -> str:
        graph = self.build_agent()
        augmented_query = self._build_augmented_query(
            user_id=user.id,
            session_uuid=session_uuid,
            message=message,
        )
        inputs = {"messages": [HumanMessage(content=augmented_query)]}
        result = graph.invoke(inputs)
        # 取最后一条 AI 消息作为回复
        messages = result.get("messages", [])
        last_ai = None
        for m in reversed(messages):
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

