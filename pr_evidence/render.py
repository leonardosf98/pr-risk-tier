from pr_evidence.classify import DEFAULT_REASON_ID, Classification, Reason

MARKER = "<!-- pr-evidence:comment -->"

TIER_LABELS = {
    0: "sem efeito em execução",
    1: "comportamento local",
    2: "contrato ou dados persistidos",
    3: "segurança ou infraestrutura",
}

REVIEW_GUIDANCE = {
    0: "Leitura rápida: conferir texto e links.",
    1: "Seguir uma ação do usuário pelo diff e ler os testes antes do código.",
    2: (
        "Comparar o contrato com o outro repositório e conferir migração e compatibilidade "
        "antes de ler o resto do diff."
    ),
    3: (
        "Antes de aprovar: rodar localmente e passar o checklist de segurança. "
        "Nunca aprovar só pelo diff."
    ),
}

FOOTER = (
    "<sub>Gerado por [pr-evidence](https://github.com/leonardosf98/pr-evidence) "
    "a partir das regras em `.github/pr-evidence.toml`.</sub>"
)


def render_comment(classification: Classification) -> str:
    tier = classification.tier
    lines = [
        MARKER,
        f"## 📦 Pacote de evidências — Tier {tier} · {TIER_LABELS[tier]}",
        "",
        f"### Por que tier {tier}",
        "",
        *(_reason_line(reason) for reason in classification.reasons),
    ]
    if not classification.reasons:
        lines.append("Nenhum arquivo alterado.")
    lines += [
        "",
        "### Revisão sugerida",
        "",
        REVIEW_GUIDANCE[tier],
        "",
        FOOTER,
        "",
    ]
    return "\n".join(lines)


def _reason_line(reason: Reason) -> str:
    label = "sem regra específica" if reason.rule_id == DEFAULT_REASON_ID else f"`{reason.rule_id}`"
    files = ", ".join(f"`{path}`" for path in reason.files)
    return f"- {label} (tier {reason.tier}): {files}"
