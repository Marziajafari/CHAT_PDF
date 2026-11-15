import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_ready_documents
from app.db.database import get_db
from app.db.models import Document, FlashcardSet, QuizHistory, utcnow
from app.schemas.schemas import (
    FlashcardGenerateRequest,
    FlashcardProgressRequest,
    FlashcardSetOut,
    QuizGenerateRequest,
    QuizHistoryOut,
    QuizOut,
    QuizQuestionResult,
    QuizResultOut,
    QuizSubmitRequest,
    SummarizeRequest,
    SummaryOut,
)
from app.services import ai_tasks, pdf_service, vector_store
from pathlib import Path

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ------------------------------------------------------------------ summaries
@router.post("/summarize", response_model=SummaryOut)
def summarize(req: SummarizeRequest, db: Session = Depends(get_db)):
    doc = get_ready_documents(db, [req.document_id])[0]
    pages = pdf_service.extract_pages(Path(doc.file_path))
    result = ai_tasks.summarize(pages, req.mode)
    return SummaryOut(document_id=doc.id, mode=req.mode, **result)


# ----------------------------------------------------------------------- quiz
@router.post("/generate-quiz", response_model=QuizOut)
def generate_quiz(req: QuizGenerateRequest, db: Session = Depends(get_db)):
    doc = get_ready_documents(db, [req.document_id])[0]
    chunks = vector_store.get_document_chunks(doc.id)
    result = ai_tasks.generate_quiz(chunks, req.difficulty, req.num_questions)
    quiz = QuizHistory(
        document_id=doc.id,
        difficulty=req.difficulty,
        total_questions=len(result["questions"]),
        questions_json=json.dumps(result["questions"]),
    )
    db.add(quiz)
    db.commit()
    return QuizOut(
        quiz_id=quiz.id,
        document_id=doc.id,
        difficulty=req.difficulty,
        # correct answers and explanations stay on the server until the quiz is submitted
        questions=[{"question": q["question"], "options": q["options"]} for q in result["questions"]],
        warning=result["warning"],
    )


@router.post("/submit-quiz", response_model=QuizResultOut)
def submit_quiz(req: QuizSubmitRequest, db: Session = Depends(get_db)):
    quiz = db.get(QuizHistory, req.quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found.")
    questions = json.loads(quiz.questions_json)
    if len(req.answers) != len(questions):
        raise HTTPException(status_code=422, detail=f"Expected {len(questions)} answers, got {len(req.answers)}.")
    for a in req.answers:
        if a is not None and a not in (0, 1, 2, 3):
            raise HTTPException(status_code=422, detail="Answers must be option numbers 0-3 (or null).")

    if quiz.completed_at is not None:
        # Retaking the same questions: store it as a new attempt so history stays accurate.
        quiz = QuizHistory(
            document_id=quiz.document_id,
            difficulty=quiz.difficulty,
            total_questions=quiz.total_questions,
            questions_json=quiz.questions_json,
        )
        db.add(quiz)

    results: List[QuizQuestionResult] = []
    score = 0
    for q, selected in zip(questions, req.answers):
        correct = selected == q["correct_index"]
        score += int(correct)
        results.append(
            QuizQuestionResult(
                question=q["question"],
                options=q["options"],
                selected=selected,
                correct_index=q["correct_index"],
                correct=correct,
                explanation=q["explanation"],
            )
        )
    quiz.score = score
    quiz.answers_json = json.dumps(req.answers)
    quiz.completed_at = utcnow()
    db.commit()
    return QuizResultOut(quiz_id=quiz.id, score=score, total=len(questions), results=results)


@router.get("/quiz-history", response_model=List[QuizHistoryOut])
def quiz_history(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(QuizHistory).where(QuizHistory.completed_at.is_not(None)).order_by(QuizHistory.completed_at.desc()).limit(30)
    ).all()
    names = {d.id: d.original_filename for d in db.scalars(select(Document)).all()}
    return [
        QuizHistoryOut(
            id=r.id,
            document_id=r.document_id,
            document_name=names.get(r.document_id),
            difficulty=r.difficulty,
            score=r.score or 0,
            total_questions=r.total_questions,
            completed_at=r.completed_at,
        )
        for r in rows
    ]


# ------------------------------------------------------------------ flashcards
def _set_out(fs: FlashcardSet) -> FlashcardSetOut:
    return FlashcardSetOut(
        id=fs.id,
        document_id=fs.document_id,
        title=fs.title,
        cards=json.loads(fs.cards_json),
        progress=json.loads(fs.progress_json or "{}"),
        created_at=fs.created_at,
    )


@router.post("/generate-flashcards", response_model=FlashcardSetOut)
def generate_flashcards(req: FlashcardGenerateRequest, db: Session = Depends(get_db)):
    doc = get_ready_documents(db, [req.document_id])[0]
    chunks = vector_store.get_document_chunks(doc.id)
    cards = ai_tasks.generate_flashcards(chunks, req.num_cards)
    fs = FlashcardSet(
        document_id=doc.id,
        title=f"{doc.original_filename} ({len(cards)} cards)"[:200],
        cards_json=json.dumps(cards),
        progress_json="{}",
    )
    db.add(fs)
    db.commit()
    return _set_out(fs)


@router.get("/flashcard-sets", response_model=List[FlashcardSetOut])
def list_flashcard_sets(db: Session = Depends(get_db)):
    sets = db.scalars(select(FlashcardSet).order_by(FlashcardSet.created_at.desc()).limit(30)).all()
    return [_set_out(s) for s in sets]


@router.patch("/flashcard-sets/{set_id}/progress", response_model=FlashcardSetOut)
def save_progress(set_id: str, req: FlashcardProgressRequest, db: Session = Depends(get_db)):
    fs = db.get(FlashcardSet, set_id)
    if fs is None:
        raise HTTPException(status_code=404, detail="Flashcard set not found.")
    total = len(json.loads(fs.cards_json))
    for key in req.progress:
        if not key.isdigit() or int(key) >= total:
            raise HTTPException(status_code=422, detail="Progress refers to a card that does not exist.")
    fs.progress_json = json.dumps(req.progress)
    db.commit()
    return _set_out(fs)
