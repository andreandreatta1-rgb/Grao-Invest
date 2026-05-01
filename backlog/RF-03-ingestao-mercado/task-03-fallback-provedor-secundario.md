# RF-03 Task 03: Fallback para provedor secundario

## Objetivo
Ativar fallback auditavel quando o provedor primario degradar ou falhar acima do limiar aceito.

## Artefatos tocados
- `services/ingestion-market/`
- `specs/events/`
- `tests/e2e/`
- `docs/runbooks/`

## Criterios de aceitacao
```gherkin
Scenario: Failover controlado
  Given degradacao sustentada do provedor primario
  When o limiar de failover e atingido
  Then o sistema alterna para o provedor secundario
  And registra evento de auditoria
  And preserva a ordem temporal dos eventos publicados
```

## Testes a escrever
- Failover por limiar
- Auditoria do evento
- Reconciliacao temporal

## Definition of Done
- Failover observavel e auditavel
- Runbook atualizado
