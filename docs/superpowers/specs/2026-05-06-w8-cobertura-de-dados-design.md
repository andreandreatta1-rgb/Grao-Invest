# W8 - Cobertura De Dados

## Objetivo

Garantir que o usuario veja uma experiencia honesta sobre a prontidao dos dados usados pelo Metodo Grao. A app deve separar dados frescos de mercado, noticias, fundamentos, macro e historico, mostrando com clareza quando uma tese e apenas tecnica, quando esta parcialmente confirmada e quando existe cobertura suficiente para aumentar confianca.

## Contexto Atual

- O refresh horario via GitHub Actions ja acorda o backend e atualiza dados de mercado cripto.
- O monitor atual deixou de ficar congelado e passou a gerar teses novas com `fresh_instruments`.
- As teses ainda aparecem com `fundamental_available=false`, `news_available=false` e suporte neutro em `50.0`.
- O backend ja possui `/api/ops/data-context-refresh` para sincronizar fundamentos e noticias.
- A UI ainda pode transformar ausencia de dado em score neutro, o que enfraquece a confianca do usuario.

## Principios

1. Ausencia de dado nao deve parecer confirmacao neutra.
2. Cada tese deve carregar o estado de prontidao das fontes que a sustentam.
3. Frequencia de atualizacao deve respeitar a natureza da fonte: preco e rapido; fundamento e lento.
4. O usuario deve entender por que uma tese esta em atencao sem abrir JSON ou logs.
5. O MVP continua educacional e nao publica decisao automatica.

## Escopo

### Incluido

- Adicionar um segundo GitHub Actions workflow para chamar `/api/ops/data-context-refresh`.
- Atualizar contexto de noticias e fundamentos em agenda propria.
- Enriquecer o contrato normalizado da UI com uma matriz de cobertura por frente/fonte.
- Trocar copy de `50% neutro` por estados explicitos: `sem fonte`, `nao aplicavel`, `desatualizado`, `atualizado`.
- Mostrar na UI uma area de saude/cobertura de dados para Mercado, Historico, Noticias, Fundamentos e Macro.
- Manter a tela de teses explicando quando a hipotese e "tecnica apenas".

### Fora De Escopo

- Contratar Vercel Pro.
- Criar streaming em tempo real.
- Transformar o app em recomendacao de investimento.
- Adicionar ordem real ou execucao automatica.
- Resolver todos os providers pagos de uma vez.

## Alternativas Consideradas

### A. So aumentar frequencia do refresh atual

Mais simples, mas insuficiente. Atualiza preco, porem continua deixando noticias e fundamentos ausentes.

### B. Criar workflows separados por tipo de dado

Recomendado. Mercado roda com frequencia maior; noticias/fundamentos rodam em janelas menos agressivas. Fica mais facil auditar falhas e ajustar custo.

### C. Migrar todo o motor de dados para outro provedor

Mais robusto no longo prazo, mas maior custo e escopo agora. Pode virar W9 ou fase posterior.

## Design Recomendado

### Workflows

1. `microtrades-refresh.yml`
   - Ja existente.
   - Roda de hora em hora.
   - Chama `/api/ops/microtrades-data-refresh`.
   - Mantem preco e candles frescos.

2. `data-context-refresh.yml`
   - Novo workflow.
   - Roda duas vezes ao dia, por exemplo `11:30 UTC` e `21:30 UTC`.
   - Chama `/api/ops/data-context-refresh`.
   - Query inicial:
     - `run_fundamentals=true`
     - `run_news=true`
     - `max_instruments=10`
     - `news_lookback_days=3`
     - `max_articles_per_instrument=20`
     - `fundamentals_provider=auto`
     - `fundamentals_only_missing=false`

### Frequencias

- Cripto mercado: horario no MVP.
- B3 mercado: diario ou em janela de pregao, quando a ingestao B3 estiver estabilizada.
- Noticias: duas vezes ao dia.
- Fundamentos: diario, com tolerancia maior de staleness.
- Macro/cambio: diario em fase posterior.
- Imoveis: manual/semanal, pois depende de dados menos liquidos e diligencia.

## Contrato De Dados Para UI

A normalizacao do cockpit deve expor:

```json
{
  "coverage": {
    "market": {"status": "fresh", "label": "Mercado atualizado"},
    "history": {"status": "fresh", "label": "Historico disponivel"},
    "news": {"status": "missing", "label": "Noticias sem cobertura recente"},
    "fundamentals": {"status": "not_applicable", "label": "Fundamentos nao aplicaveis para cripto"},
    "macro": {"status": "missing", "label": "Macro ainda nao conectado"}
  }
}
```

Status aceitos:

- `fresh`: atualizado e usado no calculo.
- `stale`: existe, mas esta velho.
- `missing`: deveria existir, mas nao chegou.
- `not_applicable`: nao faz sentido para aquele ativo/frente.
- `disabled`: fonte fora do MVP atual.

## Comportamento Na UI

### Dashboard

Adicionar um bloco compacto de cobertura:

- Mercado: atualizado.
- Historico: atualizado.
- Noticias: sem cobertura recente ou atualizado.
- Fundamentos: nao aplicavel para cripto, pendente para B3.
- Macro: fora do MVP ou pendente.

### Teses

Cada card deve explicar a qualidade da tese:

- "Tese tecnica com mercado fresco."
- "Faltam noticias recentes para confirmar contexto."
- "Fundamentos nao se aplicam a este par cripto."
- "Confianca reduzida por lacunas de confirmacao."

### Saude

Mostrar a ultima execucao de cada workflow:

- `microtrades-data-refresh`
- `data-context-refresh`
- resultado: `success`, `partial`, `failed`
- problemas principais.

## Error Handling

- Se `data-context-refresh` falhar, a UI nao deve derrubar a app.
- Se noticias falharem, mostrar `Noticias sem cobertura recente`.
- Se fundamentos nao se aplicarem a cripto, mostrar `Nao aplicavel`, nao `50%`.
- Se provider responder parcial, registrar `partial` e expor problema em Saude.
- Se o GitHub Secret faltar, o workflow falha com mensagem explicita.

## Testes

- Teste estatico do novo workflow.
- Teste de endpoint `data-context-refresh` com HTTP mockado para fundamentos/noticias.
- Teste do adapter do cockpit para transformar lacunas em `missing/not_applicable`.
- Teste de UI garantindo que `50%` nao aparece como confirmacao quando a fonte esta ausente.
- Smoke manual no GitHub Actions apos cadastrar secret.

## Criterio De Aceite

- Mercado cripto segue fresco apos o workflow horario.
- Contexto de dados roda automaticamente ao menos duas vezes ao dia.
- Uma tese cripto nao mostra fundamentos como `50% neutro`; mostra `nao aplicavel` ou `sem fonte`.
- A tela explica por que a tese esta em atencao.
- A tela Saude mostra se o problema e de preco, noticias, fundamentos ou macro.
