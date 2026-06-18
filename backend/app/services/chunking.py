import re


class TextChunker:
    def __init__(self, chunk_size: int, overlap: int) -> None:
        self.chunk_size = chunk_size
        self.overlap = min(overlap, max(chunk_size - 1, 0))

    def split(self, text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []
        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(start + self.chunk_size, len(normalized))
            if end < len(normalized):
                sentence_boundary = normalized.rfind(". ", start, end)
                if sentence_boundary > start + self.chunk_size // 2:
                    end = sentence_boundary + 1
            chunks.append(normalized[start:end].strip())
            if end == len(normalized):
                break
            start = max(end - self.overlap, start + 1)
        return [chunk for chunk in chunks if chunk]
