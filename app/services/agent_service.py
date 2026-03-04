from typing import List

from langchain.agents import AgentExecutor, initialize_agent, AgentType
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.core.config import load_config
from app.models.user import User
from app.services.memory_service import MemoryService
from app.services.skill_service import SkillService
from app.tools.create_skill_tool import CreateSkillTool
from app.tools.skill_tool import SkillTool


config = load_config()


class AgentService:
    def __init__(self) -> None:
        self.memory_service = MemoryService()
        self.skill_service = SkillService()

    def build_agent(self) -> AgentExecutor:
        system_fragment = self.skill_service.build_system_message_fragment()
        system_prompt = (
            "你是一个智能体平台助手，能够利用提供的技能帮助用户完成任务。\n"
            f"{system_fragment}\n"
            "在需要时，选择合适的技能或创建新技能。"
        )

        llm = ChatOpenAI(
            model=config.llm.model,
            openai_api_key=config.llm.api_key,
            temperature=0.3,
        )

        tools = [
            SkillTool(),
            CreateSkillTool(),
        ]

        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False,
        )
        # 将系统提示词直接注入 Agent 的说明中
        agent.system_prompt = system_prompt
        return agent

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
        agent = self.build_agent()
        augmented_query = self._build_augmented_query(
            user_id=user.id,
            session_uuid=session_uuid,
            message=message,
        )
        result = agent.run(augmented_query)

        human = HumanMessage(content=message)
        ai = AIMessage(content=result)
        self.memory_service.add_messages(
            user_id=user.id,
            session_uuid=session_uuid,
            messages=[human, ai],
        )
        return result

