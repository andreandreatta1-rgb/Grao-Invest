# RF-01 Task 02: Endpoint de signup

## Objetivo
Implementar o fluxo minimo de cadastro com validacao de entrada, aceite de termos e resposta padronizada.

## Artefatos tocados
- `services/`
- `specs/openapi/` ou `specs/graphql/`
- `tests/unit/`
- `tests/contract/`

## Criterios de aceitacao
```gherkin
Scenario: Signup bem-sucedido
  Given dados validos de cadastro
  When a requisicao de signup e enviada
  Then a conta e criada
  And o usuario recebe status apropriado
  And o consentimento exigido fica auditado
```

## Testes a escrever
- Validacao de payload
- Caminho feliz
- Erro para e-mail duplicado
- Contrato do endpoint

## Definition of Done
- Endpoint aderente ao contrato
- Testes unitarios e de contrato verdes
