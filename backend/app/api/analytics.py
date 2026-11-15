from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.chat import _summary
from app.db.database import get_db
from app.db.models import Chat, Document, Message, QuizHistory, utcnow
from app.schemas.schemas import DashboardOut, DocumentOut

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    total_documents = db.scalar(select(func.count()).select_from(Document)) or 0
    total_questions = db.scalar(select(func.count()).select_from(Message).where(Message.role == "user")) or 0
    completed = QuizHistory.completed_at.is_not(None)
    total_quizzes = db.scalar(select(func.count()).select_from(QuizHistory).where(completed)) or 0

    average = None
    rows = db.execute(
        select(QuizHistory.score, QuizHistory.total_questions).where(completed, QuizHistory.total_questions > 0)
    ).all()
    if rows:
        average = round(sum(s / t for s, t in rows) / len(rows) * 100, 1)

    recent_docs = db.scalars(select(Document).order_by(Document.upload_date.desc()).limit(5)).all()
    recent_chats = db.scalars(select(Chat).order_by(Chat.updated_at.desc()).limit(5)).all()

    today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    activity = []
    for offset in range(6, -1, -1):
        start = today - timedelta(days=offset)
        end = start + timedelta(days=1)
        questions = db.scalar(
            select(func.count()).select_from(Message).where(
                Message.role == "user", Message.created_at >= start, Message.created_at < end
            )
        ) or 0
        quizzes = db.scalar(
            select(func.count()).select_from(QuizHistory).where(
                QuizHistory.completed_at >= start, QuizHistory.completed_at < end
            )
        ) or 0
        activity.append({"date": start.strftime("%Y-%m-%d"), "questions": questions, "quizzes": quizzes})

    return DashboardOut(
        total_documents=total_documents,
        total_questions=total_questions,
        total_quizzes_completed=total_quizzes,
        average_quiz_score=average,
        recent_documents=[DocumentOut.model_validate(d) for d in recent_docs],
        recent_chats=[_summary(c) for c in recent_chats],
        activity=activity,
    )
