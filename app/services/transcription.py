from fastapi import UploadFile, HTTPException
import os
import httpx

TRANSCRIBE_SERVICE_URL = os.getenv("TRANSCRIBE_SERVICE_URL")


async def transcribe_audio(file: UploadFile) -> str:
    if not TRANSCRIBE_SERVICE_URL:
        raise HTTPException(
            status_code=500,
            detail="TRANSCRIBE_SERVICE_URL not set. Implement transcription or set the env var.",
        )

    async with httpx.AsyncClient(timeout=120) as client:
        files = {"file": (file.filename, await file.read(), file.content_type)}
        resp = await client.post(TRANSCRIBE_SERVICE_URL, files=files)

    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Transcription error: {resp.text}")

    data = resp.json()
    transcript = data.get("text") or data.get("transcript")
    if not transcript:
        raise HTTPException(status_code=500, detail="No transcript returned.")
    return transcript
