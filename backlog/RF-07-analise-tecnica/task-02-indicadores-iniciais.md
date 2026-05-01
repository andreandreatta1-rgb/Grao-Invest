# RF-07 Task 02: Indicadores iniciais reais

## Objetivo
Implementar tres indicadores tecnicos reais para validar o pipeline de series e features: `SMA`, `EMA` e `RSI`.

## Artefatos tocados
- `services/`
- `tests/unit/`
- `tests/e2e/`

## Criterios de aceitacao
```gherkin
Scenario: Calculo de indicadores sobre serie valida
  Given uma serie historica conhecida
  When o motor calcula SMA, EMA e RSI
  Then os resultados batem com fixtures aprovadas
  And cada feature fica disponivel com metadata temporal
```

## Testes a escrever
- Fixtures numericas dos indicadores
- Disponibilidade temporal da feature
- Tratamento de janelas insuficientes

## Definition of Done
- Tres indicadores entregues com testes
