# ADR-0002: Plataforma modular orientada a eventos

## Status
Accepted

## Contexto
A EF descreve a plataforma como um conjunto de dominios desacoplados, comunicando-se por barramento de eventos e APIs internas. Os fluxos de ingestao, feature engineering, anti-hype, IA, risco e simulacao exigem propagacao assicrona e auditavel de fatos.

## Decisao
- A arquitetura de referencia sera modular e orientada a eventos.
- Fatos de dominio serao publicados em contratos formais dentro de `specs/events/`.
- APIs sincronas serao reservadas para operacoes de consulta, administracao e interacoes de usuario.
- Cada dominio mantem suas responsabilidades e evita acoplamento direto a bancos de outros dominios.

## Consequencias
- Contratos de eventos tornam-se artefatos de primeira classe.
- Testes de contrato precisam validar compatibilidade entre produtores e consumidores.
- O backlog deve favorecer slices que cortam um fluxo de negocio inteiro, nao camadas tecnicas soltas.

## Alternativas consideradas
- Monolito transacional com integracao interna por chamadas diretas.
- Plataforma puramente orientada a REST.

## Motivo para rejeicao das alternativas
Ambas dificultam desacoplamento, auditoria assicrona e evolucao dos dominios que processam grandes volumes de dados de mercado.
