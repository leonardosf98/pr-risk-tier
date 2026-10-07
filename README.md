# pr-evidence

GitHub Action que transforma cada pull request num **pacote de evidências**: um comentário fixo, atualizado a cada push, que responde o que mudou, o que a mudança pode afetar, por que ela recebeu um tier de risco, o que foi provado, o que **não** foi provado e que tipo de revisão humana ela merece.

- O **tier de risco** é calculado por regras de caminho de arquivo (`.github/pr-evidence.toml` no repositório que usa a action) — determinístico e explicável.
- O agente que abriu a PR contribui só com intenção, consumidores, invariantes ligadas a testes e incertezas, num bloco JSON no corpo da PR. Esse bloco é **evidência, não autoridade**: a action valida o schema e confere se cada teste citado existe.

Inspirado em *The Pull Request Is Becoming an Evidence Package* (Nikolaos Papachristos, Level Up Coding, 2026). Nascido para as necessidades de desenvolvimento do AgrOraculum, meu sistema de monitoramento remoto agrícola que desenvolvi para o TCC.

> Em construção. Uso e formato do bloco serão documentados na primeira versão (`v1`).
