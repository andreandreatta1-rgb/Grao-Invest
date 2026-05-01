# RF-10 Task 01: Happy path de ordem simulada

## Objetivo
Materializar um fluxo completo de ordem simulada, do sinal aceito pelo risco ate a atualizacao do portfolio.

## Artefatos tocados
- `services/`
- `specs/events/`
- `tests/e2e/`

## Criterios de aceitacao
```gherkin
Scenario: Ordem paper executada
  Given um sinal aprovado e um portfolio elegivel
  When o motor de simulacao materializa a ordem
  Then a posicao e atualizada
  And custos e impostos basicos sao aplicados
  And a trilha de auditoria registra o fluxo completo
```

## Testes a escrever
- Fluxo feliz fim a fim
- Atualizacao de posicao
- Evento de auditoria

## Definition of Done
- Fluxo e2e funcional
- Auditoria e custos integrados
