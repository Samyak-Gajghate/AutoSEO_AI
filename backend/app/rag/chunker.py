from typing import List


def chunk_text(text: str, chunk_size: int = 300, overlap: int = 50) -> List[str]:
    """
    Splits text into overlapping chunks of ~chunk_size words.
    Overlap ensures context continuity at chunk boundaries.

    Args:
        text:       Raw page text to chunk.
        chunk_size: Target chunk size in words.
        overlap:    Number of words to overlap between adjacent chunks.

    Returns:
        List of chunk strings.
    """
    if not text or not text.strip():
        return []

    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap  # slide window with overlap

    return chunks
