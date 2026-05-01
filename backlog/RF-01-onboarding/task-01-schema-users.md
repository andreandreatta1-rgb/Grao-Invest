# RF-01 Task 01: Schema de usuarios, tenants e identidade

## Objetivo
Criar o esquema inicial de identidade para onboarding multiusuario, incluindo tenant, user, credenciais e trilha de consentimento LGPD.

## Artefatos tocados
- `specs/sql/`
- `specs/openapi/` ou `specs/graphql/`
- `tests/contract/`

## Criterios de aceitacao
```gherkin
Scenario: Criacao de usuario com tenant
  Given um novo cadastro valido
  When o usuario conclui o signup
  Then o sistema cria tenant e user com isolamento logico
  And registra consentimento LGPD com timestamp
```

## Testes a escrever
- Contrato do schema de identidade
- Restricao de unicidade e tenancy
- Validade minima de trilha de consentimento

## Definition of Done
- Contratos aprovados em `specs/`
- Testes de contrato criados
- Nenhuma regra anti-recomendacao violada
