# ADR-0001: Limite regulatorio e de produto da Fase 1

## Status
Accepted

## Contexto
A especificacao funcional determina que a Fase 1 do produto opere exclusivamente em modo de simulacao, sem execucao real em corretoras. O produto tambem precisa evitar enquadramento como recomendacao personalizada de investimento enquanto nao houver estrutura regulatoria apropriada.

## Decisao
- A Fase 1 implementa apenas analise, simulacao, paper trading, explicabilidade, auditoria e relatorios.
- Nenhum servico da Fase 1 pode enviar ordens para corretoras ou custodiar ativos.
- Todo texto gerado para usuario final deve respeitar a politica anti-recomendacao.
- Qualquer futura evolucao para execucao real exige novo ADR e gate regulatorio explicito.

## Consequencias
- Fluxos de paper trading devem ser projetados para parecer realistas, mas sem side effects externos em mercado.
- Integracoes com corretoras ficam fora do escopo tecnico imediato.
- Copy, templates e assistentes precisam ser testados contra linguagem proibida.

## Alternativas consideradas
- Permitir integracao read-only com corretoras ja na Fase 1.
- Permitir execucao opt-in por ambiente interno.

## Motivo para rejeicao das alternativas
As alternativas aumentam a superficie regulatoria e operacional antes de o produto validar governanca, seguranca e robustez estatistica.
