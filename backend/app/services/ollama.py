import json
import logging
import os
import re

import httpx

logger = logging.getLogger("app.ai")

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

SYSTEM_PROMPT = """你是客服对话质检助手。根据用户问题和客服回复，判断三个维度并只输出 JSON：
- accurate: true=准确,false=不准确
- off_topic: true=跑题,false=不跑题
- fabricated: true=有编造信息,false=无编造
- reason: 一句话中文理由
不要输出其它文字。"""


def coerce_bool(value) -> bool | None:
    """将模型返回的 true/false 字符串等统一为 bool。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("true", "1", "yes", "是"):
            return True
        if normalized in ("false", "0", "no", "否"):
            return False
    return None


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            return None
    return None


async def suggest_labels(user_content: str, assistant_content: str) -> tuple[dict | None, str]:
    logger.info("=" * 60)
    logger.info("[AI] 开始请求 Ollama model=%s base=%s", OLLAMA_MODEL, OLLAMA_BASE)
    logger.info("[AI] 用户: %s", user_content[:200] + ("…" if len(user_content) > 200 else ""))
    logger.info(
        "[AI] 客服: %s",
        assistant_content[:200] + ("…" if len(assistant_content) > 200 else ""),
    )

    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"【用户】{user_content}\n\n"
                    f"【客服】{assistant_content}\n\n"
                    "请输出 JSON。"
                ),
            },
        ],
        "options": {"temperature": 0.1},
    }
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.error("[AI] Ollama 请求失败: %s", exc)
        return None, f"Ollama 不可用: {exc}"

    content = data.get("message", {}).get("content", "")
    logger.info("[AI] 模型原始回复:\n%s", content)

    parsed = _extract_json(content)
    if not parsed:
        logger.warning("[AI] JSON 解析失败，原始内容见上")
        return None, "模型返回格式无法解析，请手动标注"

    logger.info("[AI] 解析后 JSON: %s", json.dumps(parsed, ensure_ascii=False))
    coerced = {
        "accurate": coerce_bool(parsed.get("accurate")),
        "off_topic": coerce_bool(parsed.get("off_topic")),
        "fabricated": coerce_bool(parsed.get("fabricated")),
        "reason": parsed.get("reason"),
    }
    logger.info("[AI] 转换后标签: %s", json.dumps(coerced, ensure_ascii=False))
    logger.info("=" * 60)
    return parsed, ""
