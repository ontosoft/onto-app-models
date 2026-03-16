from fastapi import APIRouter

from app.schemas import TextProcessRequest, WordCountResponse

router = APIRouter(prefix="/text", tags=["text-processing"])


@router.post("/word-count", response_model=WordCountResponse)
def get_word_count(payload: TextProcessRequest) -> WordCountResponse:
    """
    Receives a text payload and returns the word count.
    """
    word_count = len(payload.text.split())
    return WordCountResponse(
        word_count=word_count,
        text_length=len(payload.text),
        message="Text processed successfully.",
    )