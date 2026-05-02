# Relatorio da Janela de Case Study

- run_id: case_study_window_postmortem_smoke
- inicio_local: 2026-05-01T22:46:22-03:00
- fim_local: 2026-05-01T22:47:38-03:00
- duracao_planejada_min: 1.1
- duracao_real_min: 1.26

## KPIs Consolidados
- iteracoes_totais: 2
- case_studies_concluidos: 2
- falhas: 0
- engine_success_rate_pct: 100.0
- thesis_success_rate_pct: 100.0
- avg_confidence_tese_pct: 76.5474
- avg_expected_financial_pct: 4.3733
- avg_realized_financial_pct: 4.2702
- expected_vs_real_gap_pct: -0.1031
- avg_iteration_duration_seconds: 37.1755
- unique_theses: 2
- unique_instruments: 2

## Distribuicao
- top_instruments: [('PRIO3', 1), ('PETR4', 1)]
- top_strategies: [('Bull Call Spread', 2)]
- policies_seen: [('anti_blindspot_v3_soft', 2)]
- top_postmortem_tags: [('missing_confirmation_inputs', 1), ('expected_overstretch_without_confirmation', 1), ('low_support_rate_band', 1)]
- top_learning_actions: [('shadow_rule::missing_confirmation_inputs', 1)]

## Melhores Casos
- iter=1 | PRIO3 | Bull Call Spread | conf=72.52% | esp=3.92% | real=5.40%
  sinais: momento_bullish_7.62pct, volatilidade_1.99pct, suporte_historico_35.78pct, suporte_tecnico_95.00pct, suporte_fundamental_50.00pct
  postmortem: missing_confirmation_inputs
- iter=2 | PETR4 | Bull Call Spread | conf=80.58% | esp=4.82% | real=3.14%
  sinais: momento_bullish_6.38pct, volatilidade_1.63pct, suporte_historico_25.99pct, suporte_tecnico_94.37pct, suporte_fundamental_95.00pct
  postmortem: expected_overstretch_without_confirmation, low_support_rate_band

## Piores Casos
- iter=2 | PETR4 | Bull Call Spread | conf=80.58% | esp=4.82% | real=3.14%
  sinais: momento_bullish_6.38pct, volatilidade_1.63pct, suporte_historico_25.99pct, suporte_tecnico_94.37pct, suporte_fundamental_95.00pct
  postmortem: expected_overstretch_without_confirmation, low_support_rate_band
- iter=1 | PRIO3 | Bull Call Spread | conf=72.52% | esp=3.92% | real=5.40%
  sinais: momento_bullish_7.62pct, volatilidade_1.99pct, suporte_historico_35.78pct, suporte_tecnico_95.00pct, suporte_fundamental_50.00pct
  postmortem: missing_confirmation_inputs

## Artefatos
- report_json_file: C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\ProjectOne - Copia\data\case_study_windows\case_study_window_postmortem_smoke\report.json
- report_md_file: C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\ProjectOne - Copia\data\case_study_windows\case_study_window_postmortem_smoke\report.md
- history_file: C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\ProjectOne - Copia\data\case_study_windows\case_study_window_postmortem_smoke\history.jsonl