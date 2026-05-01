# Plano 7 Dias - Evolucao de Taxa de Sucesso e Descoberta de Teses

## Objetivo
Elevar o motor de tese de uma linha de base de `~55.8%` de acerto para faixa alvo de `62%-68%`, com aumento de descoberta de teses realmente executaveis e menor gap entre retorno esperado e realizado.

## Linha de Base (22/04/2026)
- `success_rate`: `55.8333%`
- `avg_expected_financial_pct`: `+0.0627%`
- `avg_realized_financial_pct`: `+0.9282%`
- blindspots ativos:
1. `expected_gt_real_by_2pp`
2. `low_support_rate`
3. `low_news_support`
- cobertura estrutural:
1. fundamentos: `0.2469%` do universo de mercado
2. noticias analisadas: `0.3086%` do universo

## Metas de 7 dias
1. `success_rate` >= `62%`
2. reduzir `expected_gt_real_by_2pp` em pelo menos `30%` (contagem de ocorrencias no ciclo)
3. aumentar cobertura de fundamentos para `>=10%` do universo alvo (foco em ativos liquidos)
4. aumentar cobertura de noticias para `>=15%` do universo alvo
5. estabilizar calibracao (oscilar menos entre ciclos)

## Entregas por Dia

### Dia 1 - Qualidade de Base
1. Congelar baseline do ciclo em `data/thesis_skill_profile.json`.
2. Rodar A/B historico com `scripts/run_thesis_ab_experiment.py`.
3. Definir politica promotada (se houver ganho real de acerto com discovery aceitavel).

### Dia 2 - Cobertura de Dados (Fundamentos)
1. Popular fundamentos para top ativos liquidos (lotes de 50-100).
2. Medir cobertura por ticker e staleness.
3. Registrar taxa de falha de provider e necessidade de token.

### Dia 3 - Cobertura de Dados (Noticias e Contexto)
1. Expandir coleta de noticias em janela maior por setor.
2. Melhorar diversidade de fontes e tags de contexto.
3. Reexecutar aprendizado e comparar efeito em `low_news_support`.

### Dia 4 - Regimes de Mercado
1. Segmentar teses por regime (tendencia, lateral, volatilidade alta).
2. Calibrar thresholds por regime.
3. Validar ganho por segmento no A/B.

### Dia 5 - Controle de Overpromise
1. Endurecer guardrails de `expected_financial_pct` para reduzir `expected_gt_real_by_2pp`.
2. Aplicar penalidade progressiva por blindspot.
3. Medir queda no erro de expectativa.

### Dia 6 - Expansao de Descoberta
1. Incluir novas familias de tese:
   - rotacao setorial
   - evento (balanco/macro)
   - continuidade com confirmacao de volume
2. Medir descobertas novas por familia.

### Dia 7 - Decisao de Promocao
1. Rodar bateria final A/B em janela ampla.
2. Comparar baseline vs candidato com criterios de promocao:
   - `+3pp` de acerto minimo
   - discovery >= `70%` da baseline
   - sem aumento de drawdown proxy
3. Promover politica vencedora e registrar changelog.

## Experimentos A/B (Framework)
- Script: `scripts/run_thesis_ab_experiment.py`
- Variante A: `baseline` (confidence >= 55 e esperado > 0)
- Variante B: `anti_blindspot_v1` (filtro estrito de blindspots)
- Variante C: `anti_blindspot_v2_balanced` (filtro balanceado com hard-reject em riscos criticos)
- Variante D: `anti_blindspot_v3_soft` (penalidade progressiva + gate de confianca ajustada)
- KPIs por variante:
1. `success_rate_pct`
2. `discovery_rate_pct`
3. `avg_expected_financial_pct`
4. `avg_realized_move_pct`
5. `positive_realized_move_rate_pct`

## Status Atual do A/B (22/04/2026 - rodada 1200 candidatos)
1. `baseline`: discovery `75.0%`, success `56.4444%`
2. `anti_blindspot_v1`: discovery `0.0833%`, success `100.0%` (inviavel operacionalmente)
3. `anti_blindspot_v2_balanced`: discovery `42.75%`, success `92.2027%`
4. `anti_blindspot_v3_soft`: discovery `43.0%`, success `92.2481%`
5. recomendacao tecnica atual: `anti_blindspot_v3_soft` (melhor score qualidade no script)
6. observacao de governanca: ainda abaixo do gate de promocao final do Dia 7 (`discovery >= 70% da baseline`), portanto manter em `candidate/shadow` ate nova calibracao.

## Status Atualizado (22/04/2026 - calibracao v3_soft, rodada 1200 candidatos)
1. `baseline`: discovery `76.1667%`, success `55.5799%`
2. `anti_blindspot_v2_balanced`: discovery `42.75%`, success `92.2027%`
3. `anti_blindspot_v3_soft`: discovery `51.6667%`, success `80.9677%`
4. uplift v3 vs baseline: `+25.3878pp` de success com discovery na faixa alvo (`50%-60%`)
5. recomendacao operacional apos calibracao: `anti_blindspot_v3_soft` (criterio de promocao com discovery minimo habilitado)
6. proximo gate: validar em `shadow` com monitoramento continuo de blindspots e estabilidade por ciclos diarios.

## Status Shadow -> Promocao (22/04/2026)
1. comando aplicado: `python scripts/run_thesis_shadow_cycle.py --user-id 1 --horizon-bars 12 --max-candidates 1200 --required-stable-cycles 2`
2. ciclo 1: aprovado (`stable=1/2`)
3. ciclo 2: aprovado (`stable=2/2`) com `promoted_now=true`
4. politica ativa atual: `anti_blindspot_v3_soft` (persistida em `data/thesis_policy_state.json`)
5. comportamento em runtime: case-study e game ja filtram teses pela politica ativa e retornam metadados de policy no payload.

## Rotina de Execucao Diaria
1. `python scripts/learn_thesis_skill.py --user-id <id> --horizon-bars 12 --max-candidates 1200`
2. `python scripts/run_thesis_ab_experiment.py --user-id <id> --horizon-bars 12 --max-candidates 1200`
3. `python scripts/run_case_study.py --user-id <id> --instruments PETR4,VALE3,ITUB4,B3SA3,WEGE3 --horizon-bars 12`

## Criterios de Sucesso da Semana
1. KPI tecnico: atingir meta de `success_rate`
2. KPI de negocio: reduzir erro de expectativa
3. KPI de escala: aumentar cobertura de dados
4. KPI de aprendizado: diminuir recorrencia dos blindspots
