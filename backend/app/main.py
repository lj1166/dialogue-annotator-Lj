import csv
import io
import json
import logging
from datetime import datetime

from app.logging_config import setup_logging

setup_logging()
logger = logging.getLogger("app.api")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.models import (
    AiSuggestRequest,
    AiSuggestResponse,
    Annotation,
    AnnotationSave,
    Conversation,
    ConversationSummary,
    StatsResponse,
)
from app.services.ollama import coerce_bool, suggest_labels
from app.store import (
    annotation_key,
    assistant_turn_indices,
    load_annotations,
    load_conversations,
    save_annotations,
)

app = FastAPI(title="对话质量标注工具", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_conversations: list[Conversation] = []
_annotations: dict[str, Annotation] = {}


def _is_complete(annotation: Annotation | None) -> bool:
    if annotation is None:
        return False
    return (
        annotation.accurate is not None
        and annotation.off_topic is not None
        and annotation.fabricated is not None
    )


def _reload() -> None:
    global _conversations, _annotations
    _conversations = load_conversations()
    _annotations = load_annotations()


@app.on_event("startup")
def startup() -> None:
    _reload()


_reload()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/conversations", response_model=list[ConversationSummary])
def list_conversations() -> list[ConversationSummary]:
    summaries: list[ConversationSummary] = []
    for conv in _conversations:
        indices = assistant_turn_indices(conv)
        annotated = sum(
            1
            for idx in indices
            if _is_complete(_annotations.get(annotation_key(conv.id, idx)))
        )
        preview = next((t.content for t in conv.turns if t.role == "user"), "")
        summaries.append(
            ConversationSummary(
                id=conv.id,
                preview=preview[:40] + ("…" if len(preview) > 40 else ""),
                assistant_turns=len(indices),
                annotated_turns=annotated,
                fully_annotated=annotated == len(indices) and len(indices) > 0,
            )
        )
    return summaries


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
def get_conversation(conversation_id: str) -> Conversation:
    for conv in _conversations:
        if conv.id == conversation_id:
            return conv
    raise HTTPException(status_code=404, detail="对话不存在")


@app.get("/api/annotations")
def get_all_annotations() -> dict[str, Annotation]:
    return _annotations


@app.get("/api/annotations/{conversation_id}/{turn_index}", response_model=Annotation | None)
def get_annotation(conversation_id: str, turn_index: int) -> Annotation | None:
    return _annotations.get(annotation_key(conversation_id, turn_index))


@app.put("/api/annotations", response_model=Annotation)
def save_annotation(body: AnnotationSave) -> Annotation:
    conv = next((c for c in _conversations if c.id == body.conversation_id), None)
    if conv is None:
        raise HTTPException(status_code=404, detail="对话不存在")
    if body.turn_index < 0 or body.turn_index >= len(conv.turns):
        raise HTTPException(status_code=400, detail="turn_index 无效")
    if conv.turns[body.turn_index].role != "assistant":
        raise HTTPException(status_code=400, detail="只能标注 assistant 回复")

    key = annotation_key(body.conversation_id, body.turn_index)
    existing = _annotations.get(key)
    annotation = Annotation(
        conversation_id=body.conversation_id,
        turn_index=body.turn_index,
        accurate=body.accurate,
        off_topic=body.off_topic,
        fabricated=body.fabricated,
        note=body.note,
        ai_reason=existing.ai_reason if existing else "",
        updated_at=datetime.utcnow().isoformat() + "Z",
    )
    _annotations[key] = annotation
    save_annotations(_annotations)
    return annotation


@app.get("/api/stats", response_model=StatsResponse)
def get_stats() -> StatsResponse:
    total_assistant = 0
    annotated = 0
    accurate_count = inaccurate_count = 0
    off_topic_count = on_topic_count = 0
    fabricated_count = not_fabricated_count = 0

    for conv in _conversations:
        for idx in assistant_turn_indices(conv):
            total_assistant += 1
            ann = _annotations.get(annotation_key(conv.id, idx))
            if not _is_complete(ann):
                continue
            annotated += 1
            if ann.accurate:
                accurate_count += 1
            else:
                inaccurate_count += 1
            if ann.off_topic:
                off_topic_count += 1
            else:
                on_topic_count += 1
            if ann.fabricated:
                fabricated_count += 1
            else:
                not_fabricated_count += 1

    progress = (annotated / total_assistant * 100) if total_assistant else 0.0
    return StatsResponse(
        total_conversations=len(_conversations),
        total_assistant_turns=total_assistant,
        annotated_turns=annotated,
        progress_percent=round(progress, 1),
        accurate_count=accurate_count,
        inaccurate_count=inaccurate_count,
        off_topic_count=off_topic_count,
        on_topic_count=on_topic_count,
        fabricated_count=fabricated_count,
        not_fabricated_count=not_fabricated_count,
    )


@app.post("/api/ai/suggest", response_model=AiSuggestResponse)
async def ai_suggest(body: AiSuggestRequest) -> AiSuggestResponse:
    conv = next((c for c in _conversations if c.id == body.conversation_id), None)
    if conv is None:
        raise HTTPException(status_code=404, detail="对话不存在")
    if body.turn_index < 0 or body.turn_index >= len(conv.turns):
        raise HTTPException(status_code=400, detail="turn_index 无效")
    if conv.turns[body.turn_index].role != "assistant":
        raise HTTPException(status_code=400, detail="只能对 assistant 回复建议标注")

    user_content = ""
    for turn in conv.turns[: body.turn_index]:
        if turn.role == "user":
            user_content = turn.content
    assistant_content = conv.turns[body.turn_index].content

    logger.info(
        "[API] /ai/suggest 对话=%s turn=%s",
        body.conversation_id,
        body.turn_index,
    )

    parsed, err = await suggest_labels(user_content, assistant_content)
    if parsed is None:
        logger.warning("[API] AI 建议失败: %s", err)
        return AiSuggestResponse(
            accurate=None,
            off_topic=None,
            fabricated=None,
            reason="",
            available=False,
            message=err,
        )

    accurate = coerce_bool(parsed.get("accurate"))
    off_topic = coerce_bool(parsed.get("off_topic"))
    fabricated = coerce_bool(parsed.get("fabricated"))
    reason = str(parsed.get("reason", ""))

    if accurate is None and off_topic is None and fabricated is None:
        return AiSuggestResponse(
            accurate=None,
            off_topic=None,
            fabricated=None,
            reason=reason,
            available=False,
            message="模型返回了无法识别的标签格式，请手动标注",
        )

    key = annotation_key(body.conversation_id, body.turn_index)
    existing = _annotations.get(key)
    if existing:
        existing.ai_reason = reason
        if accurate is not None:
            existing.accurate = accurate
        if off_topic is not None:
            existing.off_topic = off_topic
        if fabricated is not None:
            existing.fabricated = fabricated
    else:
        _annotations[key] = Annotation(
            conversation_id=body.conversation_id,
            turn_index=body.turn_index,
            accurate=accurate,
            off_topic=off_topic,
            fabricated=fabricated,
            ai_reason=reason,
        )
    save_annotations(_annotations)

    result = AiSuggestResponse(
        accurate=accurate,
        off_topic=off_topic,
        fabricated=fabricated,
        reason=reason,
        available=True,
        message="AI 建议仅供参考，请确认后保存",
    )
    logger.info(
        "[API] AI 建议返回: accurate=%s off_topic=%s fabricated=%s reason=%s",
        accurate,
        off_topic,
        fabricated,
        reason,
    )
    return result


def _build_export() -> list[dict]:
    rows: list[dict] = []
    for conv in _conversations:
        for idx in assistant_turn_indices(conv):
            ann = _annotations.get(annotation_key(conv.id, idx))
            user_content = ""
            for turn in conv.turns[:idx]:
                if turn.role == "user":
                    user_content = turn.content
            rows.append(
                {
                    "conversation_id": conv.id,
                    "turn_index": idx,
                    "user_content": user_content,
                    "assistant_content": conv.turns[idx].content,
                    "accurate": ann.accurate if ann else None,
                    "off_topic": ann.off_topic if ann else None,
                    "fabricated": ann.fabricated if ann else None,
                    "note": ann.note if ann else "",
                    "ai_reason": ann.ai_reason if ann else "",
                    "updated_at": ann.updated_at if ann else None,
                }
            )
    return rows


@app.get("/api/export/json")
def export_json() -> StreamingResponse:
    payload = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "items": _build_export(),
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=annotations_export.json"},
    )


@app.get("/api/export/csv")
def export_csv() -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "conversation_id",
            "turn_index",
            "user_content",
            "assistant_content",
            "accurate",
            "off_topic",
            "fabricated",
            "note",
            "ai_reason",
            "updated_at",
        ],
    )
    writer.writeheader()
    for row in _build_export():
        writer.writerow(row)
    content = "\ufeff" + buffer.getvalue()
    return StreamingResponse(
        iter([content]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=annotations_export.csv"},
    )
