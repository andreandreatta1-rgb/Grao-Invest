# ADR-0005: Stack do MVP funcional

## Status
Accepted

## Contexto
O repositório ainda não tinha stack implementada, mas a EF exige um loop curto de entrega para onboarding, ingestão, análise técnica, paper trading, auditoria e guardrails. Precisamos de uma base funcional com baixo atrito operacional para validar o Phase 1.

## Decisao
- Backend em Python com FastAPI.
- Persistência local inicial em SQLite via SQLAlchemy.
- Interface web simples servida pelo próprio backend, evitando desacoplamento prematuro.
- Contratos internos definidos por modelos Pydantic e schemas versionados em `specs/`.
- Execução local com `uvicorn`.

## Consequencias
- O MVP fica fácil de subir e testar.
- Algumas decisões de escala ficam diferidas para fases posteriores, sem violar os ADRs já aceitos.
- A arquitetura continua modular, mas num deployment simplificado para acelerar o slice vertical.

## Alternativas consideradas
- Backend Node.js + frontend React desde o primeiro commit.
- Microsserviços distribuídos desde o início.

## Motivo para rejeicao das alternativas
As alternativas aumentariam complexidade operacional antes de validarmos os fluxos principais e os guardrails regulatórios do produto.
