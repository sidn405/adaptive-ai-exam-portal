import uuid
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# Question Models (Your existing models + enhancements)
# ============================================================================

class MCQOption(BaseModel):
    text: str
    is_correct: bool = False


class GeneratedQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["mcq", "fill_blank", "short_answer"]
    prompt: str
    options: Optional[List[MCQOption]] = None
    answer: Optional[str] = None
    explanation: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None


# ============================================================================
# Lecture Models
# ============================================================================

class Lecture(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    source_type: Literal["audio", "video", "text"]
    raw_text: str
    summary: Optional[str] = None
    questions: List[GeneratedQuestion] = []
    created_at: Optional[datetime] = Field(default_factory=datetime.now)


# ============================================================================
# Test Session & Answer Models (Your existing models)
# ============================================================================

class AnswerRecord(BaseModel):
    question_id: str
    is_correct: bool
    learner_answer: Optional[str] = None
    selected_option_index: Optional[int] = None
    difficulty: Optional[str] = None
    time_spent: Optional[int] = None  # seconds


class TestSession(BaseModel):
    id: str
    lecture_id: str
    learner_id: Optional[str] = None
    current_difficulty: str = "medium"
    answers: List[AnswerRecord] = []
    correct_count: int = 0
    total_answered: int = 0
    started_at: Optional[datetime] = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    proctoring_flags: List[Dict[str, Any]] = []


# ============================================================================
# Proctoring Models (New additions)
# ============================================================================

class ProctoringEvent(BaseModel):
    session_id: str
    event_type: str  # "tab_switch", "face_not_detected", "multiple_faces", "suspicious_object"
    timestamp: datetime = Field(default_factory=datetime.now)
    confidence: float
    details: Optional[Dict[str, Any]] = None

    def __init__(self, **data):
        if not data.get("timestamp"):
            from datetime import datetime
            data["timestamp"] = datetime.now().isoformat()
        super().__init__(**data)
        
class ProctoringReport(BaseModel):
    session_id: str
    duration: int  # seconds
    risk_level: str  # "low", "medium", "high"
    integrity_score: int  # 0-100
    event_summary: Dict[str, int]
    total_events: int
    flags: Dict[str, int]
    recommendations: List[str]


# ============================================================================
# Analytics Models (New additions)
# ============================================================================

class StudentAnalytics(BaseModel):
    student_id: str
    total_exams: int
    average_score: float
    time_per_question: float
    difficulty_performance: Dict[str, float]  # easy/medium/hard -> percentage
    topic_performance: Dict[str, float]  # topic -> percentage
    improvement_trend: List[float]
    recent_sessions: List[str]  # session IDs


class ClassAnalytics(BaseModel):
    total_students: int
    total_exams: int
    average_score: float
    top_performers: List[Dict[str, Any]]
    common_weak_topics: List[Dict[str, Any]]


# ============================================================================
# Request/Response Schemas
# ============================================================================

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
    time_spent: Optional[int] = None


class AnswerQuestionResponse(BaseModel):
    correct: bool
    correct_answer: Optional[str]
    explanation: Optional[str]
    finished: bool
    score: float
    next_question: Optional[GeneratedQuestion] = None
    current_difficulty: Optional[str] = None