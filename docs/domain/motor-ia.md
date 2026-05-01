# Dominio: Motor de IA

## Missao
Transformar features tecnicas, fundamentais e de conteudo em sinais simulados auditaveis, com governanca de modelo e explicabilidade.

## Entradas
- Features point-in-time
- Scores anti-hype
- Contexto de regime de mercado
- Parametros de risco e eligibility por usuario ou tier

## Saidas
- Sinais com nivel de confianca
- Explicacoes XAI legiveis e auditaveis
- Metricas de drift, desempenho e promocao de modelo

## Regras invariantes
- Nenhuma feature futura pode entrar em treino, validacao ou inferencia historica.
- Todo modelo promovido precisa de versao, lineage e janela de validade.
- Linguagem de saida deve respeitar a politica anti-recomendacao.
- Toda decisao automatizada precisa ser auditavel.

## Riscos principais
- Leakage temporal
- Overfitting
- Drift de distribuicao
- Prompt injection no assistente conversacional
