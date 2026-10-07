from pr_risk_tier.classify import DEFAULT_REASON_ID, Classification
from pr_risk_tier.evidence import Evidence, JobResult, Size
from pr_risk_tier.rules import Rules

MARKER = "<!-- pr-risk-tier:comment -->"

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
        "Comparar o contrato com quem o consome e conferir migração e compatibilidade "
        "antes de ler o resto do diff."
    ),
    3: (
        "Antes de aprovar: rodar localmente e passar o checklist de segurança. "
        "Nunca aprovar só pelo diff."
    ),
}

FOOTER = (
    "<sub>Gerado por [pr-risk-tier](https://github.com/leonardosf98/pr-risk-tier) "
    "a partir das regras em `.github/pr-risk-tier.toml`.</sub>"
)


MAX_FILES_PER_ROW = 5

CONCLUSIONS = {
    "success": "✅ passou",
    "failure": "❌ falhou",
    "skipped": "⏭️ pulado",
    "cancelled": "⛔ cancelado",
    "timed_out": "⌛ tempo esgotado",
}

FAILED_CONCLUSIONS = {"failure", "cancelled", "timed_out", "startup_failure"}


def render_comment(classification: Classification, rules: Rules, evidence: Evidence) -> str:
    tier = classification.tier
    lines = [
        MARKER,
        f"## 📦 Pacote de evidências — Tier {tier} · {TIER_LABELS[tier]}",
        "",
        f"### Por que tier {tier}",
        "",
        *_boundary_table(classification, rules),
        "",
        "### Evidência",
        "",
        "| Verificação | Resultado |",
        "|---|---|",
        *_ci_rows(evidence.jobs),
        f"| Tamanho do diff | {_size_text(evidence.size, tier)} |",
        f"| Arquivos | {evidence.mix.code} de código · {evidence.mix.tests} de teste · "
        f"{evidence.mix.inert} sem efeito em execução |",
        "",
        "### Incertezas",
        "",
        *(f"- {unknown}" for unknown in _unknowns(evidence, tier)),
        "",
        "### Revisão sugerida",
        "",
        REVIEW_GUIDANCE[tier],
        "",
        FOOTER,
        "",
    ]
    return "\n".join(lines)


def _boundary_table(classification: Classification, rules: Rules) -> list[str]:
    if not classification.reasons:
        return ["Nenhum arquivo alterado."]
    touched = {reason.rule_id: reason.files for reason in classification.reasons}
    rows = [(rule.id, rule.tier, touched.get(rule.id, ())) for rule in rules.rules]
    rows += [
        (reason.rule_id, reason.tier, reason.files)
        for reason in classification.reasons
        if reason.rule_id == DEFAULT_REASON_ID
    ]
    rows.sort(key=lambda row: (-row[1], row[0]))
    return [
        "| Fronteira | Tier | Arquivos alterados |",
        "|---|---|---|",
        *(
            f"| {_rule_label(rule_id)} | {tier} | {_files_text(files)} |"
            for rule_id, tier, files in rows
        ),
    ]


def _rule_label(rule_id: str) -> str:
    return "sem regra específica" if rule_id == DEFAULT_REASON_ID else f"`{rule_id}`"


def _files_text(files: tuple[str, ...]) -> str:
    if not files:
        return "—"
    shown = ", ".join(f"`{path}`" for path in files[:MAX_FILES_PER_ROW])
    hidden = len(files) - MAX_FILES_PER_ROW
    return f"{shown} e mais {hidden}" if hidden > 0 else shown


def _ci_rows(jobs: tuple[JobResult, ...] | None) -> list[str]:
    if jobs is None:
        return ["| CI | ⚠️ indisponível |"]
    if not jobs:
        return ["| CI | nenhum job concluído antes deste |"]
    return [f"| CI · {job.name} | {_job_text(job)} |" for job in jobs]


def _job_text(job: JobResult) -> str:
    text = CONCLUSIONS.get(job.conclusion, f"`{job.conclusion}`")
    if job.failed_steps:
        text += " em " + ", ".join(f"`{step}`" for step in job.failed_steps)
    if job.conclusion in FAILED_CONCLUSIONS:
        text += f" · [log]({job.url})"
    return text


def _size_text(size: Size, tier: int) -> str:
    text = f"{size.total} linhas (+{size.added} −{size.deleted})"
    if not size.enforced:
        return f"{text} · tier {tier} não tem limite rígido"
    if size.over_limit:
        return f"{text} · ⚠️ acima do limite do tier {tier}: {size.limit}"
    return f"{text} · limite do tier {tier}: {size.limit} ✅"


def _unknowns(evidence: Evidence, tier: int) -> list[str]:
    unknowns = []
    if evidence.jobs is None:
        unknowns.append(
            "Resultado do CI indisponível: o job que roda a action precisa da permissão "
            "`actions: read`."
        )
    for job in evidence.jobs or ():
        if job.conclusion in FAILED_CONCLUSIONS:
            steps = ", ".join(f"`{step}`" for step in job.failed_steps)
            where = f"`{job.name}` ({steps})" if steps else f"`{job.name}`"
            unknowns.append(
                f"CI com falha em {where}: resolver antes de tratar o resto como evidência."
            )
    if evidence.size.over_limit:
        unknowns.append(
            f"Diff acima do limite do tier {tier} "
            f"({evidence.size.total}/{evidence.size.limit}): considere fatiar."
        )
    if evidence.mix.code and not evidence.mix.tests:
        unknowns.append(
            f"{evidence.mix.code} arquivo(s) de código sem nenhum teste alterado: "
            "o comportamento novo pode não estar coberto."
        )
    unknowns += [
        f"Padrão `{pattern}` da regra `{rule_id}` não casa nenhum arquivo do repositório: "
        "pode estar errado ou obsoleto."
        for rule_id, pattern in evidence.unmatched
    ]
    return unknowns or [
        "Nada detectado automaticamente. A máquina não sabe a intenção da mudança nem as "
        "regras de negócio: o que ficou sem prova é quem escreveu a PR que precisa dizer."
    ]
