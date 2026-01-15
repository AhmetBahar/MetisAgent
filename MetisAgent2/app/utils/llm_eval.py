# app/utils/llm_eval.py
import json

def summarize_for_llm(step_result: dict, max_keys: int = 6) -> dict:
    succ = bool(step_result.get("success"))
    data = step_result.get("data")
    err = step_result.get("error")
    summary = {
        "success": succ,
        "has_data": data is not None,
        "error_type": (type(err).__name__ if isinstance(err, Exception) else None) if err else None,
        "keys": list(data.keys())[:max_keys] if isinstance(data, dict) else None,
    }
    try:
        payload = json.dumps(step_result)
        summary["approx_size_bytes"] = len(payload.encode("utf-8"))
    except Exception:
        summary["approx_size_bytes"] = None
    return summary