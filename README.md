# pr-risk-tier

GitHub Action que comenta em cada pull request um **pacote de evidências**: o tier de risco da mudança (0 a 3) e por quê, o que o CI provou, o que **não** dá para considerar provado e que tipo de revisão humana a PR merece. O comentário é fixo e se atualiza a cada push.

```
## 📦 Pacote de evidências — Tier 3 · segurança ou infraestrutura

### Por que tier 3
| Fronteira          | Tier | Arquivos alterados                      |
| infrastructure     | 3    | .github/workflows/ci.yml, package.json  |
| security_boundary  | 3    | —                                       |
| api_contract       | 2    | —                                       |

### Evidência
| CI · Lint, typecheck, test, audit | ❌ falhou em `npm audit` · log |
| Tamanho do diff                   | 133 linhas (+132 −1) · limite do tier 3: 400 ✅ |
| Arquivos                          | 2 de código · 0 de teste · 4 sem efeito em execução |

### Incertezas
- CI com falha em `Lint, typecheck, test, audit` (`npm audit`): resolver antes de tratar o resto como evidência.
- 2 arquivo(s) de código sem nenhum teste alterado: o comportamento novo pode não estar coberto.

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
    actions: read
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    - uses: leonardosf98/pr-risk-tier@v1
```

- `fetch-depth: 0` é obrigatório: a action compara `base...head` para medir o diff.
- `needs` com os jobs do CI e `if: always()` fazem o comentário sair **depois** deles, mesmo quando falham — a action lê o resultado de cada job e passo pela API do próprio run.
- `actions: read` permite ler esse resultado. Sem ela, o comentário sai assim mesmo, com o CI marcado como indisponível.

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
- `size_limit` vale a partir do tier 2; nos tiers 0 e 1 o tamanho é só informativo.
- `test_paths` separa arquivos de teste dos de código; código alterado sem nenhum teste alterado vira incerteza.
- Um padrão que não casa nenhum arquivo do repositório também vira incerteza — costuma ser erro de digitação ou pasta renomeada.

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
- Invariante provada pelo relatório JUnit do CI, não só declarada.
- Tier calculado no início do CI para ligar validação mais forte em T2/T3 (testes de mutação nos arquivos alterados).
