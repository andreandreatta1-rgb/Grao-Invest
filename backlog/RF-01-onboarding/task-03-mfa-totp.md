# RF-01 Task 03: MFA por TOTP

## Objetivo
Adicionar MFA por TOTP para usuarios elegiveis, com bootstrap seguro, verificacao e revogacao.

## Artefatos tocados
- `services/`
- `specs/openapi/` ou `specs/graphql/`
- `tests/unit/`
- `tests/e2e/`

## Criterios de aceitacao
```gherkin
Scenario: Habilitacao de TOTP
  Given um usuario autenticado
  When ele habilita MFA
  Then o sistema gera segredo e desafio de verificacao
  And somente apos validacao MFA fica ativo
```

## Testes a escrever
- Bootstrap do segredo
- Validacao de codigo
- Revogacao segura
- Caminho de login com step-up

## Definition of Done
- MFA funcional no slice
- Eventos de auditoria gerados
