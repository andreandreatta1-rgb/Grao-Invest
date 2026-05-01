# RF-10 Task 02: Custos operacionais e slippage

## Objetivo
Adicionar modelagem inicial de spread, slippage e custos operacionais ao fluxo de paper trading.

## Artefatos tocados
- `services/`
- `specs/sql/`
- `tests/unit/`
- `tests/e2e/`

## Criterios de aceitacao
```gherkin
Scenario: Execucao simulada com friccao
  Given uma ordem paper elegivel
  When a simulacao calcula a execucao
  Then spread, slippage e custos configurados sao aplicados
  And a memoria de calculo fica auditavel
```

## Testes a escrever
- Calculo de slippage
- Aplicacao de custos
- Persistencia da memoria de calculo

## Definition of Done
- Friccoes integradas ao happy path
