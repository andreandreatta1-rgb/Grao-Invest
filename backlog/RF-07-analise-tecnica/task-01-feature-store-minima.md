# RF-07 Task 01: Feature store minima point-in-time

## Objetivo
Criar a base minima para persistencia e leitura point-in-time de series e features tecnicas.

## Artefatos tocados
- `specs/sql/`
- `services/`
- `tests/contract/`

## Criterios de aceitacao
```gherkin
Scenario: Consulta historica segura
  Given candles historicos e features derivadas
  When o motor consulta dados com as_of(timestamp)
  Then apenas informacoes disponiveis ate aquele instante sao retornadas
```

## Testes a escrever
- Leakage temporal
- Versionamento de feature
- Leitura por `as_of`

## Definition of Done
- Sem vazamento temporal
- Contrato temporal documentado
