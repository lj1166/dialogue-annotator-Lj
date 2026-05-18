import json
from pathlib import Path

from app.models import Annotation, Conversation

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONVERSATIONS_PATH = DATA_DIR / "conversations.json"
ANNOTATIONS_PATH = DATA_DIR / "annotations.json"


def load_conversations() -> list[Conversation]:
    raw = json.loads(CONVERSATIONS_PATH.read_text(encoding="utf-8"))
    return [Conversation.model_validate(item) for item in raw]


def load_annotations() -> dict[str, Annotation]:
    if not ANNOTATIONS_PATH.exists():
        return {}
    raw = json.loads(ANNOTATIONS_PATH.read_text(encoding="utf-8"))
    return {key: Annotation.model_validate(value) for key, value in raw.items()}


def save_annotations(annotations: dict[str, Annotation]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {key: value.model_dump() for key, value in annotations.items()}
    ANNOTATIONS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def annotation_key(conversation_id: str, turn_index: int) -> str:
    return f"{conversation_id}:{turn_index}"


def assistant_turn_indices(conversation: Conversation) -> list[int]:
    return [i for i, turn in enumerate(conversation.turns) if turn.role == "assistant"]
