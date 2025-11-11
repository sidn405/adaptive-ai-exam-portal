from typing import Optional, List, Dict
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from pydantic import BaseModel

from app.models import Lecture, GeneratedQuestion
from app.services.transcription import transcribe_audio
from app.routers import lectures
from app.services.question_generator import summarize_text
from app.app import generate_questions_from_text

# Reuse the in-memory stores from lectures.py
from app.routers.lectures import (
    LECTURES,
    SESSIONS,
    TestSession,
    AnswerRecord,
    select_next_question,
    update_difficulty,
    get_question_by_id,
    normalize_text,
)

app = FastAPI(
    title="Adaptive AI Exam Portal",
    description="An AI-driven examination portal with adaptive testing and proctoring",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    pass  # Optional for API-only

# Include routers - FIXED: Use /api prefix to match frontend
app.include_router(lectures.router, prefix="/api/lectures", tags=["lectures"])


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main landing page."""
    try:
        with open("templates/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Welcome to Adaptive AI Exam Portal</h1><p>API running at /docs</p>")


# -------------------------------------------------------------------
# Additional API endpoints for frontend
# -------------------------------------------------------------------

@app.get("/api/lectures")
def api_list_lectures():
    """List all lectures for the frontend."""
    return [
        {
            "id": lec_id,
            "title": lec.title,
            "summary": lec.summary,
            "source_type": lec.source_type,
            "question_count": len(lec.questions),
        }
        for lec_id, lec in LECTURES.items()
    ]


class ApiTranscribeResponse(BaseModel):
    lecture_id: str
    title: str
    summary: Optional[str]
    transcript: str


@app.post("/api/transcribe", response_model=ApiTranscribeResponse)
async def api_transcribe(
    file: UploadFile = File(...),
    title: str = Form("Untitled Lecture"),
):
    """Transcribe audio/video file."""
    transcript = await transcribe_audio(file)

    lecture = Lecture(
        title=title,
        source_type="audio",
        raw_text=transcript,
        summary=None,
    )
    LECTURES[lecture.id] = lecture

    return ApiTranscribeResponse(
        lecture_id=lecture.id,
        title=lecture.title,
        summary=lecture.summary,
        transcript=transcript,
    )


class StartExamRequest(BaseModel):
    student_id: str
    lecture_id: str


class StartExamResponse(BaseModel):
    session_id: str
    total_questions: int
    first_question: GeneratedQuestion

@app.post("/api/lectures")
async def api_create_lecture(
    title: str = Form(...),
    content: str = Form(...),
):
    """Create lecture and generate questions - WITH ERROR HANDLING."""
    try:
        print(f"Creating lecture: {title}")
        print(f"Content length: {len(content)}")
        
        # Create lecture
        summary = await summarize_text(content)
        lecture = Lecture(
            title=title,
            source_type="text",
            raw_text=content,
            summary=summary,
        )
        LECTURES[lecture.id] = lecture
        print(f"Lecture created with ID: {lecture.id}")
        
        # Generate questions
        num_questions = 10
        mcq = int(num_questions * 0.6)
        fill_b = int(num_questions * 0.2)
        short = num_questions - mcq - fill_b
        mix = {"mcq": mcq, "fill_blank": fill_b, "short_answer": short}
        
        print(f"Generating {num_questions} questions...")
        questions = await generate_questions_from_text(
            text=lecture.raw_text,
            num_questions=num_questions,
            mix=mix
        )
        
        lecture.questions = questions
        LECTURES[lecture.id] = lecture
        
        print(f"Generated {len(questions)} questions successfully")
        
        return {
            "lecture_id": lecture.id,
            "title": lecture.title,
            "total_questions": len(questions),
            "questions": [q.dict() for q in questions],
        }
        
    except Exception as e:
        print(f"ERROR creating lecture: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error creating lecture: {str(e)}")
    
@app.post("/api/exams/start", response_model=StartExamResponse)
async def api_start_exam(req: StartExamRequest):
    """Start an exam session."""
    lecture = LECTURES.get(req.lecture_id)
    if not lecture or not lecture.questions:
        raise HTTPException(
            status_code=400,
            detail="Lecture not found or no questions generated yet.",
        )

    session_id = str(uuid.uuid4())
    session = TestSession(
        id=session_id,
        lecture_id=req.lecture_id,
        learner_id=req.student_id,
    )
    session.current_difficulty = "medium"

    first_q = select_next_question(lecture, session)
    if not first_q:
        raise HTTPException(status_code=400, detail="No questions available.")

    SESSIONS[session_id] = session

    return StartExamResponse(
        session_id=session_id,
        total_questions=len(lecture.questions),
        first_question=first_q,
    )


class SubmitExamAnswerRequest(BaseModel):
    question_id: str
    student_answer: Optional[str] = None
    time_spent: Optional[float] = None


class SubmitExamAnswerResponse(BaseModel):
    result: Dict
    exam_complete: bool
    final_score: Optional[float] = None
    next_question: Optional[GeneratedQuestion] = None


@app.post("/api/exams/{session_id}/answer", response_model=SubmitExamAnswerResponse)
async def api_answer_exam(session_id: str, req: SubmitExamAnswerRequest):
    """Submit an answer."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    lecture = LECTURES.get(session.lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    question = get_question_by_id(lecture, req.question_id)

    # Evaluate correctness
    is_correct = False
    correct_answer_text = question.answer

    if question.type == "mcq":
        chosen = normalize_text(req.student_answer)
        is_correct = any(
            opt.is_correct and normalize_text(opt.text) == chosen
            for opt in (question.options or [])
        )
        for opt in question.options or []:
            if opt.is_correct:
                correct_answer_text = opt.text
                break
    else:
        is_correct = normalize_text(req.student_answer) == normalize_text(question.answer)

    # Update session
    session.total_answered += 1
    if is_correct:
        session.correct_count += 1

    session.answers.append(
        AnswerRecord(
            question_id=question.id,
            is_correct=is_correct,
            learner_answer=req.student_answer,
            difficulty=question.difficulty,
        )
    )

    update_difficulty(session)
    SESSIONS[session.id] = session

    next_q = select_next_question(lecture, session)
    finished = next_q is None
    score = session.correct_count / session.total_answered if session.total_answered else 0.0

    result_payload = {
        "correct": is_correct,
        "correct_answer": correct_answer_text,
        "explanation": question.explanation,
        "score": score,
    }

    return SubmitExamAnswerResponse(
        result=result_payload,
        exam_complete=finished,
        final_score=score if finished else None,
        next_question=next_q,
    )


@app.get("/exam", response_class=HTMLResponse)
async def exam_page():
    """Serve the exam page."""
    try:
        with open("templates/exam.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Exam Page</h1>")


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page():
    """Serve analytics page."""
    try:
        with open("templates/analytics.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Analytics Dashboard</h1>")


@app.get("/results", response_class=HTMLResponse)
async def results_page():
    """Serve results page."""
    try:
        with open("templates/results.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Results Page</h1>")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Adaptive AI Exam Portal is running"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)