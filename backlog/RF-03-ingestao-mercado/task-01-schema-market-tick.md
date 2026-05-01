# RF-03 Task 01: Schema canonico de MarketTick

## Objetivo
Definir o contrato canonico do evento `MarketTick` com semantica temporal, origem e identificacao de instrumento.

## Artefatos tocados
- `specs/events/`
- `tests/contract/`
- `docs/adr/`

## Criterios de aceitacao
```gherkin
Scenario: Publicacao de tick canonico
  Given um tick vindo de um provedor autorizado
  When o dado e normalizado
  Then o evento resultante segue o schema MarketTick
  And preserva event_time, ingest_time e source
```

## Testes a escrever
- Compatibilidade producer/consumer
- Campos obrigatorios e versionamento

## Definition of Done
- Schema aprovado e versionado
- Teste de contrato criado
