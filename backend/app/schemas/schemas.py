"""Pydantic models: request validation and response shapes."""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------- documents
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    upload_date: datetime
    processing_status: Literal["processing", "ready", "failed"]
    page_count: Optional[int] = None
    file_size: int
    chunk_count: int = 0
    error_message: Optional[str] = None


# --------------------------------------------------------------------- chat
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    chat_id: Optional[str] = None
    document_ids: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("question")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Question must not be empty.")
        return v


class SourceOut(BaseModel):
    document_id: str
    filename: str
    page_number: int
    excerpt: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    chat_id: str
    sources: List[SourceOut]
    info: Dict[str, Any]


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    sources: List[SourceOut] = Field(default_factory=list)
    created_at: datetime


class ChatSummaryOut(BaseModel):
    id: str
    title: str
    document_ids: List[str]
    message_count: int
    created_at: datetime
    updated_at: datetime


class ChatDetailOut(ChatSummaryOut):
    messages: List[MessageOut]


# ---------------------------------------------------------------- summaries
class SummarizeRequest(BaseModel):
    document_id: str
    mode: Literal["short", "detailed"] = "short"


class DefinitionOut(BaseModel):
    term: str
    definition: str


class SummaryOut(BaseModel):
    document_id: str
    mode: str
    summary: str
    key_concepts: List[str]
    definitions: List[DefinitionOut]
    exam_notes: List[str]
    sections_total: int
    sections_used: int


# --------------------------------------------------------------------- quiz
class GeneratedQuestion(BaseModel):
    """Validates ONE question produced by the language model. Malformed ones are rejected."""

    question: str = Field(min_length=8)
    options: List[str]
    correct_index: int
    explanation: str = Field(min_length=3)

    @model_validator(mode="before")
    @classmethod
    def _normalise(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        options = data.get("options")
        if "correct_index" not in data and isinstance(options, list):
            answer = data.get("answer", data.get("correct_answer"))
            if isinstance(answer, int):
                data["correct_index"] = answer
            elif isinstance(answer, str):
                a = answer.strip()
                if len(a) == 1 and a.upper() in "ABCD":
                    data["correct_index"] = "ABCD".index(a.upper())
                else:
                    for i, opt in enumerate(options):
                        if isinstance(opt, str) and opt.strip().lower() == a.lower():
                            data["correct_index"] = i
        return data

    @field_validator("options")
    @classmethod
    def _four_unique(cls, v: List[str]) -> List[str]:
        v = [str(o).strip() for o in v]
        if len(v) != 4 or any(not o for o in v):
            raise ValueError("A question needs exactly four non-empty options.")
        if len({o.lower() for o in v}) != 4:
            raise ValueError("Options must be different from each other.")
        return v

    @field_validator("correct_index")
    @classmethod
    def _in_range(cls, v: int) -> int:
        if v not in (0, 1, 2, 3):
            raise ValueError("correct_index must be 0-3.")
        return v


class QuizGenerateRequest(BaseModel):
    document_id: str
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    num_questions: int = Field(default=5, ge=1, le=20)


class QuizQuestionOut(BaseModel):
    """What the browser sees BEFORE submitting: no correct answer, no explanation."""

    question: str
    options: List[str]


class QuizOut(BaseModel):
    quiz_id: str
    document_id: str
    difficulty: str
    questions: List[QuizQuestionOut]
    warning: Optional[str] = None


class QuizSubmitRequest(BaseModel):
    quiz_id: str
    answers: List[Optional[int]]


class QuizQuestionResult(BaseModel):
    question: str
    options: List[str]
    selected: Optional[int]
    correct_index: int
    correct: bool
    explanation: str


class QuizResultOut(BaseModel):
    quiz_id: str  # id of the attempt that was stored (new id when retaking)
    score: int
    total: int
    results: List[QuizQuestionResult]


class QuizHistoryOut(BaseModel):
    id: str
    document_id: str
    document_name: Optional[str] = None
    difficulty: str
    score: int
    total_questions: int
    completed_at: datetime


# ---------------------------------------------------------------- flashcards
class GeneratedCard(BaseModel):
    question: str = Field(min_length=5)
    answer: str = Field(min_length=2)
    key_concept: str = Field(default="", max_length=120)


class FlashcardOut(BaseModel):
    question: str
    answer: str
    key_concept: str
    source_page: Optional[int] = None


class FlashcardGenerateRequest(BaseModel):
    document_id: str
    num_cards: int = Field(default=10, ge=1, le=30)


class FlashcardSetOut(BaseModel):
    id: str
    document_id: str
    title: str
    cards: List[FlashcardOut]
    progress: Dict[str, Literal["known", "revise"]]
    created_at: datetime


class FlashcardProgressRequest(BaseModel):
    progress: Dict[str, Literal["known", "revise"]]


# ---------------------------------------------------------------- analytics
class ActivityDay(BaseModel):
    date: str
    questions: int
    quizzes: int


class DashboardOut(BaseModel):
    total_documents: int
    total_questions: int
    total_quizzes_completed: int
    average_quiz_score: Optional[float] = None
    recent_documents: List[DocumentOut]
    recent_chats: List[ChatSummaryOut]
    activity: List[ActivityDay]
