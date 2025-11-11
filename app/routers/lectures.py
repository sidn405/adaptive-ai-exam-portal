from typing import List, Optional, Dict
import uuid

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from app.models import Lecture, GeneratedQuestion
from app.services.transcription import transcribe_audio
from app.services.question_generator import summarize_text, generate_questions_from_text

router = APIRouter()

# -------------------------------------------------------------------
# In-memory stores
# -------------------------------------------------------------------

LECTURES: Dict[str, Lecture] = {}


class AnswerRecord(BaseModel):
    question_id: str
    is_correct: bool
    learner_answer: Optional[str] = None
    selected_option_index: Optional[int] = None
    difficulty: Optional[str] = None


class TestSession(BaseModel):
    id: str
    lecture_id: str
    learner_id: Optional[str] = None
    current_difficulty: str = "medium"
    answers: List[AnswerRecord] = []
    correct_count: int = 0
    total_answered: int = 0


SESSIONS: Dict[str, TestSession] = {}


DIFFICULTY_ORDER = ["easy", "medium", "hard"]


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

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


# -------------------------------------------------------------------
# Schemas
# -------------------------------------------------------------------

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


class SessionStartRequest(BaseModel):
    learner_id: Optional[str] = None


class SessionStartResponse(BaseModel):
    session_id: str
    lecture_id: str
    learner_id: Optional[str]
    question: GeneratedQuestion


class AnswerQuestionRequest(BaseModel):
    session_id: str
    question_id: str
    learner_answer: Optional[str] = None
    selected_option_index: Optional[int] = None


class AnswerQuestionResponse(BaseModel):
    correct: bool
    correct_answer: Optional[str]
    explanation: Optional[str]
    finished: bool
    score: float
    next_question: Optional[GeneratedQuestion] = None


# -------------------------------------------------------------------
# Lecture creation & question generation
# -------------------------------------------------------------------

@router.post("/from-audio", response_model=LectureCreateResponse)
async def create_lecture_from_audio(
    file: UploadFile = File(...),
    title: str = Form("Untitled Lecture"),
):
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


@router.post("/{lecture_id}/generate-questions", response_model=QuestionGenerationResponse)
async def generate_questions_for_lecture(lecture_id: str, req: QuestionGenerationRequest):
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


# -------------------------------------------------------------------
# Adaptive test sessions
# -------------------------------------------------------------------

@router.post("/{lecture_id}/start-session", response_model=SessionStartResponse)
async def start_session(lecture_id: str, req: SessionStartRequest):
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
    )
    # start at 'medium' difficulty by default (update_difficulty will adjust)
    session.current_difficulty = "medium"

    first_q = select_next_question(lecture, session)
    if not first_q:
        raise HTTPException(status_code=400, detail="No questions available.")

    SESSIONS[session_id] = session

    return SessionStartResponse(
        session_id=session_id,
        lecture_id=lecture_id,
        learner_id=req.learner_id,
        question=first_q,
    )


@router.post("/{lecture_id}/answer", response_model=AnswerQuestionResponse)
async def answer_question(lecture_id: str, req: AnswerQuestionRequest):
    lecture = LECTURES.get(lecture_id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found.")

    session = SESSIONS.get(req.session_id)
    if not session or session.lecture_id != lecture_id:
        raise HTTPException(status_code=404, detail="Session not found for this lecture.")

    question = get_question_by_id(lecture, req.question_id)

    # --- evaluate correctness ---
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
        # override with the correct option's text for display
        for opt in question.options or []:
            if opt.is_correct:
                correct_answer_text = opt.text
                break
    else:
        # simple string comparison for now; later you can add NLP similarity
        is_correct = (
            normalize_text(req.learner_answer) == normalize_text(question.answer)
        )

    # --- update session stats ---
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
        )
    )

    # adapt difficulty for next question
    update_difficulty(session)

    # pick next question
    next_q = select_next_question(lecture, session)
    finished = next_q is None
    score = session.correct_count / session.total_answered if session.total_answered else 0.0

    # save session back
    SESSIONS[session.id] = session

    return AnswerQuestionResponse(
        correct=is_correct,
        correct_answer=correct_answer_text,
        explanation=question.explanation,
        finished=finished,
        score=score,
        next_question=next_q,
    )
