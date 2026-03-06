from typing import List, Tuple

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_openai import OpenAIEmbeddings
from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from app.core.config import load_config


config = load_config()


class MemoryService:
    def __init__(self) -> None:
        self._connect()
        self.collection = self._get_or_create_collection()
        # Embedding：使用 OpenAIEmbeddings，支持 DeepSeek 等 OpenAI 兼容服务
        self.embeddings = OpenAIEmbeddings(
            model=config.embedding.model,
            api_key=config.embedding.api_key,
            base_url=config.embedding.base_url,
            dimensions=config.embedding.dimensions,
        )

    def _connect(self) -> None:
        connections.connect(
            alias="default", host=config.vector_store.host, port=str(config.vector_store.port)
        )

    def _get_or_create_collection(self) -> Collection:
        collection_name = config.vector_store.collection
        expected_dim = config.embedding.dimensions

        if utility.has_collection(collection_name):
            coll = Collection(collection_name)
            coll.load()
            reuse = True
            for f in coll.schema.fields:
                if f.name == "embedding" and f.dtype == DataType.FLOAT_VECTOR:
                    if f.params.get("dim") != expected_dim:
                        coll.release()
                        utility.drop_collection(collection_name)
                        reuse = False
                    break
            if reuse:
                return coll

        # 不存在或维度不一致已 drop：按 config.embedding.dimensions 创建
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="user_id", dtype=DataType.INT64),
            FieldSchema(name="session_uuid", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="role", dtype=DataType.VARCHAR, max_length=16),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=expected_dim),
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

        expected_dim = config.embedding.dimensions
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "human"
            elif isinstance(msg, AIMessage):
                role = "ai"
            else:
                role = "other"
            roles.append(role)
            contents.append(msg.content)
            vec = self._embed(msg.content)
            if len(vec) != expected_dim:
                raise ValueError(
                    f"Embedding 维度与配置不一致：模型返回 {len(vec)} 维，config.embedding.dimensions={expected_dim}。"
                    "请将 config.yaml 中 embedding.dimensions 改为与模型输出一致（如 2048），并重启服务以重建 Milvus collection。"
                )
            embeddings.append(vec)

        data = [
            [user_id] * len(messages),
            [session_uuid] * len(messages),
            roles,
            contents,
            embeddings,
        ]

        # 插入时不要传 insert_param（pymilvus 会根据 schema 自动对齐）；data 顺序与 schema 字段顺序一致（不含 auto_id 的 id）
        self.collection.insert(data)

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

