"""
Prompt 模板层：将 ContextData 格式化为发给 LLM 的 message 列表。
顺序为：System → User profile → Conversation summary → Recent history → Retrieved memory → Current question。
"""
from typing import List

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

from app.context.context_builder import ContextData


def build_messages(context_data: ContextData) -> List[BaseMessage]:
    """
    将 ContextData 转为 LLM 接受的 message 列表。
    顺序：system_prompt → user_profile → conversation_summary → recent_history → retrieved_docs → user_question。
    """
    messages: List[BaseMessage] = []

    if context_data.system_prompt:
        messages.append(SystemMessage(content=context_data.system_prompt))

    if context_data.user_profile:
        messages.append(
            SystemMessage(content="User profile: " + context_data.user_profile)
        )

    if context_data.conversation_summary:
        messages.append(
            SystemMessage(
                content="Conversation summary: " + context_data.conversation_summary
            )
        )

    messages.extend(context_data.recent_history)

    if context_data.retrieved_docs:
        messages.append(
            SystemMessage(
                content="Relevant knowledge (retrieved from memory):\n"
                + context_data.retrieved_docs
            )
        )

    messages.append(HumanMessage(content=context_data.user_question))

    return messages
