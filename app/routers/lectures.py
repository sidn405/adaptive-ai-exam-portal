from typing import List, Optional, Dict
import uuid
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.models import (
    Lecture, GeneratedQuestion, MCQOption,
    LectureCreateResponse, QuestionGenerationRequest, QuestionGenerationResponse,
    SessionStartRequest, SessionStartResponse,
    AnswerQuestionRequest, AnswerQuestionResponse,
    TestSession, AnswerRecord,
    ProctoringEvent, ProctoringReport,
    StudentAnalytics, ClassAnalytics
)
from app.services.transcription import transcribe_audio
from app.services.question_generator import summarize_text, generate_questions_from_text
from app.services.proctoring import ProctoringEngine
from app.services.analytics import AnalyticsEngine

router = APIRouter()

# ============================================================================
# In-memory stores
# ============================================================================

LECTURES: Dict[str, Lecture] = {}
SESSIONS: Dict[str, TestSession] = {}

# Initialize service engines
proctoring_engine = ProctoringEngine()
analytics_engine = AnalyticsEngine()

DIFFICULTY_ORDER = ["easy", "medium", "hard"]


# ============================================================================
# Helper Functions (Your existing logic)
# ============================================================================

def get_question_by_id(lecture: Lecture, question_id: str) -> GeneratedQuestion:
    for q in lecture.questions:
        if q.id == question_id:
            return q
    raise HTTPException(status_code=404, detail="Question not found in lecture.")


def question_already_answered(session: TestSession, question_id: str) -> bool:
    return any(a.question_id == question_id for a in session.answers)


def select_next_question(lecture: Lecture, session: TestSession) -> Optional[GeneratedQuestion]:
    """
    Simple adaptive selection:
    - Prefer questions with session.current_difficulty that haven't been answered.
    - If none left at that difficulty, fall back to any unanswered question.
    - If all answered, return None.
    """
    # 1) try same difficulty
    candidates = [
        q for q in lecture.questions
        if q.difficulty == session.current_difficulty
        and not question_already_answered(session, q.id)
    ]
    if candidates:
        return candidates[0]

    # 2) any unanswered
    remaining = [
        q for q in lecture.questions
        if not question_already_answered(session, q.id)
    ]
    if remaining:
        return remaining[0]

    # 3) no questions left
    return None


def update_difficulty(session: TestSession) -> None:
    """
    Look at last 3 answers:
    - accuracy >= 0.8 -> move up a level (easy -> medium -> hard)
    - accuracy <= 0.5 -> move down a level (hard -> medium -> easy)
    """
    if not session.answers:
        return

    window = session.answers[-3:]
    correct = sum(1 for a in window if a.is_correct)
    accuracy = correct / len(window)

    current_idx = DIFFICULTY_ORDER.index(session.current_difficulty) \
        if session.current_difficulty in DIFFICULTY_ORDER else 1

    if accuracy >= 0.8 and current_idx < len(DIFFICULTY_ORDER) - 1:
        session.current_difficulty = DIFFICULTY_ORDER[current_idx + 1]
    elif accuracy <= 0.5 and current_idx > 0:
        session.current_difficulty = DIFFICULTY_ORDER[current_idx - 1]


def normalize_text(s: Optional[str]) -> str:
    return (s or "").strip().lower()


# ============================================================================
# Lecture Creation & Question Generation (Your existing endpoints)
# ============================================================================

@router.post("/from-audio", response_model=LectureCreateResponse)
async def create_lecture_from_audio(
    file: UploadFile = File(...),
    title: str = Form("Untitled Lecture"),
):
    """Create lecture from audio file with transcription."""
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


@router.post("/from-text", response_model=LectureCreateResponse)
async def create_lecture_from_text(
    title: str,
    content: str,
):
    """Create lecture from text content."""
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

@router.post("/transcribe")
async def transcribe_endpoint(file: UploadFile):
    text = await transcribe_audio(file)
    return {"text": text}

@router.post("/{lecture_id}/generate-questions", response_model=QuestionGenerationResponse)
async def generate_questions_for_lecture(lecture_id: str, req: QuestionGenerationRequest):
    """Generate questions for a lecture using AI."""
    lecture = LECTURES.get(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    n = req.num_questions
    mcq = int(n * req.mcq_ratio)
    fill_b = int(n * req.fill_blank_ratio)
    short = n - mcq - fill_b
    mix = {"mcq": mcq, "fill_blank": fill_b, "short_answer": short}

    questions = await generate_questions_from_text(
        text=lecture.raw_text, num_questions=n, mix=mix
    )
    lecture.questions = questions
    LECTURES[lecture_id] = lecture

    return QuestionGenerationResponse(
        lecture_id=lecture.id,
        total_questions=len(questions),
        questions=questions,
    )


@router.get("", response_model=List[LectureCreateResponse])
async def list_lectures():
    """List all available lectures."""
    return [
        LectureCreateResponse(
            lecture_id=lecture.id,
            title=lecture.title,
            source_type=lecture.source_type,
        )
        for lecture in LECTURES.values()
    ]


@router.get("/{lecture_id}")
async def get_lecture(lecture_id: str):
    """Get lecture details including all questions."""
    lecture = LECTURES.get(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    return lecture


# ============================================================================
# Adaptive Test Sessions (Your existing logic + proctoring integration)
# ============================================================================

@router.post("/{lecture_id}/start-session", response_model=SessionStartResponse)
async def start_session(lecture_id: str, req: SessionStartRequest):
    """Start a new adaptive test session with proctoring."""
    lecture = LECTURES.get(lecture_id)
    if not lecture or not lecture.questions:
        raise HTTPException(
            status_code=400,
            detail="Lecture not found or no questions generated yet.",
        )

    session_id = str(uuid.uuid4())
    session = TestSession(
        id=session_id,
        lecture_id=lecture_id,
        learner_id=req.learner_id,
        current_difficulty="medium",
    )

    first_q = select_next_question(lecture, session)
    if not first_q:
        raise HTTPException(status_code=400, detail="No questions available.")

    SESSIONS[session_id] = session

    # Initialize proctoring for this session
    proctoring_engine.start_proctoring_session(session_id)

    return SessionStartResponse(
        session_id=session_id,
        lecture_id=lecture_id,
        learner_id=req.learner_id,
        question=first_q,
    )


@router.post("/{lecture_id}/answer", response_model=AnswerQuestionResponse)
async def answer_question(lecture_id: str, req: AnswerQuestionRequest):
    """Submit answer and get next question with adaptive difficulty."""
    lecture = LECTURES.get(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    session = SESSIONS.get(req.session_id)
    if not session or session.lecture_id != lecture_id:
        raise HTTPException(status_code=404, detail="Session not found for this lecture.")

    question = get_question_by_id(lecture, req.question_id)

    # ========== Evaluate correctness ==========
    is_correct = False
    correct_answer_text: Optional[str] = question.answer

    if question.type == "mcq":
        if req.selected_option_index is None:
            raise HTTPException(
                status_code=400,
                detail="selected_option_index is required for MCQ questions.",
            )
        if (
            req.selected_option_index < 0
            or req.selected_option_index >= len(question.options or [])
        ):
            raise HTTPException(
                status_code=400,
                detail="selected_option_index is out of range.",
            )
        is_correct = question.options[req.selected_option_index].is_correct
        # Get correct option text for display
        for opt in question.options or []:
            if opt.is_correct:
                correct_answer_text = opt.text
                break
    else:
        # Simple string comparison for fill_blank and short_answer
        is_correct = (
            normalize_text(req.learner_answer) == normalize_text(question.answer)
        )

    # ========== Update session stats ==========
    session.total_answered += 1
    if is_correct:
        session.correct_count += 1

    session.answers.append(
        AnswerRecord(
            question_id=question.id,
            is_correct=is_correct,
            learner_answer=req.learner_answer,
            selected_option_index=req.selected_option_index,
            difficulty=question.difficulty,
            time_spent=req.time_spent,
        )
    )

    # ========== Adaptive difficulty adjustment ==========
    update_difficulty(session)

    # ========== Select next question ==========
    next_q = select_next_question(lecture, session)
    finished = next_q is None
    
    # Calculate score
    score = session.correct_count / session.total_answered if session.total_answered else 0.0

    # ========== Handle session completion ==========
    if finished:
        session.completed_at = datetime.now()
        
        # Record analytics
        if session.learner_id:
            analytics_engine.record_session(session, lecture)

    # Save session
    SESSIONS[session.id] = session

    return AnswerQuestionResponse(
        correct=is_correct,
        correct_answer=correct_answer_text,
        explanation=question.explanation,
        finished=finished,
        score=score,
        next_question=next_q,
        current_difficulty=session.current_difficulty,
    )


# ============================================================================
# Proctoring Endpoints (New additions)
# ============================================================================

@router.post("/proctoring/{session_id}/event")
async def log_proctoring_event(session_id: str, event: ProctoringEvent):
    """Log a proctoring event during the exam."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    result = proctoring_engine.log_proctoring_event(event)
    
    # Add to session flags
    session.proctoring_flags.append({
        "type": event.event_type,
        "timestamp": event.timestamp.isoformat(),
        "confidence": event.confidence,
    })
    SESSIONS[session_id] = session
    
    return result


@router.get("/proctoring/{session_id}/report", response_model=ProctoringReport)
async def get_proctoring_report(session_id: str):
    """Get comprehensive proctoring report for a session."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    report = proctoring_engine.get_proctoring_report(session_id)
    return report


# ============================================================================
# Analytics Endpoints (New additions)
# ============================================================================

@router.get("/analytics/student/{student_id}", response_model=StudentAnalytics)
async def get_student_analytics(student_id: str):
    """Get comprehensive analytics for a specific student."""
    analytics = analytics_engine.get_student_analytics(student_id)
    
    return StudentAnalytics(
        student_id=analytics.student_id,
        total_exams=analytics.total_exams,
        average_score=analytics.average_score,
        time_per_question=analytics.time_per_question,
        difficulty_performance=analytics.difficulty_performance,
        topic_performance=analytics.topic_performance,
        improvement_trend=analytics.improvement_trend,
        recent_sessions=[]
    )


@router.get("/analytics/class/overview", response_model=ClassAnalytics)
async def get_class_analytics():
    """Get class-wide analytics and statistics."""
    analytics = analytics_engine.get_class_analytics()
    return ClassAnalytics(
        total_students=analytics["total_students"],
        total_exams=analytics["total_exams"],
        average_score=analytics["average_score"],
        top_performers=analytics["top_performers"],
        common_weak_topics=analytics["common_weak_topics"],
    )


# ============================================================================
# Results & Session Info
# ============================================================================

@router.get("/results/{session_id}")
async def get_exam_results(session_id: str):
    """Get detailed results for a completed exam session."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    if not session.completed_at:
        raise HTTPException(status_code=400, detail="Exam not yet completed.")
    
    lecture = LECTURES.get(session.lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    
    # Build detailed results
    results = []
    for answer in session.answers:
        question = get_question_by_id(lecture, answer.question_id)
        results.append({
            "question": question.prompt,
            "your_answer": answer.learner_answer or f"Option {answer.selected_option_index}",
            "correct_answer": question.answer,
            "is_correct": answer.is_correct,
            "explanation": question.explanation,
            "difficulty": question.difficulty,
        })
    
    # Get proctoring report
    proctoring_report = proctoring_engine.get_proctoring_report(session_id)
    
    score_percentage = (session.correct_count / session.total_answered * 100) if session.total_answered else 0
    
    return {
        "session_id": session_id,
        "learner_id": session.learner_id,
        "lecture_id": session.lecture_id,
        "lecture_title": lecture.title,
        "score": score_percentage,
        "correct": session.correct_count,
        "total": session.total_answered,
        "results": results,
        "proctoring": proctoring_report,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }
    
@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get current session information and progress."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    lecture = LECTURES.get(session.lecture_id)
    
    return {
        "session_id": session.id,
        "lecture_id": session.lecture_id,
        "lecture_title": lecture.title if lecture else "Unknown",
        "learner_id": session.learner_id,
        "current_difficulty": session.current_difficulty,
        "progress": f"{session.total_answered}/{len(lecture.questions) if lecture else 0}",
        "score": (session.correct_count / session.total_answered) if session.total_answered else 0,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }
