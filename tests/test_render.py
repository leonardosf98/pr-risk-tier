from pr_evidence.classify import DEFAULT_REASON_ID, Classification, Reason
from pr_evidence.render import MARKER, render_comment


def test_comment_starts_with_marker():
    comment = render_comment(Classification(0, ()))

    assert comment.startswith(MARKER + "\n")


def test_header_shows_tier_and_label():
    comment = render_comment(Classification(2, (Reason("api_contract", 2, ("a.py",)),)))

    assert "## 📦 Pacote de evidências — Tier 2 · contrato ou dados persistidos" in comment


def test_reasons_list_rule_and_files():
    comment = render_comment(
        Classification(3, (Reason("security_boundary", 3, ("app/core/auth.py", "b.py")),))
    )

    assert "### Por que tier 3" in comment
    assert "- `security_boundary` (tier 3): `app/core/auth.py`, `b.py`" in comment


def test_default_reason_is_explained_in_portuguese():
    comment = render_comment(Classification(1, (Reason(DEFAULT_REASON_ID, 1, ("x.py",)),)))

    assert "- sem regra específica (tier 1): `x.py`" in comment


def test_review_guidance_follows_reasons_section():
    comment = render_comment(Classification(3, (Reason("infra", 3, ("Dockerfile",)),)))

    reasons_at = comment.index("### Por que tier 3")
    review_at = comment.index("### Revisão sugerida")
    assert reasons_at < review_at
    assert "rodar localmente" in comment[review_at:]


def test_empty_pull_request_says_no_files():
    comment = render_comment(Classification(0, ()))

    assert "Nenhum arquivo alterado." in comment
