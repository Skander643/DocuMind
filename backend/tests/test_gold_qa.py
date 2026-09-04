import json

from app.config import PROJECT_ROOT


def test_gold_set_has_fifty_questions() -> None:
    path = PROJECT_ROOT / "eval" / "gold_qa.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data["items"]
    assert len(items) == 50
    ids = [row["id"] for row in items]
    assert len(set(ids)) == 50
    grounded = [row for row in items if not row["expect_refuse"]]
    refused = [row for row in items if row["expect_refuse"]]
    assert len(grounded) == 47
    assert len(refused) == 3
    for row in grounded:
        assert row["ground_truth"].strip()
        assert ":" in row["source_hint"]
        filename, page = row["source_hint"].rsplit(":", 1)
        assert filename.endswith(".pdf")
        assert page.isdigit()
    langs = {row["language"] for row in items}
    assert langs >= {"fr", "en", "ar"}
