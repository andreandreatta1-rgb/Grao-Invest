# AI-Powered Investment Advisor

This repository is structured to help coding agents implement the product safely and incrementally from the functional specification.

## Artifact Pyramid
- Functional specification in `docs/ef/`
- Architecture decisions in `docs/adr/`
- Domain notes in `docs/domain/`
- Executable specs in `specs/`
- Vertical-slice tasks in `backlog/`

## Current State
- The functional specification has been copied into `docs/ef/`.
- Initial ADRs, domain notes, task templates, and slice backlogs are in place.
- A functional MVP for Phase 1 is implemented with FastAPI, SQLite and a simple web UI.

## MVP Coverage
- `RF-01`: signup, consent capture, login baseline and MFA setup/verification endpoints
- `RF-02`: suitability questionnaire with investor profile classification
- `RF-03`: market tick ingestion with canonical normalized event shape
- `RF-03`: failover auditavel entre provedor primario e secundario na ingestao de mercado
- `RF-03`: sincronizacao externa de historico B3 (COTAHIST) com carteira pequena para validacao de formato e carga incremental
- `RF-04`: ingestao point-in-time de fundamentos com versionamento por snapshot e consulta historica
- `RF-05`: noticias com classificacao estruturada de sentimento, magnitude, agregacao por ticker e historico por fonte
- `RF-07`: feature store tecnica com `SMA`, `EMA`, `RSI`, `MACD`, momentum e volatilidade
- `RF-10`: paper trading com spread/slippage dinamicos, custos e IR estimado com memoria de calculo auditavel
- `RF-09`: baseline de backtesting point-in-time com metricas e trades explicaveis
- `RF-11` e `RF-12`: risco agregado, drawdown guard, circuit breaker e kill-switch persistente
- `RF-15`, `RF-16` e `RF-17`: dashboard ampliado, relatorios consolidados, alertas configuraveis e XAI estruturado
- `RF-36` (suplemento SSE baseline): estudo de caso tese->operacao estruturada->monitoramento com KPIs de confianca, financeiro esperado e financeiro realizado
- `RF-08`: sinais multi-fator e suporte inicial a recomputacao batch multiativo
- Cross-cutting: audit trail, anti-recommendation guardrail and point-in-time query helpers

## Run Locally
1. Install dependencies: `python -m pip install -e .[dev]`
2. Start the application: `python -m uvicorn app.main:app --app-dir services/api --reload`
3. Open:
   - App UI: `http://127.0.0.1:8000/`
   - OpenAPI docs: `http://127.0.0.1:8000/docs`

## Quality Loop
- `python scripts/check.py`
- `make check`

## Daily Ops (B3 + Case Study)
- Se existir `COTAHIST_A<ano>.ZIP` na raiz do repo (ou pasta pai), o sync B3 usa o arquivo local antes do download.
- `python scripts/sync_b3_small_portfolio.py --user-id <id> --year 2025 --max-days-per-instrument 120`
- `python scripts/sync_b3_small_portfolio.py --user-id <id> --start-year 2022 --end-year 2025 --max-days-per-instrument 250`
- `python scripts/sync_b3_small_portfolio.py --user-id <id> --full-universe --start-year 2022 --end-year 2025 --max-days-per-instrument 250 --max-instruments 1500`
- `python scripts/ingest_fundamentals_batch.py --input-file <fundamentals.json>`
- `python scripts/daily_b3_pipeline.py --user-id <id> --year 2025 --horizon-bars 10`
- `python scripts/daily_b3_pipeline.py --user-id <id> --start-year 2022 --end-year 2025 --horizon-bars 12`
- `python scripts/realtime_b3_loop.py --user-id <id> --year 2026 --poll-seconds 900 --iterations 0`
- `python scripts/intraday_feed_worker.py --user-id <id> --mode rest --provider-name finnhub --instruments PETR4,VALE3 --auto-recompute-indicators`
- `python scripts/intraday_feed_worker.py --user-id <id> --mode ws --provider-name finnhub --instruments PETR4,VALE3 --duration-seconds 120 --auto-recompute-indicators`
- `python scripts/feed_health_job.py --user-id <id> --stale-threshold-seconds 1800 --latency-threshold-seconds 120`
- `python scripts/data_quality_gate_job.py --user-id <id> --instruments PETR4,VALE3,ITUB4 --market-min-fresh-coverage-pct 95 --fundamentals-min-coverage-pct 90 --fundamentals-min-fresh-coverage-pct 90`
- `python scripts/sync_news_period.py --user-id <id> --start-date 2025-01-01 --end-date 2026-04-21 --instruments PETR4,VALE3,ITUB4 --max-articles-per-instrument 80`
- `python scripts/sync_fundamentals_external.py --user-id <id> --provider-name auto --max-instruments 600`
- `python scripts/sync_fundamentals_external.py --user-id <id> --instruments PETR4,VALE3,ITUB4 --include-existing`
- `python scripts/learn_thesis_skill.py --user-id <id> --horizon-bars 12 --max-candidates 1500`
- `python scripts/learn_thesis_skill.py --user-id <id> --iterations 8 --sleep-seconds 1800`
- `python scripts/run_thesis_ab_experiment.py --user-id <id> --horizon-bars 12 --max-candidates 1200`
- `python scripts/run_thesis_shadow_cycle.py --user-id <id> --horizon-bars 12 --max-candidates 1200 --required-stable-cycles 2`
- `python scripts/daily_b3_pipeline.py --user-id <id> --start-year 2020 --end-year 2026 --sync-news --news-start-date 2025-01-01 --news-end-date 2026-04-21 --horizon-bars 12`
- `python scripts/run_case_study.py --user-id <id> --instruments PETR4,VALE3 --horizon-bars 8`
- `python scripts/run_gamification_experiment.py --user-id <id> --instruments PETR4,VALE3,ITUB4,B3SA3,WEGE3 --thesis-count 10 --horizon-bars 8`
- `python scripts/run_gamification_experiment.py --user-id <id> --decision-file data/game_players_input.example.json --thesis-count 10`
- `python scripts/run_gamification_pack.py --user-id <id> --instruments PETR4,VALE3,ITUB4,B3SA3,WEGE3 --thesis-count 10 --horizon-bars 8`
- `python scripts/build_b3_bronze_silver.py --source-root data/b3/historico_2026-04-22 --pesquisa-root data/b3/pesquisa_pregao_2026-04-22 --output-root data/lake/b3 --instruments PETR4,VALE3,ITUB4`
- `python scripts/build_b3_bronze_silver.py --source-root data/b3/historico_2026-04-22 --output-root data/lake/b3 --full-universe`
- `python scripts/load_b3_silver_market.py --csv-path data/lake/b3/silver/market_daily.csv --database-path data/app.db --provider b3-cotahist-lake --batch-size 5000`
- `python scripts/load_b3_silver_market.py --csv-path data/lake/b3/silver/market_daily.csv --database-path data/app.db --provider b3-cotahist-lake --truncate-provider-before-load`
- `python scripts/run_b3_daily_job.py --user-id <id> --full-universe`
- `python scripts/run_b3_daily_job.py --user-id <id> --skip-build --skip-load --case-study-instruments PETR4,VALE3 --horizon-bars 8`

## Quick Test (Real Data, No Mock)
1. Start app: `python -m uvicorn app.main:app --app-dir services/api --reload`
2. Open `http://127.0.0.1:8000/`
3. In `Onboarding`, create account to obtain `user_id` + auth token in session.
4. In `Mercado`, run `Baixar historico completo B3` (escolha janela de anos e limite de ativos).
5. In `Mercado`, run `Buscar noticias reais` (periodo + tickers).
6. Click `Atualizar saude/cobertura feed` and then `Dashboard > Atualizar dashboard`.
7. In `Game`, start `5 teses` and play thesis-by-thesis com dados historicos reais.

## Publicacao gratuita (Vercel + Supabase)
Este e o caminho recomendado para publicar sem Render pago.

1. Suba este projeto para um repositorio GitHub.
2. Crie um projeto Supabase e copie a string de conexao Postgres.
3. No Vercel, importe o repositorio.
4. Em `Settings > Environment Variables`, configure:
   - `DATABASE_URL`: string Postgres do Supabase.
   - `FINNHUB_API_TOKEN` (opcional, intraday real).
   - `BRAPI_TOKEN` (opcional, fundamentos externos).
5. Faca deploy e abra `/health` na URL publica.

Resultado:
- Frontend e API FastAPI rodam na Vercel via [`index.py`](index.py).
- O banco persistente fica no Supabase.
- A pasta `data/` em producao e transitoria (`/tmp`) e nao deve guardar dados importantes.

Observacao sobre B3 historico:
- Os arquivos historicos B3/COTAHIST nao fazem parte da publicacao.
- Eles servem apenas para exercicios locais de teses historicas.
- Em producao, o app deve usar dados leves no banco ou provedores externos sob demanda.

## Publicacao com Render (opcional, pago quando exigir disco)
O arquivo [`render.yaml`](render.yaml) continua disponivel para uma versao com servidor
persistente e disco em `/var/data`, mas esse caminho pode exigir plano pago quando
houver necessidade de disco persistente.

## Real Intraday Provider (Finnhub)
- Set token in shell before running app/worker:
  - PowerShell: `$env:FINNHUB_API_TOKEN="seu_token"`
- Intraday live exige token; sem token o endpoint retorna erro de validacao.
- Then use `provider=finnhub` in UI or worker scripts.

## Real Fundamentals Provider (Auto: Yahoo/Brapi)
- Default mode: `provider=auto` (tenta Yahoo e fallback para Brapi).
- Para cobertura ampla no Brapi, configure token:
  - PowerShell: `$env:BRAPI_TOKEN="seu_token"`
  - Alternativa: criar `token.txt` na raiz do projeto (ou na pasta pai) contendo apenas o token.

## Gamification Test Pack
- Endpoint: `POST /api/theses/game-simulation`
- Endpoint UI game (5 teses com contexto + imagens): `POST /api/theses/game-playbook`
- Endpoint aprendizado da skill de tese: `POST /api/theses/skill/learn`
- Endpoint data quality gate: `GET /api/data-quality/gate`
- Estado da politica ativa/shadow: `data/thesis_policy_state.json`
- Default players when `players` is omitted:
  - `Andre`: `auto_conservative`
  - `Enzo`: `auto_aggressive`
- Output includes:
  - 10 teses com data de levantamento, entrada, saida, expectativa e resultado efetivo
  - Opcoes `A/B/C` por tese com risco/retorno esperado e realizado
  - Decisoes de seguir/nao seguir e `%` de alocacao por jogador
  - Carteira inicial/final e ranking de rendimento
  - Contexto historico por data da tese (fato + imagem com fonte externa)
  - Retroalimentacao automatica de confianca + blindspots em `data/thesis_skill_profile.json`

## Next Recommended Steps
1. Expand RF-05 with source-level trend visualizations in the UI and timeline drill-down per article.
2. Replace the current pricing stub in paper trading with point-in-time execution based on latest market data.
3. Add richer risk rules, circuit breakers and explainability traces for signals.
4. Grow the contract suite from JSON schema checks into generated OpenAPI artifact validation.
