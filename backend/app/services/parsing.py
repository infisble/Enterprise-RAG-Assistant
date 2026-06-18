from io import BytesIO

from docx import Document as DocxDocument
from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader


class DocumentParser:
    async def parse(self, file: UploadFile) -> str:
        content = await file.read()
        filename = (file.filename or "").lower()
        content_type = file.content_type or "application/octet-stream"

        if filename.endswith(".pdf") or content_type == "application/pdf":
            return self._parse_pdf(content)
        if filename.endswith(".docx") or "wordprocessingml" in content_type:
            return self._parse_docx(content)
        if filename.endswith(".txt") or content_type.startswith("text/"):
            return content.decode("utf-8", errors="ignore")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF, DOCX and TXT uploads are supported",
        )

    @staticmethod
    def _parse_pdf(content: bytes) -> str:
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    @staticmethod
    def _parse_docx(content: bytes) -> str:
        document = DocxDocument(BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
