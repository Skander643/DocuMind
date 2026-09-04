from app.eval.metrics import score_item


def test_score_item_refuse_only_tracks_gate() -> None:
    result = score_item(
        question="What is the capital of Australia?",
        answer="I don't have enough confidence to answer from the indexed documents.",
        ground_truth="refuse",
        contexts=[],
        refused=True,
        expect_refuse=True,
        judge_fn=lambda _p: '{"score": 1.0}',
        embed_fn=lambda texts: [[1.0, 0.0] for _ in texts],
    )
    assert result["refuse_correct"] is True
    assert result["faithfulness"] is None


def test_score_item_uses_judge_and_embeddings() -> None:
    def judge(prompt: str) -> str:
        if "one bool per passage" in prompt:
            return '{"relevant": [true, false]}'
        return '{"score": 0.8}'

    result = score_item(
        question="congé annuel",
        answer="quinze jours",
        ground_truth="quinze jours comprenant douze jours ouvrables",
        contexts=["article 113 quinze jours", "unrelated night work"],
        refused=False,
        expect_refuse=False,
        judge_fn=judge,
        embed_fn=lambda texts: [[1.0, 0.0] for _ in texts],
    )
    assert result["faithfulness"] == 0.8
    assert result["context_recall"] == 0.8
    assert result["context_precision"] == 1.0
    assert result["answer_relevancy"] == 1.0
