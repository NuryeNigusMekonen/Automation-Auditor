from src.nodes.judges import _sanitize_citations


def test_sanitize_citations_filters_to_allowed_only() -> None:
    cited = ["src/graph.py", "src/graph.py", "fake/path.py", "src/state.py"]
    allowed = ["src/graph.py", "src/state.py"]

    out = _sanitize_citations(cited, allowed)

    assert out == ["src/graph.py", "src/graph.py", "src/state.py"]


def test_sanitize_citations_empty_allowed_returns_empty() -> None:
    cited = ["src/graph.py", "src/state.py"]
    out = _sanitize_citations(cited, [])
    assert out == []
