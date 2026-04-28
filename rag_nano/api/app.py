from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from rag_nano.api import routes
from rag_nano.components.embedding import get_embedding_provider
from rag_nano.components.retriever import get_retriever
from rag_nano.components.reranker import get_reranker
from rag_nano.components.structured_store import get_structured_store
from rag_nano.components.vector_store import get_vector_store
from rag_nano.config import Settings
from rag_nano.core.retrieval import Components


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="rag-nano", version="1.0.0")

    embedding_provider = get_embedding_provider(settings)
    vector_store = get_vector_store(settings)
    structured_store = get_structured_store(settings)
    retriever = get_retriever(settings)
    reranker = get_reranker(settings)

    app.state.settings = settings
    app.state.components = Components(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        retriever=retriever,
        reranker=reranker,
        structured_store=structured_store,
    )

    app.include_router(routes.router)
    app.add_exception_handler(RequestValidationError, routes.validation_error_handler)

    return app
