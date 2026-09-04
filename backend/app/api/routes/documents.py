from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import require_write_access
from app.ingest.catalog import (
    delete_indexed_document,
    find_pdf_by_doc_id,
    list_document_infos,
    save_upload,
)
from app.ingest.ingest import run_ingest
from app.models.schemas import DocumentInfo

router = APIRouter(tags=["documents"])


@router.get("/documents", response_model=list[DocumentInfo])
def list_documents() -> list[DocumentInfo]:
    return list_document_infos()


@router.post("/documents", response_model=list[DocumentInfo], status_code=201)
async def upload_documents(
    files: list[UploadFile] = File(...),
    _: None = Depends(require_write_access),
) -> list[DocumentInfo]:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")
    saved: list[str] = []
    for upload in files:
        name = upload.filename or ""
        data = await upload.read()
        try:
            path = save_upload(name, data)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        saved.append(path.name)
    run_ingest(filenames=saved)
    by_name = {doc.filename: doc for doc in list_document_infos()}
    return [by_name[name] for name in saved if name in by_name]


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str, _: None = Depends(require_write_access)) -> Response:
    try:
        delete_indexed_document(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found.") from exc
    return Response(status_code=204)


@router.post("/documents/{doc_id}/reindex", response_model=DocumentInfo)
def reindex_document(doc_id: str, _: None = Depends(require_write_access)) -> DocumentInfo:
    path = find_pdf_by_doc_id(doc_id)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Document PDF not found on disk.")
    run_ingest(filenames=[path.name])
    for doc in list_document_infos():
        if doc.filename == path.name:
            return doc
    raise HTTPException(
        status_code=500,
        detail="Re-index finished but document is missing from the catalog.",
    )


@router.get("/documents/{doc_id}/file")
def get_document_file(doc_id: str) -> FileResponse:
    path = find_pdf_by_doc_id(doc_id)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="PDF file not found.")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
        content_disposition_type="inline",
    )
