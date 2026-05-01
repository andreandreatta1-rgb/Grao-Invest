# MVP OpenAPI Notes

O contrato operacional do MVP e exposto pela propria aplicacao FastAPI em:
- `/openapi.json`
- `/docs`

## Endpoints cobertos pelo MVP
- `POST /api/auth/signup`
- `POST /api/auth/login`
- `POST /api/auth/mfa/setup`
- `POST /api/auth/mfa/verify`
- `POST /api/suitability`
- `POST /api/market/providers/status`
- `GET /api/market/providers`
- `POST /api/market/ticks/ingest`
- `POST /api/market/external/b3/sync`
- `POST /api/fundamentals/ingest`
- `GET /api/fundamentals/{instrument}`
- `POST /api/news/ingest`
- `GET /api/news/sentiment/{instrument}`
- `GET /api/news/sources/{instrument}`
- `GET /api/market/ticks/{instrument}`
- `GET /api/news/{instrument}`
- `POST /api/analysis/indicators/recompute`
- `POST /api/analysis/indicators/recompute-batch`
- `GET /api/analysis/indicators/{instrument}`
- `POST /api/signals/generate`
- `POST /api/paper/orders/from-signal/{signal_id}`
- `POST /api/backtests/run`
- `GET /api/backtests/{run_id}`
- `GET /api/audit/events`
- `POST /api/alerts/rules`
- `GET /api/alerts/events/{user_id}`
- `GET /api/risk/circuit-breaker/{instrument}`
- `POST /api/risk/kill-switch`
- `GET /api/risk/kill-switch`
- `GET /api/reports/summary/{user_id}`
- `GET /api/dashboard/summary/{user_id}`
- `POST /api/theses/case-study`

## Observacoes
- O MVP evita endpoints de execucao real.
- Todo fluxo de sinal e simulacao preserva a postura anti-recomendacao.
- Endpoints de usuario (suitability, sinais, ordens paper, backtest, alertas, relatorios, dashboard, kill-switch e auditoria) exigem `Authorization: Bearer <token>` retornado em `POST /api/auth/login`.
- Consultas historicas aceitam `as_of` para respeitar point-in-time.
- O modulo de noticias aplica score anti-hype baseline e o risco pode bloquear ordens paper.
- O modulo de fundamentos preserva `reference_time` e `availability_time` para consultas point-in-time e reutilizacao em sinais.
- A ingestao de ticks passa a ser idempotente quando `source_payload_id` e informado (duplicatas sao ignoradas de forma auditavel).
- A sincronizacao externa da B3 (`/api/market/external/b3/sync`) usa `COTAHIST` oficial, valida formato fixo (245 colunas) e permite restringir ingestao a carteira pequena para validacao incremental.
- A carteira de validacao default foi ampliada para 10 ativos liquidos da B3 e o endpoint limita explicitamente o escopo a no maximo 10 ativos para controle de carga e verificacao de formato.
- A ingestao fundamentalista passa a ser idempotente por chave versionada (`instrument`, `source_name`, `source_type`, `reference_time`, `availability_time`, `version_tag`).
- O modulo de noticias agora gera classificacao estruturada com sentimento, magnitude e confianca do modelo, alem de agregacao por ticker.
- O modulo de noticias inclui historico agregado por fonte (`/api/news/sources/{instrument}`) e pode disparar alerta `news_magnitude` quando a magnitude superar o limiar configurado.
- O backtest reaproveita indicadores, sinal e risco em replay point-in-time.
- O backtest agora aplica friccoes operacionais (spread/slippage), custos e IR estimado no replay e publica snapshot de validacao com metricas de performance e robustez Monte Carlo.
- O risco agora considera exposicao agregada, drawdown guard e kill-switch persistente.
- A execucao paper aplica spread/slippage dinamicos por participacao no volume de mercado e registra memoria de calculo auditavel no evento `paper.order.executed`.
- Os sinais expostos pelo MVP carregam payload XAI estruturado e podem disparar alertas configuraveis.
- Os alertas configuraveis agora incluem gatilhos de validacao de estrategia (`backtest_return`, `backtest_drawdown`, `backtest_win_rate`) com controle de frequencia baseline.
- Dashboard e relatorio resumido incluem secao de validacao de estrategia (performance, robustez e flags de risco) para apoiar RF-15/RF-16.
- O endpoint `POST /api/theses/case-study` executa varredura historica point-in-time para levantar candidatas de tese, validar suporte estatistico, montar operacao estruturada simulada, monitorar eventos e calcular KPIs (confianca, financeiro esperado e financeiro realizado).
- A camada tecnica agora suporta batch multiativo e fatores adicionais como MACD, momentum e volatilidade.
- O pipeline de ingestao suporta failover auditavel entre provedor primario e secundario com limiar configuravel.
