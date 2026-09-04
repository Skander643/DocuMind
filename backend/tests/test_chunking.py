from app.ingest.chunking import CHARS_PER_TOKEN, split_page_text


def test_empty_page_yields_no_chunks() -> None:
    assert (
        split_page_text(
            "   \n",
            doc_id="abc",
            filename="x.pdf",
            page=1,
            language="fr",
            chunk_size=512,
            chunk_overlap=64,
        )
        == []
    )


def test_short_page_is_one_chunk() -> None:
    text = "Article premier. Le présent code s'applique aux établissements."
    chunks = split_page_text(
        text,
        doc_id="abc123",
        filename="code.pdf",
        page=2,
        language="fr",
        chunk_size=512,
        chunk_overlap=64,
    )
    assert len(chunks) == 1
    assert chunks[0].doc_id == "abc123"
    assert chunks[0].filename == "code.pdf"
    assert chunks[0].page == 2
    assert chunks[0].language == "fr"
    assert chunks[0].chunk_index == 0
    assert "présent code" in chunks[0].text


def test_long_page_splits_and_keeps_metadata() -> None:
    sentence = "Le salarié bénéficie d'un congé annuel payé. "
    text = sentence * 80
    chunks = split_page_text(
        text,
        doc_id="d1",
        filename="conges.pdf",
        page=7,
        language="fr",
        chunk_size=32,
        chunk_overlap=8,
        start_index=3,
    )
    assert len(chunks) > 1
    assert all(c.filename == "conges.pdf" and c.page == 7 for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(3, 3 + len(chunks)))
    assert all(len(c.text) <= 32 * CHARS_PER_TOKEN + 64 for c in chunks)
