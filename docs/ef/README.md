# Especificacao Funcional

Arquivo principal:
- `docs/ef/Especificacao_Funcional_AI_Investment_Advisor.docx`

## Resumo operacional
- Produto SaaS multiusuario para analise algoritmica, simulacao de investimentos e paper trading no mercado B3.
- Fase 1 exclui execucao real em corretora.
- A plataforma deve operar com postura explicita de anti-recomendacao e compliance by design.
- Dados historicos e features precisam respeitar rigorosamente o principio de point-in-time.
- Os primeiros modulos criticos do MVP sao onboarding, ingestao de mercado, analise tecnica, motor de IA, paper trading, risco, fiscal e auditoria.

## Como usar no fluxo de desenvolvimento
- Use a EF como referencia de negocio e restricoes.
- Congele decisoes tecnicas em ADRs antes de propagar padroes para o codigo.
- Materialize contratos em `specs/` antes de pedir implementacoes amplas.
- Puxe trabalho apenas a partir de tarefas em `backlog/`.
