import uuid
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


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


class Lecture(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    source_type: Literal["audio", "video", "text"]
    raw_text: str
    summary: Optional[str] = None
    questions: List[GeneratedQuestion] = []
