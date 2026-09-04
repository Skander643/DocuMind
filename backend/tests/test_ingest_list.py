from pathlib import Path

from app.ingest.ingest import list_pdfs


def test_list_pdfs_creates_dir(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    assert list_pdfs(raw) == []
    assert raw.is_dir()
