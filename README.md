# pr-evidence

GitHub Action que transforma cada pull request num **pacote de evidências**: um comentário fixo, atualizado a cada push, que diz por que a mudança recebeu um tier de risco e que tipo de revisão humana ela merece.

O tier é calculado por **regras de caminho de arquivo** — determinístico e explicável. Um arquivo de duas linhas numa fronteira de segurança pesa mais que um refactor de 500 linhas de interface.

| Tier | Significado | Revisão sugerida |
|------|-------------|------------------|
| 0 | Sem efeito em execução | Leitura rápida |
| 1 | Comportamento local (padrão) | Seguir uma ação do usuário pelo diff; ler os testes antes do código |
| 2 | Contrato ou dados persistidos | Comparar o contrato com o outro lado; conferir migração e compatibilidade |
| 3 | Segurança ou infraestrutura | Rodar localmente e passar o checklist de segurança |

Inspirado em *The Pull Request Is Becoming an Evidence Package* (Nikolaos Papachristos, Level Up Coding, 2026). Criado para o AgrOraculum (TCC — FATEC Baixada Santista).

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
    - uses: leonardosf98/pr-evidence@v1
```

`fetch-depth: 0` é obrigatório: a action compara `base...head` para listar os arquivos alterados.

## Regras (`.github/pr-evidence.toml`)

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
