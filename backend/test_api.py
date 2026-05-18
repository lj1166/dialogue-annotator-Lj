"""后端接口冒烟测试。用法: python test_api.py"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api"


def req(method: str, path: str, body: dict | None = None, timeout: int = 130):
    url = f"{BASE}{path}"
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, json.loads(raw) if raw else None


def main() -> int:
    passed = 0
    failed = 0

    def check(name: str, ok: bool, detail: str = ""):
        nonlocal passed, failed
        if ok:
            passed += 1
            print(f"  [PASS] {name}" + (f" — {detail}" if detail else ""))
        else:
            failed += 1
            print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))

    print("=== 后端 API 测试 ===\n")

    try:
        code, health = req("GET", "/health")
        check("GET /health", code == 200 and health.get("status") == "ok", str(health))
    except Exception as e:
        check("GET /health", False, str(e))
        print("\n后端未启动，请先运行: python run.py")
        return 1

    try:
        code, convs = req("GET", "/conversations")
        check("GET /conversations", code == 200 and len(convs) == 15, f"count={len(convs)}")
    except Exception as e:
        check("GET /conversations", False, str(e))

    try:
        code, conv = req("GET", "/conversations/001")
        check(
            "GET /conversations/001",
            code == 200 and conv.get("id") == "001" and len(conv.get("turns", [])) >= 2,
            f"turns={len(conv.get('turns', []))}",
        )
    except Exception as e:
        check("GET /conversations/001", False, str(e))

    try:
        code, stats = req("GET", "/stats")
        check(
            "GET /stats",
            code == 200 and stats.get("total_assistant_turns") == 15,
            f"progress={stats.get('progress_percent')}%",
        )
    except Exception as e:
        check("GET /stats", False, str(e))

    try:
        body = {
            "conversation_id": "002",
            "turn_index": 1,
            "accurate": True,
            "off_topic": False,
            "fabricated": False,
            "note": "自动化测试",
        }
        code, saved = req("PUT", "/annotations", body)
        check(
            "PUT /annotations",
            code == 200 and saved.get("conversation_id") == "002",
            f"accurate={saved.get('accurate')}",
        )
    except Exception as e:
        check("PUT /annotations", False, str(e))

    try:
        code, ann = req("GET", "/annotations/002/1")
        check(
            "GET /annotations/002/1",
            code == 200 and ann is not None and ann.get("accurate") is True,
            str(ann),
        )
    except Exception as e:
        check("GET /annotations/002/1", False, str(e))

    try:
        export_size = len(urllib.request.urlopen(f"{BASE}/export/json", timeout=10).read())
        check("GET /export/json", export_size > 100, f"bytes={export_size}")
    except Exception as e:
        check("GET /export/json", False, str(e))

    print("\n--- AI 建议 (Ollama，可能较慢) ---")
    try:
        code, ai = req(
            "POST",
            "/ai/suggest",
            {"conversation_id": "001", "turn_index": 1},
            timeout=130,
        )
        has_bool = (
            isinstance(ai.get("accurate"), bool)
            and isinstance(ai.get("off_topic"), bool)
            and isinstance(ai.get("fabricated"), bool)
        )
        check(
            "POST /ai/suggest",
            code == 200 and ai.get("available") and has_bool,
            f"accurate={ai.get('accurate')}, off_topic={ai.get('off_topic')}, "
            f"fabricated={ai.get('fabricated')}, reason={ai.get('reason', '')[:30]}",
        )
    except urllib.error.HTTPError as e:
        check("POST /ai/suggest", False, f"HTTP {e.code}: {e.read().decode()[:200]}")
    except Exception as e:
        check("POST /ai/suggest", False, str(e))

    print(f"\n=== 结果: {passed} 通过, {failed} 失败 ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
