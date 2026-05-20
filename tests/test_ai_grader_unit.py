import json

from services.ai_grader import grade_submission_with_ai


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_ai_grader_no_files_returns_zero():
    result = grade_submission_with_ai("desc", "mission", [])
    assert result["success"] is True
    assert result["score"] == 0.0
    assert result["criteria"][0]["score"] == 0


def test_ai_grader_missing_keys_fails(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    result = grade_submission_with_ai("desc", "mission", [{"name": "main.ino", "content": "void setup(){}"}])

    assert result["success"] is False
    assert "API key" in result["error"]


def test_ai_grader_gemini_success_clamps_scores_and_skips_dataset(monkeypatch, tmp_path):
    dataset_path = tmp_path / "dataset.jsonl"
    ai_payload = {
        "score": 9.0,
        "feedback": "ok",
        "criteria": [
            {"name": "A", "score": 20},
            {"name": "B", "score": -5},
            {"name": "C", "score": 5},
        ],
    }
    gemini_payload = {"candidates": [{"content": {"parts": [{"text": json.dumps(ai_payload)}]}}]}

    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("AI_GRADER_RECORD_DATASET", "0")
    monkeypatch.setenv("AI_GRADER_DATASET_PATH", str(dataset_path))

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: FakeResponse(gemini_payload))

    result = grade_submission_with_ai("desc", "mission", [{"name": "main.ino", "content": "void setup(){}"}], provider="gemini")

    assert result["success"] is True
    assert result["score"] == 5.0
    assert [item["score"] for item in result["criteria"]] == [10.0, 0.0, 5.0]
    assert not dataset_path.exists()


def test_ai_grader_writes_to_temp_dataset_when_enabled(monkeypatch, tmp_path):
    dataset_path = tmp_path / "ai_training_dataset.jsonl"
    ai_payload = {"score": 7.0, "feedback": "ok", "criteria": []}
    groq_payload = {"choices": [{"message": {"content": json.dumps(ai_payload)}}]}

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq")
    monkeypatch.setenv("AI_GRADER_RECORD_DATASET", "1")
    monkeypatch.setenv("AI_GRADER_DATASET_PATH", str(dataset_path))

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: FakeResponse(groq_payload))

    result = grade_submission_with_ai("desc", "mission", [{"name": "main.ino", "content": "void loop(){}"}], provider="groq")

    assert result["success"] is True
    lines = dataset_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["final_score"] == 7.0


def test_ai_grader_invalid_json_response(monkeypatch):
    gemini_payload = {"candidates": [{"content": {"parts": [{"text": "not-json"}]}}]}

    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("AI_GRADER_RECORD_DATASET", "0")

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: FakeResponse(gemini_payload))

    result = grade_submission_with_ai("desc", "mission", [{"name": "main.ino", "content": "void setup(){}"}], provider="gemini")

    assert result["success"] is False
    assert "định dạng" in result["error"]
