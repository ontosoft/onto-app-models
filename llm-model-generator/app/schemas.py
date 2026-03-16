from pydantic import BaseModel, Field


class TextProcessRequest(BaseModel):
    text: str = Field(min_length=1, description="The text to be processed.")


class WordCountResponse(BaseModel):
    word_count: int
    text_length: int
    message: str