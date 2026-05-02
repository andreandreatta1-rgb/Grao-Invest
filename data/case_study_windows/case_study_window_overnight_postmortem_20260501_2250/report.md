# Relatorio da Janela de Case Study

- run_id: case_study_window_overnight_postmortem_20260501_2250
- inicio_local: 2026-05-01T22:50:38-03:00
- fim_local: 2026-05-02T07:10:38-03:00
- duracao_planejada_min: 500.0
- duracao_real_min: 500.0

## KPIs Consolidados
- iteracoes_totais: 1055
- case_studies_concluidos: 1055
- falhas: 0
- engine_success_rate_pct: 100.0
- thesis_success_rate_pct: 77.82
- avg_confidence_tese_pct: 74.6171
- avg_expected_financial_pct: 4.1571
- avg_realized_financial_pct: 3.0792
- expected_vs_real_gap_pct: -1.0779
- avg_iteration_duration_seconds: 18.4368
- unique_theses: 748
- unique_instruments: 14

## Distribuicao
- top_instruments: [('PETR4', 337), ('PRIO3', 206), ('HAPV3', 168), ('BPAC11', 102), ('SUZB3', 70)]
- top_strategies: [('Bull Call Spread', 866), ('Bear Put Spread', 189)]
- policies_seen: [('anti_blindspot_v3_soft', 1055)]
- top_postmortem_tags: [('missing_confirmation_inputs', 705), ('expected_overstretch_without_confirmation', 681), ('low_support_rate_band', 681), ('confidence_overweighted_by_technical', 331), ('expected_real_gap_negative', 234), ('repeat_failure_signature', 229), ('early_invalidation', 163), ('risk_cluster_high', 127)]
- top_learning_actions: [('shadow_rule::missing_confirmation_inputs', 705), ('shadow_rule::confidence_overweighted_by_technical', 331), ('shadow_rule::expected_real_gap_negative', 234), ('shadow_rule::repeat_failure_signature', 229), ('shadow_rule::early_invalidation', 163)]

## Melhores Casos
- iter=1 | PRIO3 | Bull Call Spread | conf=72.52% | esp=3.92% | real=5.40%
  sinais: momento_bullish_7.62pct, volatilidade_1.99pct, suporte_historico_35.78pct, suporte_tecnico_95.00pct, suporte_fundamental_50.00pct
  postmortem: missing_confirmation_inputs
- iter=11 | JBSS3 | Bull Call Spread | conf=71.17% | esp=3.77% | real=5.40%
  sinais: momento_bullish_8.26pct, volatilidade_2.37pct, suporte_historico_29.40pct, suporte_tecnico_95.00pct, suporte_fundamental_50.00pct
  postmortem: confidence_overweighted_by_technical, expected_overstretch_without_confirmation, low_support_rate_band, missing_confirmation_inputs
- iter=12 | PRIO3 | Bull Call Spread | conf=72.52% | esp=3.92% | real=5.40%
  sinais: momento_bullish_7.62pct, volatilidade_1.99pct, suporte_historico_35.78pct, suporte_tecnico_95.00pct, suporte_fundamental_50.00pct
  postmortem: missing_confirmation_inputs

## Piores Casos
- iter=6 | BPAC11 | Bull Call Spread | conf=71.35% | esp=3.79% | real=-2.20%
  sinais: momento_bullish_7.53pct, volatilidade_2.14pct, suporte_historico_30.26pct, suporte_tecnico_95.00pct, suporte_fundamental_50.00pct
  postmortem: confidence_overweighted_by_technical, early_invalidation, expected_overstretch_without_confirmation, expected_real_gap_negative, low_support_rate_band, missing_confirmation_inputs, risk_cluster_high, structure_limited_loss
- iter=21 | GGBR4 | Bull Call Spread | conf=70.48% | esp=3.69% | real=-2.20%
  sinais: momento_bullish_8.70pct, volatilidade_2.23pct, suporte_historico_26.14pct, suporte_tecnico_95.00pct, suporte_fundamental_50.00pct
  postmortem: confidence_overweighted_by_technical, early_invalidation, expected_overstretch_without_confirmation, expected_real_gap_negative, low_support_rate_band, missing_confirmation_inputs, risk_cluster_high, structure_limited_loss
- iter=26 | BPAC11 | Bull Call Spread | conf=71.35% | esp=3.79% | real=-2.20%
  sinais: momento_bullish_7.53pct, volatilidade_2.14pct, suporte_historico_30.26pct, suporte_tecnico_95.00pct, suporte_fundamental_50.00pct
  postmortem: confidence_overweighted_by_technical, early_invalidation, expected_overstretch_without_confirmation, expected_real_gap_negative, low_support_rate_band, missing_confirmation_inputs, repeat_failure_signature, risk_cluster_high

## Artefatos
- report_json_file: C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\ProjectOne - Copia\data\case_study_windows\case_study_window_overnight_postmortem_20260501_2250\report.json
- report_md_file: C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\ProjectOne - Copia\data\case_study_windows\case_study_window_overnight_postmortem_20260501_2250\report.md
- history_file: C:\Users\Andreatta\OneDrive - Oracle Corporation\Andreatta OD\Pessoal\A Projetos\Assistente de Investimento\ProjectOne - Copia\data\case_study_windows\case_study_window_overnight_postmortem_20260501_2250\history.jsonl