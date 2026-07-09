from __future__ import annotations

from pathlib import Path

from scripts.build_papers_tesis_deep_audit import write_audit


def _row(
    *,
    relative_path: str,
    decision: str,
    action_required: str = "none_now",
    bib_status: str = "existing",
) -> dict[str, object]:
    return {
        "folder": relative_path.split("/", 1)[0],
        "relative_path": relative_path,
        "title": f"Title {relative_path}",
        "status": "published",
        "primary_domain": "conformal risk control",
        "bib_key": "paperkey",
        "bib_status": bib_status,
        "core_concepts": "coverage; decision risk",
        "key_claims": "claim summary",
        "conclusions": "use with finite-grid boundary",
        "figures_tables_useful": "inspiration only",
        "limitations": "not CRPTO evidence",
        "decision": decision,
        "action_required": action_required,
        "crpto_value": "supports CRPTO framing",
        "extended_lab_value": "future-work value",
        "evidence_gate": "do not reopen champion",
        "artifact_sink": "docs/research/example.md",
        "stop_rule": "keep as literature unless claim changes",
        "implementation_or_experiment": "none",
    }


def test_write_audit_builds_editorial_sections(tmp_path: Path) -> None:
    rows = [
        _row(relative_path="paper/promote.pdf", decision="promote_crpto_body"),
        _row(relative_path="paper/append.pdf", decision="append_crpto_related_work"),
        _row(
            relative_path="supplement/experiment.pdf",
            decision="append_tail_risk",
            action_required="experiment_completed_appendix_diagnostic",
        ),
        _row(
            relative_path="tesis/future.pdf",
            decision="park_future_work",
            bib_status="needs_bib_if_cited",
        ),
    ]
    curated_visual_rows = [
        {
            "relative_path": "paper/promote.pdf",
            "caption_type": "figure",
            "caption_index": 1,
            "editorial_sink": "own schematic",
            "why_useful": "layout inspiration",
            "claim_boundary": "do not reproduce",
        }
    ]
    audit_path = tmp_path / "audit.md"

    write_audit(
        audit_path,
        rows,
        tmp_path / "matrix.csv",
        tmp_path / "captions.csv",
        tmp_path / "visuals.csv",
        curated_visual_rows,
    )

    text = audit_path.read_text(encoding="utf-8")

    assert "# Papers_tesis Deep Audit" in text
    assert "## Lectura integrada para Paper CRPTO" in text
    assert "paper/promote.pdf" in text
    assert "paper/append.pdf" in text
    assert "supplement/experiment.pdf" in text
    assert "tesis/future.pdf" in text
    assert "| action_required | n |" in text
    assert "experiment_completed_appendix_diagnostic" in text
    assert "needs_bib_if_cited" in text
    assert "no cambia el champion CRPTO" in text
