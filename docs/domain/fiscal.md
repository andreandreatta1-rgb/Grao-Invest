# Dominio: Fiscal e Custos Operacionais

## Missao
Simular impostos, emolumentos, corretagem, taxas e relatorios fiscais de forma parametrizada, auditavel e temporalmente versionada.

## Entradas
- Trades simulados
- Cadastro fiscal do usuario
- Parametros de aliquotas, taxas B3 e corretagem
- Classificacao do instrumento e modalidade da operacao

## Saidas
- Eventos de custo aplicado
- Demonstrativos mensais
- Base para relatorios exportaveis e dashboards

## Regras invariantes
- Parametros fiscais precisam ser versionados por vigencia.
- Calculos devem explicitar memoria minima para auditoria.
- O sistema estima e informa; nao substitui assessoria tributaria individualizada.
- Custos e impostos fazem parte da simulacao oficial do portfolio.

## Riscos principais
- Mudanca regulatoria sem atualizacao de parametros
- Classificacao incorreta de modalidade
- Divergencia entre simulacao e relatorio exportado
