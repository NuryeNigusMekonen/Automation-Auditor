from src.state import Evidence, merge_evidence_dicts


def test_merge_evidence_dicts_extends_lists():
    left = {
        "a": [
            Evidence(goal="a", found=True, location="x", rationale="r", confidence=1.0)
        ]
    }
    right = {
        "a": [
            Evidence(goal="a", found=False, location="y", rationale="r", confidence=1.0)
        ]
    }
    out = merge_evidence_dicts(left, right)
    assert len(out["a"]) == 2
