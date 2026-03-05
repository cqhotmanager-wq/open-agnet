from typing import List, Tuple

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from app.core.config import load_config
from langchain_openai_like import init_openai_like_embeddings


config = load_config()


class MemoryService:
    def __init__(self) -> None:
        self._connect()
        self.collection = self._get_or_create_collection()
        # Embedding 实例通过统一入口创建，支持 OpenAI / DeepSeek 等 OpenAI-like 服务
        self.embeddings = init_openai_like_embeddings()

    def _connect(self) -> None:
        connections.connect(
            alias="default", host=config.vector_store.host, port=str(config.vector_store.port)
        )

    def _get_or_create_collection(self) -> Collection:
        collection_name = config.vector_store.collection
        if not utility.has_collection(collection_name):
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="user_id", dtype=DataType.INT64),
                FieldSchema(name="session_uuid", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="role", dtype=DataType.VARCHAR, max_length=16),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2048),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536),
            ]
            schema = CollectionSchema(fields=fields, description="Chat memory")
            collection = Collection(name=collection_name, schema=schema)
            collection.create_index(
                field_name="embedding",
                index_params={
                    "metric_type": "IP",
                    "index_type": "IVF_FLAT",
                    "params": {"nlist": 1024},
                },
            )
        else:
            collection = Collection(collection_name)
        collection.load()
        return collection

    def _embed(self, text: str) -> List[float]:
        return self.embeddings.embed_query(text)

    def add_messages(
        self,
        user_id: int,
        session_uuid: str,
        messages: List[BaseMessage],
    ) -> None:
        roles: List[str] = []
        contents: List[str] = []
        embeddings: List[List[float]] = []

        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "human"
            elif isinstance(msg, AIMessage):
                role = "ai"
            else:
                role = "other"
            roles.append(role)
            contents.append(msg.content)
            embeddings.append(self._embed(msg.content))

        data = [
            [user_id] * len(messages),
            [session_uuid] * len(messages),
            roles,
            contents,
            embeddings,
        ]

        self.collection.insert(
            data,
            insert_param={
                "fields": ["user_id", "session_uuid", "role", "content", "embedding"]
            },
        )

    def query_history(
        self,
        user_id: int,
        session_uuid: str,
        query_text: str,
        top_k: int = 6,
    ) -> List[Tuple[str, str]]:
        """
        使用当前用户问题的向量，在 user_id + session_uuid 过滤条件下进行相似度 TopK 检索。
        返回按相似度排序的 (role, content) 列表。
        """
        expr = f"user_id == {user_id} && session_uuid == '{session_uuid}'"
        query_vec = self._embed(query_text)
        search_params = {"metric_type": "IP", "params": {"nprobe": 16}}

        results = self.collection.search(
            data=[query_vec],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["role", "content"],
        )

        history: List[Tuple[str, str]] = []
        if results:
            for hit in results[0]:
                history.append((hit.entity.get("role"), hit.entity.get("content")))
        return history

    def clear_session(self, user_id: int, session_uuid: str) -> None:
        expr = f"user_id == {user_id} && session_uuid == '{session_uuid}'"
        self.collection.delete(expr)

