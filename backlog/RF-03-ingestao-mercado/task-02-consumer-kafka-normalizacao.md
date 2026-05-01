# RF-03 Task 02: Consumer de ticks com normalizacao

## Objetivo
Consumir ticks do provedor primario, normalizar para o schema canonico `MarketTick` e publicar no topico interno versionado.

## Artefatos tocados
- `services/ingestion-market/`
- `specs/events/`
- `tests/unit/`
- `tests/contract/`
- `tests/fixtures/`

## Criterios de aceitacao
```gherkin
Scenario: Tick do provedor primario e normalizado
  Given um tick valido do provedor primario
  When o consumer processa a mensagem
  Then o evento canonico e publicado no topico interno
  And o payload segue exatamente o schema aprovado
```

## Testes a escrever
- Normalizacao por fixture
- Contrato contra o schema
- Tratamento de mensagens invalidas

## Definition of Done
- Consumer criado
- Testes verdes
- Nenhuma alteracao opportunistica em `specs/events/`
