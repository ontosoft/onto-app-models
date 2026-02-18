from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import ollama
import asyncio

router = APIRouter(prefix="/stream", tags=["stream"])
client = ollama.AsyncClient(host='http://ollama:11434')

async def llama_streamer(prompt: str):
    """Generator that yields chunks of text from Llama."""
    async for part in await client.generate(model='llama3.2', prompt=prompt, stream=True):
        yield part['response']

@router.get("/stream")
async def stream_ai(prompt: str):
    return StreamingResponse(llama_streamer(prompt), media_type="text/plain")
