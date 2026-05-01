# Modelo de atualizacao

Este projeto usa um fluxo simples para evitar upload manual.

## Fonte da verdade

- Codigo: GitHub, repositorio `Grao-Invest`.
- Deploy: Vercel, conectado ao GitHub.
- Banco persistente: Supabase, via `DATABASE_URL`.
- Dados historicos B3: somente local, fora da publicacao.

## Como uma mudanca vai para producao

1. Alterar o codigo localmente.
2. Rodar uma validacao minima:
   - `python -m pytest -q tests/contract`
   - abrir `/health` localmente quando a mudanca afetar backend.
3. Criar commit:
   - `git add .`
   - `git commit -m "Descricao curta da mudanca"`
4. Publicar:
   - `git push`
5. A Vercel detecta o push no GitHub e cria novo deploy automaticamente.
6. Validar a URL publica:
   - `/health`
   - tela principal
   - fluxo alterado.

## Regra de seguranca

Nunca subir:

- `data/app.db`
- `data/b3/`
- `data/lake/`
- `.venv/`
- tokens
- arquivos `tmp_b3_*`

Esses itens ja estao protegidos pelo `.gitignore`.

## Quando usar local

Use localmente para exercicios com historico B3 completo e teses historicas pesadas.

## Quando usar producao

Use a URL publicada para acesso dos participantes, cadastro, dashboard, simulacoes leves
e funcoes que usam dados persistidos no Supabase ou provedores externos sob demanda.
