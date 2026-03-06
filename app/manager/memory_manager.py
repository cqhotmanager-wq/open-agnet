"""
统一记忆管理：SQL 存完整聊天与摘要，Milvus agent_memory 存长期向量记忆。
通过 user_id + session_uuid 在向量库中定位本次会话；通过 user_id 可查用户全部会话。
提供：最近历史（SQL）、摘要（SQL）、向量检索（Milvus）、写入聊天/重要记忆、摘要更新（LLM）。
"""
import time
from typing import List, Literal, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
from sqlalchemy.orm import Session

from app.core.config import load_config
from app.repositories import chat_message_repo, conversation_summary_repo
from app.services.memory_service import MemoryService  # 仅复用 embedding 与连接

config = load_config()

# type 取值
AgentMemoryType = Literal["chat", "knowledge", "important_memory"]

SUMMARY_THRESHOLD = 10  # 超过此条数则更新 summary
RECENT_HISTORY_LIMIT = 6
SUMMARY_CONTEXT_MESSAGES = 20  # 生成 summary 时取最近条数


class MemoryManager:
    """
    存储策略：SQL 存完整聊天 + summary；Milvus 存重要记忆与可检索语义。
    查询策略：Recent History 来自 SQL，Summary 来自 SQL，Retrieved Memory 来自 Milvus。
    """

    def __init__(self) -> None:
        self._ensure_milvus_connection()
        self._agent_memory_collection = self._get_or_create_agent_memory_collection()
        # 复用 MemoryService 的 embedding（与现有 config 一致）
        self._embedding_service = MemoryService()

    def _ensure_milvus_connection(self) -> None:
        try:
            connections.connect(
                alias="default",
                host=config.vector_store.host,
                port=str(config.vector_store.port),
            )
        except Exception:
            pass  # 已连接则忽略

    def _get_or_create_agent_memory_collection(self) -> Collection:
        name = getattr(
            config.vector_store,
            "agent_memory_collection",
            "agent_memory",
        )
        dim = config.embedding.dimensions

        if utility.has_collection(name):
            coll = Collection(name)
            coll.load()
            field_names = {f.name for f in coll.schema.fields}
            # 维度或缺少 user_id 时重建集合，保证支持 user_id + session_uuid 查询
            need_recreate = "user_id" not in field_names
            for f in coll.schema.fields:
                if f.name == "embedding" and f.dtype == DataType.FLOAT_VECTOR:
                    if f.params.get("dim") != dim:
                        need_recreate = True
                    break
            if need_recreate:
                coll.release()
                utility.drop_collection(name)
            else:
                return coll

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="user_id", dtype=DataType.INT64),
            FieldSchema(name="session_uuid", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=32),
            FieldSchema(name="timestamp", dtype=DataType.INT64),
        ]
        schema = CollectionSchema(fields=fields, description="Agent long-term memory")
        collection = Collection(name=name, schema=schema)
        collection.create_index(
            field_name="embedding",
            index_params={
                "metric_type": "IP",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024},
            },
        )
        collection.load()
        return collection

    # ---------- 写入 ----------

    def add_chat_messages(
        self,
        db: Session,
        session_uuid: str,
        messages: List[BaseMessage],
    ) -> None:
        """每条消息：存 SQL chat_message。"""
        chat_message_repo.insert_messages(db, session_uuid, messages)

    def add_important_memory(
        self,
        user_id: int,
        session_uuid: str,
        text: str,
        memory_type: AgentMemoryType = "important_memory",
    ) -> None:
        """重要记忆写入 Milvus agent_memory，便于按 user_id + session_uuid 查询。"""
        vec = self._embedding_service._embed(text)
        dim = config.embedding.dimensions
        if len(vec) != dim:
            return
        data = [
            [user_id],
            [session_uuid],
            [text[:4095]],
            [vec],
            [memory_type],
            [int(time.time())],
        ]
        self._agent_memory_collection.insert(data)

    def upsert_summary(self, db: Session, session_uuid: str, summary: str) -> None:
        """更新会话摘要。"""
        conversation_summary_repo.upsert_summary(db, session_uuid, summary)

    def clear_session(
        self, db: Session, user_id: int, session_uuid: str
    ) -> None:
        """清空该会话的 SQL 聊天/摘要与 Milvus 向量记忆（按 user_id + session_uuid 限定）。"""
        from app.models.chat_message import ChatMessage
        from app.models.conversation_summary import ConversationSummary
        db.query(ChatMessage).filter(ChatMessage.session_uuid == session_uuid).delete()
        db.query(ConversationSummary).filter(
            ConversationSummary.session_uuid == session_uuid
        ).delete()
        db.commit()
        expr = f"user_id == {user_id} && session_uuid == '{session_uuid}'"
        self._agent_memory_collection.delete(expr)

    # ---------- 查询 ----------

    def get_recent_history(
        self,
        db: Session,
        session_uuid: str,
        limit: int = RECENT_HISTORY_LIMIT,
    ) -> List[tuple]:
        """Recent History：来自 SQL，ORDER BY created_at DESC LIMIT 6。"""
        return chat_message_repo.get_recent(db, session_uuid, limit=limit)

    def get_summary(self, db: Session, session_uuid: str) -> str:
        """Summary：来自 SQL conversation_summary。"""
        return conversation_summary_repo.get_summary(db, session_uuid)

    def get_retrieved_memory(
        self,
        user_id: int,
        session_uuid: str,
        query_text: str,
        top_k: int = 6,
    ) -> List[str]:
        """Vector Retrieval：Milvus 按 user_id + session_uuid 过滤本次会话，返回 text 列表。"""
        query_vec = self._embedding_service._embed(query_text)
        search_params = {"metric_type": "IP", "params": {"nprobe": 16}}
        expr = f"user_id == {user_id} && session_uuid == '{session_uuid}'"
        results = self._agent_memory_collection.search(
            data=[query_vec],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["text"],
        )
        if not results:
            return []
        return [hit.entity.get("text", "") for hit in results[0]]

    # ---------- Summary 更新（history > 10 或会话结束时由调用方触发）----------

    def update_summary_if_needed(
        self,
        db: Session,
        session_uuid: str,
        llm: Optional[ChatOpenAI] = None,
    ) -> None:
        """若当前会话消息数 > SUMMARY_THRESHOLD，则用 LLM 生成摘要并写入。"""
        count = chat_message_repo.count_by_session(db, session_uuid)
        if count <= SUMMARY_THRESHOLD:
            return
        old_summary = conversation_summary_repo.get_summary(db, session_uuid)
        recent_pairs = chat_message_repo.get_recent(
            db, session_uuid, limit=SUMMARY_CONTEXT_MESSAGES
        )
        if not recent_pairs:
            return
        lines = []
        for role, content in recent_pairs:
            prefix = "用户" if role == "human" else "助手"
            lines.append(f"{prefix}：{content}")
        conversation_block = "\n".join(lines)

        if llm is None:
            llm = ChatOpenAI(
                model=config.llm.model,
                api_key=config.llm.api_key,
                base_url=config.llm.base_url,
                temperature=0.1,
                max_tokens=1024,
            )
        prompt = (
            "请将以下对话压缩成一段简洁的会话摘要（保留关键事实与结论），用于后续上下文。"
            "若已有「上一轮摘要」，请在其基础上合并新对话内容。\n\n"
        )
        if old_summary:
            prompt += f"上一轮摘要：\n{old_summary}\n\n"
        prompt += "最近对话：\n" + conversation_block
        response = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content="请输出摘要。"),
        ])
        summary_text = getattr(response, "content", "") or str(response)
        conversation_summary_repo.upsert_summary(db, session_uuid, summary_text.strip())
