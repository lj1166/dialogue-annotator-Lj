from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

LabelDimension = Literal["accurate", "inaccurate", "off_topic", "on_topic", "fabricated", "not_fabricated"]


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class Conversation(BaseModel):
    id: str
    turns: list[Turn]


class Annotation(BaseModel):
    conversation_id: str
    turn_index: int
    accurate: bool | None = None
    off_topic: bool | None = None
    fabricated: bool | None = None
    note: str = ""
    ai_reason: str = ""
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class AnnotationSave(BaseModel):
    conversation_id: str
    turn_index: int
    accurate: bool | None = None
    off_topic: bool | None = None
    fabricated: bool | None = None
    note: str = ""


class ConversationSummary(BaseModel):
    id: str
    preview: str
    assistant_turns: int
    annotated_turns: int
    fully_annotated: bool


class StatsResponse(BaseModel):
    total_conversations: int
    total_assistant_turns: int
    annotated_turns: int
    progress_percent: float
    accurate_count: int
    inaccurate_count: int
    off_topic_count: int
    on_topic_count: int
    fabricated_count: int
    not_fabricated_count: int


class AiSuggestRequest(BaseModel):
    conversation_id: str
    turn_index: int


class AiSuggestResponse(BaseModel):
    accurate: bool | None
    off_topic: bool | None
    fabricated: bool | None
    reason: str
    available: bool
    message: str = ""
