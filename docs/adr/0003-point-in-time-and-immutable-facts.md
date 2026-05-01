# ADR-0003: Point-in-time e fatos imutaveis

## Status
Accepted

## Contexto
Backtests, forward testing e explicacoes auditaveis perdem validade se qualquer pipeline consultar dados futuros ou sobrescrever fatos historicos. A EF estabelece point-in-time, imutabilidade de fatos e trilha de auditoria como principios centrais.

## Decisao
- Ticks, candles, noticias, trades simulados e eventos de auditoria sao append-only.
- Correcoes de dados devem ser registradas como novas versoes.
- Entidades derivadas relevantes devem carregar `reference_time` e `availability_time` ou equivalente.
- Consultas historicas devem passar por helper ou repositorio com `as_of(timestamp)`.

## Consequencias
- O desenho de storage e APIs precisa suportar versionamento temporal.
- Testes de leakage tornam-se obrigatorios.
- Refactors que simplificam o acesso a dados mas removem semantics temporais nao sao aceitaveis.

## Alternativas consideradas
- Atualizacao in-place de fatos historicos.
- Point-in-time apenas no motor de backtest.

## Motivo para rejeicao das alternativas
Ambas permitem vazamento temporal e comprometem reproduzibilidade, auditoria e confianca estatistica.
