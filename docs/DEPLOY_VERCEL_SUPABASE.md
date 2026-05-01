# Deploy gratuito: Vercel + Supabase

Este app pode ser publicado sem Render quando os dados historicos B3 ficarem fora da
publicacao.

## Decisao de arquitetura

- Vercel hospeda o frontend e a API FastAPI via `api/index.py`.
- Supabase guarda o banco Postgres persistente.
- `data/` em producao usa `/tmp` e e transitorio.
- Historico B3/COTAHIST fica somente local para exercicios de teses historicas.

## Variaveis obrigatorias na Vercel

Configure em `Project Settings > Environment Variables`:

```text
DATABASE_URL=postgresql://...
```

Variaveis opcionais:

```text
FINNHUB_API_TOKEN=...
BRAPI_TOKEN=...
```

## Como publicar

1. Conecte o repositorio `Grao-Invest` na Vercel.
2. Mantenha `Root Directory` vazio, na raiz do repositorio.
3. Configure `DATABASE_URL` com a string do Supabase.
4. Rode o deploy.
5. Abra `/health` na URL publicada.

## O que nao deve ir para producao

- `data/app.db`
- `data/b3/`
- `data/lake/`
- `COTAHIST*.ZIP`
- arquivos `tmp_b3_*`

Esses arquivos sao grandes e servem apenas para treinamento historico local.
