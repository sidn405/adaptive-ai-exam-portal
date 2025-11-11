import uuid
from typing import List, Optional, Literal

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import os
import httpx

# ----------------------------------------------------
# Config
# ----------------------------------------------------

# If you have a separate transcription microservice, point to it here.
TRANSCRIBE_SERVICE_URL = os.getenv("TRANSCRIBE_SERVICE_URL")  # optional
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="Adaptive AI Exam Portal - Prototype")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# In-memory storage (swap to DB later)
# ----------------------------------------------------

class QuestionType(str):
    MCQ = "mcq"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"


class MCQOption(BaseModel):
    text: str
    is_correct: bool = False


class GeneratedQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["mcq", "fill_blank", "short_answer"]
    prompt: str
    options: Optional[List[MCQOption]] = None   # only for MCQ
    answer: Optional[str] = None                # canonical answer
    explanation: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None


class Lecture(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    source_type: Literal["audio", "video", "text"]
    raw_text: str
    summary: Optional[str] = None
    questions: List[GeneratedQuestion] = []


LECTURES: dict[str, Lecture] = {}  # lecture_id -> Lecture


# ----------------------------------------------------
# Service layer – you can reuse your old logic HERE
# ----------------------------------------------------

async def transcribe_audio(file: UploadFile) -> str:
    """
    Transcribe uploaded audio/video into text.

    Option A: call an external transcription service (Whisper, etc.).
    Option B: import and call your local transcription function here.

    For now this is written as:
    - if TRANSCRIBE_SERVICE_URL is set, call that HTTP endpoint.
    - otherwise, raise an error (you’ll fill this in).
    """
    if TRANSCRIBE_SERVICE_URL:
        async with httpx.AsyncClient(timeout=120) as client:
            files = {"file": (file.filename, await file.read(), file.content_type)}
            resp = await client.post(TRANSCRIBE_SERVICE_URL, files=files)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Transcription service error: {resp.text}",
            )
        data = resp.json()
        transcript = data.get("text") or data.get("transcript")
        if not transcript:
            raise HTTPException(status_code=500, detail="No transcript returned.")
        return transcript

    # If you’re not using an external service, replace this with your own code
    raise HTTPException(
        status_code=500,
        detail="Transcription not implemented. Implement transcribe_audio() or set TRANSCRIBE_SERVICE_URL.",
    )


async def summarize_text(text: str) -> str:
    """
    Summarize the lecture text.

    You can:
      - call your own summarization microservice
      - or call OpenAI directly here.
    For now: return a naive trimmed version.
    """
    return text[:1500]


async def generate_questions_from_text(
    text: str,
    num_questions: int = 10,
    mix: dict[str, int] | None = None,
) -> List[GeneratedQuestion]:
    """Use GPT (or your own model) to generate structured questions."""
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY not configured for question generation.",
        )

    mix = mix or {"mcq": int(num_questions * 0.6),
                  "fill_blank": int(num_questions * 0.2),
                  "short_answer": num_questions - int(num_questions * 0.6) - int(num_questions * 0.2)}

    import openai  # type: ignore
    client = openai.OpenAI(api_key=OPENAI_API_KEY)

    system_prompt = (
        "You are an assistant that generates exam questions from lecture text. "
        "Return STRICT JSON with a list of questions. "
        "Each question MUST have: type (mcq|fill_blank|short_answer), "
        "prompt, options (for mcq), answer, explanation, topic, difficulty."
    )

    user_prompt = f"""
Lecture content:
{text[:8000]}

Generate exactly {num_questions} questions using this mix:
- MCQ: {mix['mcq']}
- Fill in the blank: {mix['fill_blank']}
- Short answer: {mix['short_answer']}

Respond in JSON:
{{
  "questions": [
    {{
      "type": "mcq",
      "prompt": "...",
      "options": [{{"text": "...", "is_correct": false}}, ...],
      "answer": "...",
      "explanation": "...",
      "topic": "...",
      "difficulty": "easy|medium|hard"
    }},
    ...
  ]
}}
"""

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )

    content = resp.choices[0].message.content
    import json
    data = json.loads(content)
    questions_raw = data.get("questions", [])

    questions: List[GeneratedQuestion] = []
    for q in questions_raw:
        q_type = q.get("type", "mcq")
        options = None
        if q_type == "mcq":
            options = [MCQOption(**opt) for opt in q.get("options", [])]
        questions.append(
            GeneratedQuestion(
                type=q_type,
                prompt=q.get("prompt", ""),
                options=options,
                answer=q.get("answer"),
                explanation=q.get("explanation"),
                topic=q.get("topic"),
                difficulty=q.get("difficulty"),
            )
        )
    return questions


# ----------------------------------------------------
# API Schemas
# ----------------------------------------------------

class LectureCreateResponse(BaseModel):
    lecture_id: str
    title: str
    source_type: str


class QuestionGenerationRequest(BaseModel):
    num_questions: int = 10
    mcq_ratio: float = 0.6
    fill_blank_ratio: float = 0.2
    short_answer_ratio: float = 0.2


class QuestionGenerationResponse(BaseModel):
    lecture_id: str
    total_questions: int
    questions: List[GeneratedQuestion]


class LectureDetailResponse(BaseModel):
    lecture: Lecture


# ----------------------------------------------------
# Routes
# ----------------------------------------------------

@app.post("/lectures/from-audio", response_model=LectureCreateResponse)
async def create_lecture_from_audio(
    file: UploadFile = File(...),
    title: str = Form("Untitled Lecture"),
):
    """
    1) Upload an audio/video file.
    2) Transcribe to text.
    3) Store lecture with summary.
    """
    transcript = await transcribe_audio(file)
    summary = await summarize_text(transcript)

    lecture = Lecture(
        title=title,
        source_type="audio",
        raw_text=transcript,
        summary=summary,
    )
    LECTURES[lecture.id] = lecture

    return LectureCreateResponse(
        lecture_id=lecture.id,
        title=lecture.title,
        source_type=lecture.source_type,
    )


@app.post("/lectures/from-text", response_model=LectureCreateResponse)
async def create_lecture_from_text(
    title: str,
    content: str,
):
    """If instructor already has lecture notes/slides as text, use this."""
    summary = await summarize_text(content)
    lecture = Lecture(
        title=title,
        source_type="text",
        raw_text=content,
        summary=summary,
    )
    LECTURES[lecture.id] = lecture

    return LectureCreateResponse(
        lecture_id=lecture.id,
        title=lecture.title,
        source_type=lecture.source_type,
    )


@app.post(
    "/lectures/{lecture_id}/generate-questions",
    response_model=QuestionGenerationResponse,
)
async def generate_questions_for_lecture(
    lecture_id: str,
    req: QuestionGenerationRequest,
):
    lecture = LECTURES.get(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    n = req.num_questions
    mcq = int(n * req.mcq_ratio)
    fill_b = int(n * req.fill_blank_ratio)
    short = n - mcq - fill_b
    mix = {"mcq": mcq, "fill_blank": fill_b, "short_answer": short}

    questions = await generate_questions_from_text(
        text=lecture.raw_text,
        num_questions=n,
        mix=mix,
    )
    lecture.questions = questions
    LECTURES[lecture_id] = lecture

    return QuestionGenerationResponse(
        lecture_id=lecture.id,
        total_questions=len(questions),
        questions=questions,
    )


@app.get("/lectures/{lecture_id}", response_model=LectureDetailResponse)
async def get_lecture_detail(lecture_id: str):
    lecture = LECTURES.get(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    return LectureDetailResponse(lecture=lecture)
