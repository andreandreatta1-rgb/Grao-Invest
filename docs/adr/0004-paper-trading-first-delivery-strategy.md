# ADR-0004: Estrategia de entrega paper-trading-first

## Status
Accepted

## Contexto
A especificacao funcional sugere um roadmap orientado a risco, com validacao tecnica e regulatoria antes de qualquer execucao real. O produto precisa demonstrar valor com simulacao robusta antes de ampliar escopo.

## Decisao
- O roadmap inicial sera implementado em slices verticais que destravam um fluxo fim a fim de simulacao.
- As primeiras frentes preferenciais sao:
  - RF-01 onboarding e MFA
  - RF-03 ingestao de mercado com provedor stub
  - RF-07 analise tecnica com poucos indicadores reais
  - RF-10 paper trading happy path

## Consequencias
- O repositrio prioriza tarefas orientadas a resultado.
- Camadas horizontais so devem surgir quando exigidas por um slice.
- Validacao de progresso fica mais objetiva para produto, arquitetura e compliance.

## Alternativas consideradas
- Construir todas as fundacoes tecnicas antes de qualquer fluxo completo.
- Atacar o motor de IA antes de onboarding e ingestao confiavel.

## Motivo para rejeicao das alternativas
Essas abordagens escondem risco, prolongam feedback e reduzem clareza sobre valor entregue.
