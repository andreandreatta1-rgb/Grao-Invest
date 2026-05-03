# Cockpit Halley — Design Spec

Data: 2026-05-03
Produto: Grão Invest
Fatia: Cockpit Halley
Status: design em revisão do usuário antes do plano de implementação

## 1. Decisão estratégica

O Grão Invest passa a ser apresentado como uma plataforma-laboratório de teses de investimento baseada no método científico. A nova experiência principal será construída em React/PWA, usando a aplicação atual como acelerador técnico e de dados. O app Android atual permanece como beta operacional, sem ser descartado, mas não será o eixo principal da nova experiência nesta fase.

A primeira fatia será o Cockpit Halley: uma tela executiva para demonstrar, com simplicidade e credibilidade, se o motor Halley está aprendendo com os exercícios históricos e com as teses em go-live.

A direção visual aprovada é Placar Científico, com uma pitada de Mesa do Patrick Jane. Isso significa: primeiro números, evidências e método; depois narrativa contextual curta, calma e elegante.

## 2. Posicionamento do produto

O produto não deve soar como recomendação de investimento. Deve soar como laboratório de hipóteses.

Fluxo conceitual obrigatório:

```text
Hipótese -> Evidência -> Backtest -> Validação ou Refutação -> Go-live -> Aprendizado
```

Termos preferidos: tese, hipótese, evidência, backtest, expectância, ciclo, go-live, refutar, validar, método, rigor, motor, laboratório, calibração, padrão.

Termos proibidos na experiência: vai subir, certeza, garanto, compre agora, última chance, lucro fácil, oportunidade imperdível.

O game simulator não deve ser usado daqui para frente como fonte de narrativa ou resultado principal. Os resultados devem vir de case study histórico, current monitor, monitoramento go-live e loops de aprendizado.

## 3. Objetivo da tela

O Cockpit Halley deve responder rapidamente a quatro perguntas executivas:

1. Quantas teses já foram testadas pelo laboratório?
2. O histórico indica que o método tem algum poder de seleção?
3. Quais hipóteses estão vivas agora em go-live?
4. O que o motor aprendeu e já está aplicando nas próximas teses/operações?

A tela deve evitar poluição. O primeiro nível é resumo executivo. O detalhe aparece apenas por drill-down leve ao clicar em uma tese, frente ou aprendizado.

## 4. Estrutura da tela

### 4.1 Topo

Componente PatrickJane no estado `reporting`, acima dos KPIs.

Mensagem-modelo:

> O Halley revisou o laboratório e as hipóteses em go-live. O histórico indica onde o método tem força; as teses abertas mostram onde ainda estamos coletando evidência. O plano foi seguido. Aprendizado registrado.

Regras:

- A mensagem deve ser curta.
- Deve usar voz de método, não voz de recomendação.
- Não deve comemorar resultado sem evidência forte.
- Não deve pedir compra, venda ou urgência.

### 4.2 KPIs científicos

Grid canônico: `repeat(5, 1fr)`, gap 12, componente KPICard.

KPIs iniciais:

1. Teses testadas
   - Valor: total acumulado de teses históricas com resultado.
   - Accent: `C.purple`.
   - Sub: "laboratório histórico".

2. Validação histórica
   - Valor: percentual de teses com desfecho entendido como sucesso.
   - Accent e valueColor: `C.teal` quando `validatedPct >= 55`, `C.amber` quando `50 <= validatedPct < 55`, `C.coral` quando `validatedPct < 50`.
   - Sub: "não é garantia futura".

3. Expectância líquida
   - Valor: média percentual líquida ponderada por tese, positiva ou negativa.
   - Positivo: `C.teal`; negativo: `C.coral`.
   - Sub: "ganho/perda médio por hipótese".

4. Teses em go-live
   - Valor: quantidade de hipóteses abertas pós kickoff de 27/04/2026.
   - Accent: `C.sky`.
   - Sub: "coletando evidência".

5. Aprendizados aplicados
   - Valor: quantidade de dores/remédios ativos no motor.
   - Accent: `C.gold`.
   - Sub: "calibração do Halley".

### 4.3 Frentes de atuação

Cards compactos para B3, Cripto e Imóveis.

Cada card deve mostrar:

- Nome da frente.
- Teses testadas.
- Teses em go-live.
- Validação histórica.
- Status do dado: atualizado, parcial, indisponível ou em calibração.

Sem detalhes longos no primeiro nível.

### 4.4 Teses em go-live

Cards de hipóteses abertas usando ThesisCard como base visual, adaptado somente por composição, não reescrito.

Cada card deve mostrar:

- Número real da tese.
- Frente: B3, Cripto ou Imóveis.
- Ativo ou objeto analisado.
- Hipótese em linguagem simples.
- Preço/valor de entrada.
- Preço/valor atual.
- Alvo.
- Stop ou limite de invalidação.
- Percentual esperado.
- Percentual atual.
- Dias aberta.
- Status.

Ao clicar no card, abrir drill-down leve com:

- Evidências principais.
- Por que virou tese.
- Estrutura da operação.
- O que invalida a hipótese.
- O que essa tese está ensinando ao motor.

### 4.5 Aprendizado Halley

Bloco em formato Dor -> Remédio -> Impacto esperado.

Exemplo de linha:

```text
Dor observada: Teses com bom padrão técnico falharam quando o volume não confirmou.
Remédio aplicado: exigir confirmação mínima de volume antes de elevar score.
Impacto esperado: reduzir entradas em falsos rompimentos.
```

Esse bloco deve demonstrar que o sistema está aprendendo. Não basta categorizar palavras soltas como "janela da tese" ou "stop antecipado". A tela precisa explicar sintoma e resposta prática.

## 5. Modelo de dados

A tela deve consumir um objeto normalizado, mesmo que inicialmente montado no frontend a partir de endpoints existentes.

```js
{
  scientificSummary: {
    testedTheses,
    validatedPct,
    expectancyPct,
    goLiveCount,
    appliedLearningsCount,
    lastUpdatedAt
  },
  goLiveTheses: [
    {
      id,
      front,
      asset,
      hypothesis,
      evidence,
      entryPrice,
      currentPrice,
      targetPrice,
      stopPrice,
      expectedPct,
      currentPct,
      daysOpen,
      openedAt,
      status,
      learning,
      janeState,
      janeMessage
    }
  ],
  learningLoops: [
    {
      pain,
      remedy,
      expectedImpact,
      appliedTo,
      evidenceCount
    }
  ],
  fronts: [
    {
      id,
      label,
      tested,
      goLive,
      validatedPct,
      status,
      lastUpdatedAt
    }
  ]
}
```

### Status normalizados

| Status técnico | Label na UI | Cor |
|---|---|---|
| `monitoring` | Observando | `C.sky` |
| `near_target` | Confirmando | `C.teal` |
| `target_hit` | Validada | `C.green` |
| `stop_alert` | Alerta | `C.amber` |
| `invalidated` | Refutada | `C.coral` |
| `closed` | Fechada | `C.muted` |

### Definição de sucesso histórico

Uma tese histórica conta como sucesso quando teve resultado líquido positivo e respeitou o plano definido na abertura da hipótese. Casos de alvo atingido contam como sucesso. Casos fechados por tempo contam como sucesso somente se o resultado líquido final for positivo. Casos fechados por stop, invalidação ou resultado líquido negativo contam como refutação para o cálculo de validação histórica.

O denominador de `validatedPct` deve considerar apenas teses históricas com desfecho conhecido. Teses abertas ou sem resultado conclusivo não entram nesse percentual.

`expectancyPct` deve representar o resultado percentual líquido médio por hipótese com desfecho conhecido. A primeira versão pode usar média simples se o backend não expuser ponderação confiável; se houver tamanho financeiro por tese, a implementação deve preferir média ponderada por exposição.

## 6. Arquitetura proposta

A primeira versão deve ser implementada como React/PWA dentro da base atual, sem substituir o Android beta.

Camadas sugeridas:

```text
API existente -> normalizador Cockpit Halley -> componentes base -> tela Cockpit
```

Unidades previstas:

- `src/tokens.js`: fonte única de cores e `mono`.
- `src/components/Badge.jsx`: componente base.
- `src/components/KPICard.jsx`: componente base.
- `src/components/ThesisCard.jsx`: componente base.
- `src/components/PatrickJane.jsx`: componente base.
- `src/screens/CockpitHalley.jsx`: composição da tela.
- `src/data/cockpitHalleyAdapter.js`: normaliza dados dos endpoints atuais.

O adapter deve proteger a UI de diferenças entre B3, Cripto e Imóveis. A tela não deve conhecer detalhes crus de cada endpoint.

## 7. Fontes de dados iniciais

Endpoints já verificados como ativos:

- `/health`
- `/api/dashboard/summary/1`
- `/api/theses/current-monitor/latest`
- `/api/real-estate/candidates`

A primeira implementação deve usar esses endpoints quando disponíveis e aplicar fallback explícito quando algum deles falhar.

O kickoff pós go-live permanece 27/04/2026. Teses abertas pós go-live devem ser calculadas a partir dessa data quando houver data disponível.

## 8. Estados, erros e vazios

### 8.1 Loading

Mostrar cards skeleton simples em `C.panel`/`C.faint`, sem shimmer exagerado.

Mensagem PatrickJane `testing`:

> O Halley está organizando as evidências. Alguns padrões só aparecem quando deixamos os dados falarem primeiro.

### 8.2 Dados atualizados

Mostrar `lastUpdatedAt` em texto discreto no topo.

Mensagem PatrickJane `reporting`:

> O painel foi atualizado. A hipótese sugere, o histórico indica, e o plano segue documentado.

### 8.3 API indisponível

Não deixar a tela em branco.

Mostrar aviso com `C.amber`:

> Feed temporariamente indisponível. Mantendo o último retrato válido do laboratório.

Se houver cache/local seed, usar dados congelados e rotular como "último retrato válido".

### 8.4 Nenhum usuário anônimo

Esse erro não deve aparecer para o usuário final como mensagem técnica. Deve virar estado operacional:

> Acesso de laboratório ainda sem perfil padrão. O cockpit não conseguiu selecionar o conjunto de teses.

Ação futura: garantir usuário padrão/anon no backend ou remover dependência de usuário para leitura pública.

### 8.5 Sem teses abertas

Não é erro. Mostrar estado vazio:

> Nenhuma hipótese em go-live neste momento. O laboratório continua testando o histórico; uma nova tese só entra em campo quando houver evidência suficiente.

### 8.6 Frente parcial

Se B3, Cripto ou Imóveis estiver sem dados, mostrar card da frente como `em calibração`, não esconder.

### 8.7 Erro de encoding/acento

Requisito obrigatório: todos os arquivos novos devem ser UTF-8. A experiência não pode exibir mojibake, ou seja, palavras com acento renderizadas como caracteres corrompidos.

Teste manual obrigatório: validar labels com acentos em tela: Ações, Operações, Imóveis, Hipótese, Evidência, Validação, Refutação.

### 8.8 Números inválidos

Nunca exibir `NaN`, `undefined`, `null` ou número cru sem formatação.

Fallbacks:

- Percentuais ausentes: `--%`.
- Valores monetários ausentes: `R$ --`.
- Datas ausentes: `--`.
- Dias abertos ausentes: `-- d`.

## 9. Regras de UI/UX

- Primeiro nível deve caber como cockpit executivo, sem textos longos.
- Textos ricos ficam no drill-down.
- Clique em card ou linha abre detalhe; clicar novamente fecha.
- Não usar botão separado de "ver detalhes" quando a própria linha/card puder funcionar como controle.
- Não usar `position: fixed`.
- Não usar fundo claro.
- Não usar Tailwind nem CSS externo.
- Não hardcodar hex fora de `C`.
- Todos os valores numéricos usam `mono`.
- Cores devem seguir semântica, não estética.

## 10. Critérios de sucesso

A primeira versão será considerada bem-sucedida se:

1. Um executivo entender em menos de 30 segundos: total testado, validação histórica, expectância, teses abertas e aprendizados aplicados.
2. O usuário conseguir abrir uma tese e entender por que ela existe, qual é o plano e o que invalida a hipótese.
3. O bloco de aprendizado demonstrar dor, remédio e impacto esperado.
4. A tela funcionar mesmo com uma frente parcialmente indisponível.
5. Nenhum texto com acento aparecer quebrado.
6. Nenhuma mensagem soar como recomendação de compra/venda.

## 11. Testes necessários

### 11.1 Unitários

- Adapter normaliza payload completo.
- Adapter lida com endpoints parciais.
- Adapter calcula `goLiveCount` com kickoff em 27/04/2026.
- Adapter calcula dias abertos como inteiro.
- Adapter aplica fallback para números ausentes.
- Status técnico vira label/cor correta.

### 11.2 Componentes

- KPICard renderiza valor, sub e accent corretos.
- PatrickJane não recebe estado inválido sem fallback.
- Drill-down abre e fecha no clique do card/linha.
- ThesisCard não quebra layout com textos longos.

### 11.3 Integração

- Tela renderiza com todos endpoints disponíveis.
- Tela renderiza com `/api/theses/current-monitor/latest` indisponível.
- Tela renderiza com `/api/real-estate/candidates` indisponível.
- Tela exibe cache/seed quando API falha.

### 11.4 Visual/manual

- Validar desktop e mobile estreito.
- Validar acentos em português.
- Validar que textos longos ficam recolhidos.
- Validar que B3, Cripto e Imóveis aparecem mesmo com dados parciais.
- Validar que não aparece "game" como fonte de tese.

## 12. Fora de escopo desta fatia

- Reescrever o app Android nativo.
- Criar onboarding completo.
- Criar autenticação.
- Criar recomendação de investimento.
- Automatizar ordens reais.
- Criar push notifications.
- Substituir todos os dashboards existentes.

## 13. Pendências conscientes para a implementação

- Confirmar se o novo AGENTS.md estratégico substituirá o AGENTS.md atual do repo, que está com acentos quebrados em alguns trechos.
- Definir se `CockpitHalley.jsx` entra como tela inicial ou como rota separada durante beta.
- Confirmar se o endpoint de dashboard histórico já expõe todos os campos necessários para expectância líquida e total de teses testadas.
- Confirmar o formato final dos dados de Imóveis para alinhar com B3 e Cripto.

## 14. Próximo passo após aprovação

Após revisão e aprovação desta spec pelo usuário, criar um plano de implementação detalhado com etapas pequenas, testes e pontos de rollback. Nenhuma implementação deve começar antes desse plano.
