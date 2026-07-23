"""Routes for uploading provenance-rich agriculture knowledge sources."""

from datetime import date
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from pydantic import HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_db_session
from app.core.config import Settings
from app.schemas import KnowledgeDocumentResponse
from app.services import DocumentStorage, KnowledgeDocumentService

router = APIRouter(prefix="/documents", tags=["knowledge documents"])


@router.post(
    "",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload one agriculture knowledge source",
)
async def upload_document(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: Annotated[UploadFile, File(description="PDF, UTF-8 TXT, or Markdown")],
    title: Annotated[str, Form(min_length=1, max_length=300)],
    source_organization: Annotated[str, Form(min_length=1, max_length=200)],
    entity_ids: Annotated[list[int], Form()],
    source_url: Annotated[HttpUrl | None, Form()] = None,
    publication_date: Annotated[date | None, Form()] = None,
    region: Annotated[str | None, Form(max_length=100)] = None,
) -> KnowledgeDocumentResponse:
    """Validate source bytes and register provenance before indexing."""

    settings = cast(Settings, request.app.state.settings)
    content = await file.read(settings.max_document_bytes + 1)
    await file.close()
    stored = await run_in_threadpool(
        DocumentStorage(settings).validate_and_store,
        content=content,
        filename=file.filename,
        content_type=file.content_type,
    )
    document = await KnowledgeDocumentService(session).register(
        stored=stored,
        title=title,
        source_organization=source_organization,
        source_url=str(source_url) if source_url else None,
        publication_date=publication_date,
        region=region,
        entity_ids=entity_ids,
    )
    return KnowledgeDocumentResponse(
        id=document.id,
        title=document.title,
        source_organization=document.source_organization,
        source_url=document.source_url,
        publication_date=document.publication_date,
        region=document.region,
        file_type=cast(Literal["pdf", "txt", "md"], document.file_type),
        checksum_sha256=document.checksum_sha256,
        status=cast(
            Literal["uploaded", "processing", "indexed", "failed"],
            document.status,
        ),
        entity_ids=sorted(set(entity_ids)),
        created_at=document.created_at,
    )
