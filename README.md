# pr-risk-tier

GitHub Action que comenta em cada pull request **o tier de risco da mudança (0 a 3), por que ela recebeu esse tier e que tipo de revisão humana ela merece**. O comentário é fixo e se atualiza a cada push.

```
## 📦 Pacote de evidências — Tier 3 · segurança ou infraestrutura

### Por que tier 3
- `infrastructure` (tier 3): `.github/workflows/ci.yml`, `Dockerfile`
- `api_contract` (tier 2): `app/schema/user.py`
- sem regra específica (tier 1): `app/services/report.py`

### Revisão sugerida
Antes de aprovar: rodar localmente e passar o checklist de segurança. Nunca aprovar só pelo diff.
```

O tier vem de **regras de caminho de arquivo** que cada repositório declara — determinístico e explicável, sem IA decidindo nada. Duas linhas numa fronteira de segurança pesam mais que um refactor de 500 linhas de interface.

| Tier | Significado | Revisão sugerida |
|------|-------------|------------------|
| 0 | Sem efeito em execução | Leitura rápida |
| 1 | Comportamento local (padrão) | Seguir uma ação do usuário pelo diff; ler os testes antes do código |
| 2 | Contrato ou dados persistidos | Comparar o contrato com quem o consome; conferir migração e compatibilidade |
| 3 | Segurança ou infraestrutura | Rodar localmente e passar o checklist de segurança |

Inspirado em *The Pull Request Is Becoming an Evidence Package* (Nikolaos Papachristos, Level Up Coding, 2026). Nasceu no AgrOraculum (TCC — FATEC Baixada Santista) e serve a qualquer repositório.

## Uso

```yaml
evidence:
  needs: [ci]
  if: always() && github.event_name == 'pull_request'
  runs-on: ubuntu-latest
  permissions:
    contents: read
    pull-requests: write
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    - uses: leonardosf98/pr-risk-tier@v1
```

`fetch-depth: 0` é obrigatório: a action compara `base...head` para listar os arquivos alterados.

## Regras (`.github/pr-risk-tier.toml`)

```toml
size_limit = 400
default_tier = 1
test_paths = ["tests/**"]

[[rule]]
id = "docs_only"
tier = 0
paths = ["docs/**", "**/*.md"]

[[rule]]
id = "api_contract"
tier = 2
paths = ["app/schema/**"]
```

- Cada arquivo recebe o **maior** tier entre as regras que casam; sem regra, recebe `default_tier`.
- O tier da PR é o maior entre os arquivos — tier 0 só quando **todos** os arquivos são tier 0.
- Padrões: `*` não atravessa `/`; `**` atravessa; `**/` também casa a raiz.

## Desenvolvimento

Python 3.11+, só biblioteca padrão.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/ruff format --check . && .venv/bin/ruff check .
```

## Próximas versões

- Bloco do agente no corpo da PR (intenção, consumidores, invariantes ligadas a testes, incertezas), validado pela action.
- Evidência do CI e do tamanho do diff.
