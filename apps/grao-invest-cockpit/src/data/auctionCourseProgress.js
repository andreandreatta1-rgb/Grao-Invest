const appInsertionByLesson = Object.freeze({
  "m01-boas-vindas": "Criar criterio de uso do curso: cada aula deve virar regra, checklist ou decisao no Radar Imobiliario.",
  "m01-aula-1": "Alimentar base de leiloeiros/fontes e classificar qualidade de origem antes de criar candidato.",
  "m01-aula-2": "Adicionar classificacao de leilao extrajudicial, risco de consolidacao e documentos minimos.",
  "m01-aula-3": "Criar filtro Pareto judicial: poucos casos com assimetria real, descartando ruidos juridicos cedo.",
  "m01-aula-4": "Refinar modalidades Caixa, etapa do imovel e regra de 2a praca versus venda direta.",
  "m01-aula-5": "Registrar canal do leilao e impacto operacional: presencial, online ou hibrido.",
  "m02-aula-1": "Separar leiloes trabalhistas por tipo de execucao, prazos e riscos de passivo.",
  "m02-aula-2": "Padronizar avaliacao online: comparaveis, liquidez local, preco conservador e evidencias.",
  "m02-aula-3": "Transformar busca de oportunidades em funil: fonte, filtro, ranking e descarte.",
  "m02-aula-4": "Fortalecer P0 de dividas: condominio, IPTU, processo, executado e responsabilidade.",
  "m03-aula-1": "Diferenciar metade do preco de preco vil e bloquear tese juridicamente fraca.",
  "m03-aula-2": "Mapear alavancagem, parcerias e arrematacao com pouco caixa dentro do risco permitido.",
  "m03-aula-3": "Criar bloco de contabilidade legal: matricula, onus, averbacoes, posse e custos.",
  "m03-aula-4": "Evoluir pre-dossie de ocupacao com sinais publicos e reserva de desocupacao.",
  "m03-aula-5": "Converter checklist do Granvas em checklist operacional da app.",
  "m04-aula-1": "Montar fluxo de primeira arrematacao: documentos, caixa, lance, pos-lance e decisao.",
  "m04-aula-2": "Refinar modelo de desocupacao: prazo, acordo, advogado, dano e reserva.",
  "m04-aula-3": "Adicionar plano de saida: venda, aluguel, liquidez, corretagem e tempo de giro.",
  "m04-aula-4": "Criar dossie de investidores para defender tese e captar capital com evidencias.",
  "m04-editais": "Transformar leitura de edital em parser/checklist: fonte, praca, pagamento, dividas e posse.",
  "m04-requerimento": "Registrar modelos como artefatos de pos-arrematacao, sem automatizar acao juridica sem revisao.",
  "m04-sem-bolso": "Mapear estruturas de arrematacao sem capital proprio e seus limites de risco.",
  "m04-distancia": "Criar fluxo remoto: documentos digitais, procuracao, diligencia e validacao local.",
  "m04-consorcio": "Avaliar carta de consorcio como frente separada de monetizacao, fora do lance padrao.",
  "m04-fim": "Fechar playbook: curso consumido, regras incorporadas e rotina de garimpo ativa.",
});

const analysisByLesson = Object.freeze({
  "m01-boas-vindas": "Analise resumida da aula: aula de onboarding e recursos de suporte. Aprendizado operacional: comunidade, nivelamento e canal de duvidas devem virar trilha de apoio, nao criterio de investimento.",
  "m01-aula-1": "Analise resumida da aula: construir base de leiloes e fonte antes de olhar oportunidades. Aprendizado operacional: sem base de fontes, o radar vira busca manual e perde repetibilidade.",
  "m01-aula-2": "Analise resumida da aula: leilao extrajudicial exige separar alienacao fiduciaria, consolidacao, prazos e documentos. Aprendizado operacional: a app precisa tratar tipo de leilao como risco estrutural.",
  "m01-aula-3": "Analise resumida da aula: judicial deve obedecer Pareto, focando poucos casos assimetricos. Aprendizado operacional: descartar cedo ruidos processuais e baixo desconto real.",
  "m01-aula-4": "Analise resumida da aula: Caixa tem regras, canais e fases proprias. Aprendizado operacional: classificar venda direta, 1a/2a praca, ocupacao e pagamento antes de calcular teto.",
  "m01-aula-5": "Analise resumida da aula: canal presencial, online ou hibrido muda execucao. Aprendizado operacional: registrar canal do leilao, requisitos de habilitacao e risco operacional.",
  "m02-aula-1": "Analise resumida da aula: leiloes trabalhistas pedem diligencia propria sobre execucao e passivos. Aprendizado operacional: criar etiqueta de justica trabalhista e checklist de riscos.",
  "m02-aula-2": "Analise resumida da aula: avaliacao online e comparaveis sustentam preco teto. Aprendizado operacional: reforcar avaliacao conservadora, fontes de comparaveis e liquidez local.",
  "m02-aula-3": "Analise resumida da aula: encontrar e selecionar ofertas e um funil, nao uma busca avulsa. Aprendizado operacional: fonte, filtro, score e descarte precisam ficar auditaveis.",
  "m02-aula-4": "Analise resumida da aula: dividas do imovel e do executado podem destruir margem. Aprendizado operacional: P0 deve exigir IPTU, condominio, processo, matricula e responsabilidade por debitos.",
  "m03-aula-1": "Analise resumida da aula: comprar barato nao basta; preco vil pode gerar risco juridico. Aprendizado operacional: diferenciar desconto economico de fragilidade legal.",
  "m03-aula-2": "Analise resumida da aula: arrematar com pouco dinheiro depende de estrutura, parceiro ou alavancagem. Aprendizado operacional: separar oportunidade imobiliaria de engenharia financeira.",
  "m03-aula-3": "Analise resumida da aula: contabilidade legal do imovel organiza onus, posse e custos. Aprendizado operacional: criar bloco padrao para matricula, averbacoes, tributos e despesas pos-lance.",
  "m03-aula-4": "Analise resumida da aula: informacao sobre ocupante muda prazo, custo e negociacao. Aprendizado operacional: pre-dossie de ocupacao deve vir antes da decisao de lance.",
  "m03-aula-5": "Analise resumida da aula: checklist do Granvas deve virar checklist da app. Aprendizado operacional: transformar itens do curso em criterios binarios e bloqueios P0.",
  "m04-aula-1": "Analise resumida da aula: primeira arrematacao precisa de fluxo completo. Aprendizado operacional: criar roteiro de documentos, lance, deposito, homologacao, posse e saida.",
  "m04-aula-2": "Analise resumida da aula: desocupacao e uma frente de execucao, nao detalhe posterior. Aprendizado operacional: estimar acordo, advogado, prazo e reserva antes do teto.",
  "m04-aula-3": "Analise resumida da aula: venda ou aluguel rapido define a tese de saida. Aprendizado operacional: todo candidato precisa de plano de liquidez, corretagem, prazo e preco conservador.",
  "m04-aula-4": "Analise resumida da aula: dossie de investidores transforma tese em captacao defensavel. Aprendizado operacional: gerar pack com fonte, numeros, P0, risco, tese e uso de capital.",
  "m04-editais": "Analise resumida da aula: edital e contrato operacional do leilao. Aprendizado operacional: parser/checklist de edital deve capturar praca, pagamento, comissao, dividas, posse e penalidades.",
  "m04-requerimento": "Analise resumida da aula: modelos juridicos entram como artefatos de pos-arrematacao. Aprendizado operacional: armazenar templates e exigir revisao profissional antes de qualquer uso.",
  "m04-sem-bolso": "Analise resumida da aula: arrematar sem capital proprio exige estrutura e limites. Aprendizado operacional: mapear parceiros, financiamento, cessao, risco e compliance separado da tese do imovel.",
  "m04-distancia": "Analise resumida da aula: operacao remota exige validacao documental e local. Aprendizado operacional: criar fluxo para procuracao, vistoria, diligencia local e assinatura digital.",
  "m04-consorcio": "Analise resumida da aula: carta de consorcio e frente de monetizacao paralela. Aprendizado operacional: tratar como produto/estrategia separada, nao como regra padrao de lance.",
  "m04-fim": "Analise resumida da aula: fechamento do curso deve virar rotina operacional. Aprendizado operacional: consolidar playbook, pendencias e proxima fila de aulas para analise profunda.",
});

const descriptionCaptureByLesson = Object.freeze({
  "m01-boas-vindas": {
    status: "captured",
    lines: [
      "Grupo do Telegram - E de EXTREMA IMPORTANCIA que voce entre no canal de alunos, os maiores resultados saem de la e voce vai entender o motivo.",
      "ACESSO AO CANAL DE ALUNOS:",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Nivelamento:",
      "https://leiloeslucrativos.com.br/t12025finclass/nivelamento",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m01-aula-1": {
    status: "captured",
    lines: [
      "Grupo do Telegram - E de EXTREMA IMPORTANCIA que voce entre no canal de alunos, os maiores resultados saem de la e voce vai entender o motivo.",
      "ACESSO AO CANAL DE ALUNOS:",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m01-aula-2": {
    status: "captured",
    lines: [
      "Grupo do Telegram - E de EXTREMA IMPORTANCIA que voce entre no canal de alunos, os maiores resultados saem de la e voce vai entender o motivo.",
      "ACESSO AO CANAL DE ALUNOS:",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m01-aula-3": {
    status: "captured",
    lines: [
      "Grupo do Telegram - E de EXTREMA IMPORTANCIA que voce entre no canal de alunos, os maiores resultados saem de la e voce vai entender o motivo.",
      "ACESSO AO CANAL DE ALUNOS:",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m01-aula-4": { status: "not_exposed", lines: [] },
  "m01-aula-5": {
    status: "captured",
    lines: [
      "ACESSO AO CANAL DE ALUNOS DO TELEGRAM:",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m02-aula-1": {
    status: "captured",
    lines: [
      "ACESSO AO CANAL DE ALUNOS DO TELEGRAM:",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m02-aula-2": {
    status: "captured",
    lines: [
      "ACESSO AO CANAL DE ALUNOS DO TELEGRAM:",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m02-aula-3": {
    status: "captured",
    lines: [
      "ACESSO AO CANAL DE ALUNOS DO TELEGRAM:",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m02-aula-4": {
    status: "captured",
    lines: [
      "ACESSO AO CANAL DE ALUNOS DO TELEGRAM:",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m03-aula-1": {
    status: "captured",
    lines: [
      "ACESSO AO CANAL DE ALUNOS DO TELEGRAM:",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m03-aula-2": {
    status: "captured",
    lines: [
      "ACESSO AO CANAL DE ALUNOS DO TELEGRAM:",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m03-aula-3": {
    status: "captured",
    lines: [
      "ACESSO AO CANAL DE ALUNOS DO TELEGRAM:",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m03-aula-4": {
    status: "captured",
    lines: [
      "ACESSO AO CANAL DE ALUNOS DO TELEGRAM:",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m03-aula-5": {
    status: "captured",
    lines: [
      "ACESSO AO CANAL DE ALUNOS DO TELEGRAM: https://t.me/+Tp289Ti0jfhlMjQx",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m04-aula-1": {
    status: "captured",
    lines: [
      "ACESSO AO CANAL DE ALUNOS DO TELEGRAM: https://t.me/+Tp289Ti0jfhlMjQx",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m04-aula-2": {
    status: "captured",
    lines: [
      "ACESSO AO CANAL DE ALUNOS DO TELEGRAM: https://t.me/+Tp289Ti0jfhlMjQx",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m04-aula-3": { status: "not_exposed", lines: [] },
  "m04-aula-4": { status: "not_exposed", lines: [] },
  "m04-editais": { status: "not_exposed", lines: [] },
  "m04-requerimento": { status: "not_exposed", lines: [] },
  "m04-sem-bolso": {
    status: "captured",
    lines: [
      "ACESSO AO CANAL DE ALUNOS DO TELEGRAM: https://t.me/+Tp289Ti0jfhlMjQx",
      "https://t.me/+Tp289Ti0jfhlMjQx",
      "Pergunte ao Granvas (SOMENTE duvidas sobre conteudo ou sobre leiloes):",
      "https://pergunteaogranvas.com.br/t12025finclass/",
    ],
  },
  "m04-distancia": { status: "not_exposed", lines: [] },
  "m04-consorcio": { status: "capture_failed", lines: [] },
  "m04-fim": { status: "not_exposed", lines: [] },
});

const transcriptStudyByLesson = Object.freeze({
  "m01-boas-vindas": {
    status: "analyzed_from_transcript",
    lineCount: 191,
    summary: "Onboarding do treinamento: separa sala de aula, comunidade e suporte, e orienta como registrar duvidas sem misturar atendimento da plataforma com decisao de investimento.",
  },
  "m01-aula-1": {
    status: "analyzed_from_transcript",
    lineCount: 224,
    summary: "Ensina a criar base propria de leiloeiros por fontes oficiais, validar leiloeiro atuante, usar email dedicado e fugir da concorrencia obvia dos grandes agregadores.",
  },
  "m01-aula-2": {
    status: "analyzed_from_transcript",
    lineCount: 1613,
    summary: "Mapeia o fluxo extrajudicial: alienacao fiduciaria, notificacao, primeira e segunda praca, venda posterior, ocupacao, comparaveis e alternativas de capital.",
  },
  "m01-aula-3": {
    status: "analyzed_from_transcript",
    lineCount: 2196,
    summary: "Aprofunda leilao judicial com filtro Pareto: processo, entrada, parcelamento, preco vil, comissao, deposito, subrogacao de dividas e descarte de casos ruins.",
  },
  "m01-aula-4": {
    status: "analyzed_from_transcript",
    lineCount: 669,
    summary: "Explica modalidades Caixa, licitacao aberta/fechada, deposito, documentacao, financiamento, FGTS e como a fase da Caixa muda o teto de lance.",
  },
  "m01-aula-5": {
    status: "analyzed_from_transcript",
    lineCount: 854,
    summary: "Compara leilao presencial, online e hibrido, destacando habilitacao, representante, visita local, recebimento de emails e disciplina emocional no lance.",
  },
  "m02-aula-1": {
    status: "analyzed_from_transcript",
    lineCount: 744,
    summary: "Mostra leiloes trabalhistas por regiao, centrais de hasta, lotes agrupados, retirada de bens, deposito judicial e risco de invalidacao.",
  },
  "m02-aula-2": {
    status: "analyzed_from_transcript",
    lineCount: 559,
    summary: "Demonstra avaliacao remota usando mapas, visualizacao de rua, nomes das partes, documentos online e leitura de inteligencia sobre bairro e liquidez.",
  },
  "m02-aula-3": {
    status: "analyzed_from_transcript",
    lineCount: 1334,
    summary: "Transforma busca de leiloes em funil: fontes, agregadores, Caixa, jornais, concorrencia, margem, rotatividade e motivo objetivo de selecao.",
  },
  "m02-aula-4": {
    status: "analyzed_from_transcript",
    lineCount: 1052,
    summary: "Analisa dividas do imovel e do executado, prioridades, subrogacao, CTN, IPTU/ITU/ITR, bem de familia e excecoes que podem destruir margem.",
  },
  "m03-aula-1": {
    status: "analyzed_from_transcript",
    lineCount: 817,
    summary: "Diferencia desconto legitimo de preco vil, usando percentual sobre avaliacao, regra judicial, mercado conservador e justificativa economica.",
  },
  "m03-aula-2": {
    status: "analyzed_from_transcript",
    lineCount: 1144,
    summary: "Mostra estruturas para arrematar com pouco caixa: parcelamento, PGFN/federal, financiamento, investidores, parceiros e custo financeiro separado.",
  },
  "m03-aula-3": {
    status: "analyzed_from_transcript",
    lineCount: 1076,
    summary: "Organiza a contabilidade legal do imovel: tributos, ITBI, transferencia, taxas, dividas anteriores, base legal e recursos administrativos.",
  },
  "m03-aula-4": {
    status: "analyzed_from_transcript",
    lineCount: 686,
    summary: "Ensina pre-diligencia de ocupacao usando laudo, avaliador, oficial de justica, vizinhos, internet e sinais locais antes de definir teto.",
  },
  "m03-aula-5": {
    status: "analyzed_from_transcript",
    lineCount: 1177,
    summary: "Consolida checklist de edital, matricula, onus, dividas, notificacao, condominio e diferencas entre judicial e extrajudicial.",
  },
  "m04-aula-1": {
    status: "analyzed_from_transcript",
    lineCount: 1041,
    summary: "Prepara a primeira arrematacao com simulacao, decisao de fazer ou nao fazer, repeticao de analises e disciplina operacional antes do lance real.",
  },
  "m04-aula-2": {
    status: "analyzed_from_transcript",
    lineCount: 720,
    summary: "Trata desocupacao como frente economica e juridica: risco de imovel ocupado, estrategia, advogado, relato objetivo, documentos, prazo e reserva.",
  },
  "m04-aula-3": {
    status: "analyzed_from_transcript",
    lineCount: 755,
    summary: "Mostra saida rapida por venda ou aluguel: fotos, descricao, titulo, canais, pessoa juridica, publicidade segmentada e prazo de giro.",
  },
  "m04-aula-4": {
    status: "analyzed_from_transcript",
    lineCount: 1131,
    summary: "Ensina dossie de investidores com cenarios conservadores, dados principais, risco, uso de capital, confianca, escassez e integridade.",
  },
  "m04-editais": {
    status: "analyzed_from_transcript",
    lineCount: 530,
    summary: "Analisa editais na pratica: credor, imovel, localizacao, lance condicionado, forma de pagamento, fase da divida e decisao baseada no texto.",
  },
  "m04-requerimento": {
    status: "analyzed_from_static_content",
    lineCount: 0,
    summary: "Material textual de modelos de requerimento para desocupacao; deve ser tratado como artefato pos-arrematacao com revisao juridica.",
  },
  "m04-sem-bolso": {
    status: "analyzed_from_transcript",
    lineCount: 457,
    summary: "Caso pratico de arrematar com pouco caixa usando giro, prazo, cartao/boleto e criatividade financeira, com alerta de risco de alavancagem.",
  },
  "m04-distancia": {
    status: "analyzed_from_transcript",
    lineCount: 689,
    summary: "Mostra operacao remota com cartorio, prefeitura, plataformas de prestadores, vistoria local terceirizada e evidencias digitais.",
  },
  "m04-consorcio": {
    status: "analyzed_from_transcript",
    lineCount: 1073,
    summary: "Apresenta carta de consorcio como estrategia paralela de capital: lance embutido, quitacao, reforma com nota, fluxo de aluguel e monetizacao.",
  },
  "m04-fim": {
    status: "analyzed_from_static_content",
    lineCount: 0,
    summary: "Encerramento do curso: fecha as aulas como inicio da rotina pratica de buscar, filtrar, diligenciar e executar com metodo.",
  },
});

const moduleStoryMetaById = Object.freeze({
  "modulo-01": {
    theme: "fundamentos",
    name: "Fundamentos & Base Operacional",
    subtitle: "A historia comeca antes do primeiro leilao: quem nao constroi base vive apagando incendio.",
    tags: ["Base de fontes", "Tipos de leilao", "Processo"],
  },
  "modulo-02": {
    theme: "avaliacao",
    name: "Analise & Avaliacao de Imoveis",
    subtitle: "O teto de lance nasce da leitura conservadora de valor, risco e liquidez.",
    tags: ["Avaliacao", "Comparaveis", "Diligencia"],
  },
  "modulo-03": {
    theme: "arrematacao",
    name: "Arrematacao & Engenharia da Compra",
    subtitle: "Comprar barato so e tese quando o risco juridico, financeiro e operacional tambem fecha.",
    tags: ["Preco vil", "Capital", "Checklist"],
  },
  "modulo-04": {
    theme: "pos-leilao",
    name: "Pos-leilao & Escala",
    subtitle: "A margem aparece depois do lance: posse, saida, investidores e execucao remota.",
    tags: ["Desocupacao", "Saida", "Investidores"],
  },
});

const storyVisualAssets = Object.freeze({
  leilaoPortal: {
    src: "/assets/demo/siteleiloes-portal-cantareira.png",
    alt: "Tela de lote de leilao com lance inicial, leiloeiro oficial e regra extrajudicial",
  },
  mapaComparaveis: {
    src: "/assets/demo/portal-cantareira-map.png",
    alt: "Mapa do candidato com pins de comparaveis e raio de analise",
  },
  fachadaImovel: {
    src: "/assets/demo/turiassu-apto-fonte.webp",
    alt: "Foto de fachada e entorno de imovel usada para diligencia visual",
  },
  riscoOperacional: {
    src: "/assets/patrick-jane-risco.png",
    alt: "Painel de risco do laboratorio Grao Invest com mapa e radar de risco",
  },
  metodoOperacional: {
    src: "/assets/patrick-jane-metodo.png",
    alt: "Caderno metodologico do laboratorio Grao Invest com graficos e checklist",
  },
});

const storyVisualByLesson = Object.freeze({
  "m01-boas-vindas": {
    ...storyVisualAssets.metodoOperacional,
    caption: "Antes do primeiro lance, o aluno precisa de metodo, canal de duvida e registro do que aprendeu.",
  },
  "m01-aula-1": {
    ...storyVisualAssets.leilaoPortal,
    caption: "A base nasce em fonte real: lote, leiloeiro, lance, comissao e regra publicados.",
  },
  "m01-aula-2": {
    ...storyVisualAssets.leilaoPortal,
    caption: "Extrajudicial pede leitura fria da tela: fase, credor, lance minimo, ocupacao e prazo.",
  },
  "m01-aula-3": {
    ...storyVisualAssets.riscoOperacional,
    caption: "Judicial entra como filtro Pareto: poucos casos, risco escrito e assimetria provada.",
  },
  "m01-aula-4": {
    ...storyVisualAssets.leilaoPortal,
    caption: "Modalidade Caixa muda documento, pagamento, deposito, financiamento e regra de participacao.",
  },
  "m01-aula-5": {
    ...storyVisualAssets.leilaoPortal,
    caption: "Presencial, online ou hibrido muda o palco do lance e o risco de execucao.",
  },
  "m02-aula-1": {
    ...storyVisualAssets.riscoOperacional,
    caption: "Trabalhista exige olhar alem do lote: devedor, passivo, processo e risco de invalidacao.",
  },
  "m02-aula-2": {
    ...storyVisualAssets.mapaComparaveis,
    caption: "Preco teto nasce no mapa: entorno, liquidez e comparaveis antes da vontade de dar lance.",
  },
  "m02-aula-3": {
    ...storyVisualAssets.mapaComparaveis,
    caption: "Garimpo bom vira funil visual: muitos pontos no mapa, poucos sobreviventes no Radar.",
  },
  "m02-aula-4": {
    ...storyVisualAssets.riscoOperacional,
    caption: "Divida escondida entra como alerta de risco antes de qualquer calculo de lucro.",
  },
  "m03-aula-1": {
    ...storyVisualAssets.riscoOperacional,
    caption: "Metade do preco so interessa quando o desconto nao vira fragilidade juridica.",
  },
  "m03-aula-2": {
    ...storyVisualAssets.metodoOperacional,
    caption: "Capital, parceiro e parcelamento precisam caber no metodo antes de caber no sonho.",
  },
  "m03-aula-3": {
    ...storyVisualAssets.metodoOperacional,
    caption: "Custos pequenos aparecem no caderno antes de comerem a margem depois do lance.",
  },
  "m03-aula-4": {
    ...storyVisualAssets.fachadaImovel,
    caption: "Ocupacao e entorno precisam sair da neblina: fachada, rua, acesso e sinais publicos.",
  },
  "m03-aula-5": {
    ...storyVisualAssets.metodoOperacional,
    caption: "Checklist e copiloto: ele segura a euforia quando o candidato ainda nao tem prova.",
  },
  "m04-aula-1": {
    ...storyVisualAssets.metodoOperacional,
    caption: "A primeira arrematacao deve parecer consequencia do processo, nao coragem improvisada.",
  },
  "m04-aula-2": {
    ...storyVisualAssets.fachadaImovel,
    caption: "Desocupacao comeca antes da conversa: posse, documento, entorno e estrategia.",
  },
  "m04-aula-3": {
    ...storyVisualAssets.fachadaImovel,
    caption: "Venda ou aluguel rapido depende de como o comprador enxerga o imovel e a rua.",
  },
  "m04-aula-4": {
    ...storyVisualAssets.riscoOperacional,
    caption: "Dossie bom mostra retorno e risco na mesma mesa; investidor serio quer os dois.",
  },
  "m04-editais": {
    ...storyVisualAssets.leilaoPortal,
    caption: "Edital e tela de lote sao o mapa da operacao: regra critica precisa estar marcada.",
  },
  "m04-requerimento": {
    ...storyVisualAssets.metodoOperacional,
    caption: "Modelo juridico entra como artefato controlado, com fatos e revisao humana.",
  },
  "m04-sem-bolso": {
    ...storyVisualAssets.riscoOperacional,
    caption: "Sem capital proprio nao significa sem risco; significa que o risco precisa aparecer primeiro.",
  },
  "m04-distancia": {
    ...storyVisualAssets.mapaComparaveis,
    caption: "Operacao remota continua tendo chao: mapa, vistoria local, fotos e fonte datada.",
  },
  "m04-consorcio": {
    ...storyVisualAssets.metodoOperacional,
    caption: "Consorcio vira ferramenta quando regra, prazo, taxa e uso do credito cabem no plano.",
  },
  "m04-fim": {
    ...storyVisualAssets.metodoOperacional,
    caption: "O fim do curso precisa virar rotina semanal: fonte, candidato, dossie e decisao.",
  },
});

const storyNarrativeByLesson = Object.freeze({
  "m01-boas-vindas": {
    caso: {
      scene: "Andre sentou para estudar no domingo, abriu tres abas, anotou meia duzia de links e travou na primeira duvida. O problema nao era conteudo: era falta de lugar certo para perguntar e continuar andando.",
      steps: [
        "Ele separa duvida de aula, problema de acesso e pergunta juridica que precisa de especialista.",
        "Entra na comunidade antes de precisar dela, nao depois de ficar duas semanas parado.",
        "Transforma cada resposta util em nota do caderno, porque duvida respondida e ativo operacional.",
      ],
    },
    armadilhas: [
      "Achar que comunidade e bonus simpatico, quando na pratica ela encurta o ciclo de erro.",
      "Misturar suporte da plataforma com duvida de leilao e perder tempo no canal errado.",
      "Assistir calado, acumular duvida e depois abandonar o processo por atrito pequeno.",
    ],
    sentimento: "A primeira aula nao e sobre leilao; e sobre nao estudar sozinho como se estivesse montando uma operacao secreta. Quem pergunta melhor, erra mais barato.",
  },
  "m01-aula-1": {
    caso: {
      scene: "Marina percebe que todo mundo garimpa nos mesmos portais. Em vez de entrar na fila, ela monta uma caixa de entrada so para leiloeiros oficiais e comeca a receber oportunidades antes do barulho.",
      steps: [
        "Busca leiloeiros na Junta Comercial e marca quem esta atuante, quem sumiu e quem nao serve.",
        "Cria um email dedicado, cadastra newsletters e separa fonte primaria de agregador lotado.",
        "Quando uma oportunidade aparece, ela ja sabe de onde veio, quem publicou e quanta concorrencia deve esperar.",
      ],
    },
    armadilhas: [
      "Confundir portal conhecido com fonte boa. Portal famoso tambem chama concorrente famoso.",
      "Cadastrar qualquer leiloeiro sem validar situacao oficial.",
      "Usar email pessoal e perder aviso importante no meio de boleto, promocao e spam.",
    ],
    sentimento: "Aqui a aula acende a luz: oportunidade boa nao nasce no botao pesquisar; nasce de uma rede de fontes que voce construiu antes da pressa.",
  },
  "m01-aula-2": {
    caso: {
      scene: "Marina acha um apartamento em Guarulhos com cara de achado. O preco parece lindo, mas o edital fala alienacao fiduciaria, segunda praca, ocupacao e venda posterior. A alegria dura ate ela abrir a planilha de risco.",
      steps: [
        "Primeiro ela identifica a fase real: consolidacao, primeira praca, segunda praca ou venda direta.",
        "Depois separa lance minimo, divida, comissao, ocupacao e prazo para pagamento, sem misturar tudo num desconto magico.",
        "So entao compara mercado; se o ganho depende de preco pedido fantasioso em portal, ela corta o teto sem drama.",
      ],
    },
    armadilhas: [
      "Olhar apenas percentual de desconto e ignorar em que fase o imovel esta.",
      "Tratar segunda praca como liquidacao simples, sem olhar ocupacao, divida e regra do edital.",
      "Usar preco anunciado como se fosse preco de venda realizada.",
    ],
    sentimento: "Extrajudicial e rapido, mas nao e videogame. Ele recompensa quem separa rito, dinheiro e posse antes de se apaixonar pelo desconto.",
  },
  "m01-aula-3": {
    caso: {
      scene: "Duda mostra um judicial que assusta no nome do processo, mas faz sentido nos numeros. O iniciante ve tribunal e quer fugir; o operador ve avaliacao antiga, entrada, parcelamento e risco que pode ser precificado.",
      steps: [
        "Ele confere tipo de justica, data da avaliacao, praca, entrada, parcelamento e comissao.",
        "Checa se ha sinal de preco vil, recurso ou trava processual capaz de atrasar a carta.",
        "Se o caso nao entra no 20% que paga o esforco, sai da mesa sem remorso.",
      ],
    },
    armadilhas: [
      "Fugir de todo judicial por medo e perder os casos em que o juiz justamente aumenta a seguranca.",
      "Achar que parcelamento melhora a tese sem calcular correcao, prazo e risco de caixa.",
      "Forcar lance em processo barulhento so porque o desconto parece grande.",
    ],
    sentimento: "Judicial nao e monstro; e filtro. O truque e nao tentar vencer todos os processos, e sim escolher poucos que merecem o seu tempo.",
  },
  "m01-aula-4": {
    caso: {
      scene: "Carlos abre um imovel da Caixa e comemora porque aceita financiamento. Cinco minutos depois percebe que licitacao fechada pede deposito, documento e regra propria. Nao era so clicar em participar.",
      steps: [
        "Ele classifica a modalidade Caixa antes de comparar com leilao comum.",
        "Confere deposito, proposta, financiamento, FGTS, ocupacao e prazo de assinatura.",
        "Calcula o teto considerando custo financeiro, nao apenas o lance que cabe no bolso.",
      ],
    },
    armadilhas: [
      "Achar que todo imovel Caixa tem a mesma regra de compra.",
      "Esquecer garantia/deposito e descobrir a exigencia perto demais do prazo.",
      "Usar financiamento como desculpa para aceitar margem menor.",
    ],
    sentimento: "Caixa pode ser uma porta de entrada excelente, mas porta de entrada ainda tem fechadura. Quem nao le a modalidade fica do lado de fora.",
  },
  "m01-aula-5": {
    caso: {
      scene: "Rafael escolhe um leilao presencial porque queria sentir a sala. Chega la e descobre duas vantagens: menos gente preparada e mais informacao de corredor. Tambem descobre que ansiedade tem preco.",
      steps: [
        "Ele registra se o leilao e presencial, online ou hibrido e quais documentos cada formato exige.",
        "Se nao puder ir, prepara representante com antecedencia, sem improviso de ultima hora.",
        "Define teto antes do evento para nao transformar adrenalina em prejuizo.",
      ],
    },
    armadilhas: [
      "Subestimar leilao presencial como coisa antiga; as vezes e onde a concorrencia digital nao chegou.",
      "Entrar em leilao online sem testar cadastro, senha, documento e limite.",
      "Deixar o lance subir porque alguem na sala parece mais confiante que voce.",
    ],
    sentimento: "O canal muda o jogo. Presencial, online e hibrido nao sao detalhe tecnico; sao o palco onde a sua disciplina vai ser testada.",
  },
  "m02-aula-1": {
    caso: {
      scene: "Carlos ve um galpao trabalhista com desconto agressivo. Parece uma joia, ate ele consultar o CNPJ e encontrar uma fila de processos. O desconto era convite; o passivo era a conta.",
      steps: [
        "Ele identifica TRT, tipo de devedor, composicao do lote e credor principal.",
        "Consulta outros processos e procura sinal de bem contaminado por briga maior.",
        "Se o lote parece barato porque ninguem quer encostar nele, o Radar manda para descarte ou diligencia profunda.",
      ],
    },
    armadilhas: [
      "Tratar trabalhista como judicial comum e ignorar a historia do devedor.",
      "Comprar lote agrupado sem entender o que vem junto.",
      "Achar que deposito judicial elimina todo risco de atraso ou invalidacao.",
    ],
    sentimento: "Trabalhista nao e categoria para evitar; e categoria para respeitar. O desconto bom aparece quando voce sabe onde pisar.",
  },
  "m02-aula-2": {
    caso: {
      scene: "Bianca acha um apartamento barato, abre o mapa e o encanto diminui: rua estreita, entorno cansado, anuncio comparavel inflado e liquidez duvidosa. O Google Street View salvou dinheiro antes da visita.",
      steps: [
        "Ela olha endereco, fachada, rua, comercio proximo e sinais de liquidez real.",
        "Cruza comparaveis com tamanho, bairro, conservacao e tempo de anuncio.",
        "Quando o bairro conta uma historia diferente do portal, ela baixa o preco de saida.",
      ],
    },
    armadilhas: [
      "Pegar o maior comparavel da internet para justificar o lance que voce ja queria dar.",
      "Ignorar rua, entorno e liquidez porque a metragem parece boa.",
      "Avaliar remoto sem salvar evidencia; depois ninguem lembra por que o teto mudou.",
    ],
    sentimento: "Avaliacao online boa tem faro de detetive: nao basta ver preco, tem que enxergar o que o anuncio tenta esconder.",
  },
  "m02-aula-3": {
    caso: {
      scene: "Num sabado, Joao separa 80 leiloes. Na segunda, sobram 6. Nao porque ele ficou pessimista, mas porque finalmente aprendeu que garimpo bom e mais descarte do que entusiasmo.",
      steps: [
        "Ele separa fonte primaria, agregador, Caixa, jornal e leiloeiro menor.",
        "Aplica filtros rapidos: local, tipo, desconto crivel, ocupacao, edital e liquidez.",
        "Os poucos que sobrevivem entram na fila de analise; o resto vira aprendizado, nao pendencia.",
      ],
    },
    armadilhas: [
      "Medir produtividade por quantidade de links salvos.",
      "Analisar profundamente oportunidade que ja falha no primeiro filtro.",
      "Confundir falta de volume com falta de metodo; as vezes o metodo esta descartando certo.",
    ],
    sentimento: "O segredo nao e achar mais leiloes. E criar coragem de jogar fora rapido o que so parece oportunidade.",
  },
  "m02-aula-4": {
    caso: {
      scene: "Fernanda encontra um desconto bonito, mas o condominio atrasado aparece como uma sombra no canto do edital. Ela para tudo: antes de margem, vem a pergunta chata que salva o caixa.",
      steps: [
        "Ela separa divida do imovel, divida do executado e divida que pode subrogar no preco.",
        "Confere IPTU, condominio, credores, prioridade e regra escrita no edital.",
        "Se a responsabilidade economica nao fica clara, o Radar nao deixa chamar de oportunidade.",
      ],
    },
    armadilhas: [
      "Usar artigo de lei como frase magica sem olhar edital e decisao do caso.",
      "Misturar IPTU, condominio e divida pessoal como se tudo tivesse a mesma prioridade.",
      "Calcular lucro bruto antes de descobrir quem paga a conta antiga.",
    ],
    sentimento: "Divida escondida e o imposto emocional do leilao. A aula existe para voce pagar zero desse imposto.",
  },
  "m03-aula-1": {
    caso: {
      scene: "Paulo ve um lance a 45% da avaliacao e sente que ganhou o dia. O advogado corta a festa: abaixo de certo limite, o barato pode virar preco vil e voltar como problema.",
      steps: [
        "Ele compara lance com avaliacao original, avaliacao atualizada e mercado conservador.",
        "Confere se o juiz fixou percentual minimo diferente ou autorizou condicao especial.",
        "Se o desconto extremo nao tem justificativa robusta, vira risco juridico, nao margem.",
      ],
    },
    armadilhas: [
      "Achar que quanto menor o lance, melhor a tese.",
      "Ignorar data da avaliacao e inflacao do mercado.",
      "Entrar em disputa sem saber onde termina desconto e comeca anulacao.",
    ],
    sentimento: "Metade do preco pode ser oportunidade. Preco vil pode ser armadilha vestida de oportunidade. A diferenca esta no fundamento.",
  },
  "m03-aula-2": {
    caso: {
      scene: "Livia nao tem o dinheiro inteiro, mas tem uma tese boa. Em vez de desistir, monta a operacao: entrada, parcelamento, investidor, custo financeiro e saida. O imovel continua o mesmo; a engenharia muda o jogo.",
      steps: [
        "Ela separa estrutura de capital da qualidade do imovel.",
        "Calcula entrada, parcelas, indexador, prazo e parceiro antes de prometer lucro.",
        "Se a alavancagem so funciona num cenario otimista, o Radar corta a operacao.",
      ],
    },
    armadilhas: [
      "Confundir falta de caixa com permissao para assumir qualquer risco.",
      "Vender a tese ao investidor antes de saber custo financeiro real.",
      "Deixar parcelamento esconder um imovel ruim.",
    ],
    sentimento: "Arrematar com pouco dinheiro e possivel. O perigoso e fingir que criatividade financeira substitui diligencia.",
  },
  "m03-aula-3": {
    caso: {
      scene: "Eduardo comprou barato e descobriu depois o festival de pequenas contas: ITBI, registro, taxa, lixo, recurso administrativo. Nenhuma sozinha matava a tese; juntas, comiam a margem.",
      steps: [
        "Ele monta um ledger juridico-financeiro antes do lance.",
        "Separa tributo, registro, taxa municipal, divida anterior e custo discutivel.",
        "Cada custo ganha base legal, responsavel e status: pagar, contestar ou embutir no teto.",
      ],
    },
    armadilhas: [
      "Chamar custo pequeno de detalhe ate ele aparecer multiplicado.",
      "Nao entender quando ITBI e registro entram no caixa.",
      "Aceitar cobranca municipal sem checar base legal.",
    ],
    sentimento: "Lucro em leilao tambem morre de mil cortes pequenos. Contabilidade legal e o curativo antes do sangramento.",
  },
  "m03-aula-4": {
    caso: {
      scene: "Sofia ve 'ocupado' e quase descarta. Em vez disso, investiga: laudo, oficial de justica, vizinho, consumo, foto de fachada. O ocupante deixa de ser misterio e vira custo estimado.",
      steps: [
        "Ela procura pistas no processo, na avaliacao e em sinais publicos.",
        "Classifica ocupacao como livre, ocupada ou incerta, com grau de confianca.",
        "Transforma a incerteza em reserva de prazo, acordo, advogado ou descarte.",
      ],
    },
    armadilhas: [
      "Tratar ocupacao como assunto para depois da arrematacao.",
      "Achar que uma foto antiga prova estado atual do imovel.",
      "Fazer teto sem reservar dinheiro e tempo para posse.",
    ],
    sentimento: "Ocupante desconhecido e neblina. A aula nao promete sol; ela ensina a dirigir devagar ate enxergar a estrada.",
  },
  "m03-aula-5": {
    caso: {
      scene: "Depois de tantas aulas, o checklist vira o copiloto. Quando o entusiasmo tenta pular etapa, ele pergunta: edital leu tres vezes? Matricula abriu? Divida conferiu? Ocupacao provou?",
      steps: [
        "O aluno transforma o checklist em itens binarios, nao em lembrete vago.",
        "Cada resposta precisa de evidencia: documento, link, certidao, contato ou decisao.",
        "Se um item P0 fica sem prova, a oportunidade nao avanca por charme ou pressa.",
      ],
    },
    armadilhas: [
      "Usar checklist como enfeite depois de ja decidir dar lance.",
      "Responder 'ok' sem anexar prova.",
      "Confundir checklist longo com processo seguro; o que protege e criterio de bloqueio.",
    ],
    sentimento: "Checklist bom e chato de proposito. Ele existe para impedir que a empolgacao sente no lugar do operador.",
  },
  "m04-aula-1": {
    caso: {
      scene: "A primeira arrematacao de Marcelo quase aconteceu tres vezes. Nas duas primeiras, o metodo mandou parar. Na terceira, ele deu lance sabendo por que entrava e principalmente ate onde iria.",
      steps: [
        "Ele simula candidatos antes de usar dinheiro real.",
        "Anota faria/nao faria com motivo claro, para treinar julgamento.",
        "Quando chega o caso certo, o lance ja e consequencia do processo, nao coragem de ultima hora.",
      ],
    },
    armadilhas: [
      "Querer que a primeira arrematacao seja perfeita e nunca comecar.",
      "Usar a ansiedade de estrear como desculpa para afrouxar criterio.",
      "Nao registrar os 'nao' que ensinaram mais que o lance vencedor.",
    ],
    sentimento: "Primeira arrematacao nao e salto no escuro. E o dia em que o treino finalmente encontra um caso que merece dinheiro.",
  },
  "m04-aula-2": {
    caso: {
      scene: "Renata arremata ocupado e, em vez de ligar no impulso, respira. Dez dias, notificacao, relato curto para o advogado, estrategia de acordo. O objetivo nao e vencer uma briga; e tomar posse com menor atrito.",
      steps: [
        "Ela separa o que pode ser conversa amigavel do que precisa de medida formal.",
        "Prepara relato objetivo, documentos, prazos e reserva antes de falar em desocupacao.",
        "Se o caminho judicial for inevitavel, entra organizada, nao irritada.",
      ],
    },
    armadilhas: [
      "Tratar ocupante como inimigo antes de entender o caso.",
      "Prometer prazo de posse sem advogado e sem documento.",
      "Economizar na estrategia de desocupacao e pagar com meses de atraso.",
    ],
    sentimento: "Desocupacao eficiente tem menos bravata e mais metodo. Quem organiza a conversa costuma gastar menos energia e menos dinheiro.",
  },
  "m04-aula-3": {
    caso: {
      scene: "Gustavo arrematou bem, reformou rapido e travou na venda porque o anuncio parecia feito com pressa. Foto ruim, titulo morno, preco sem estrategia. O lucro estava no imovel, mas nao chegava no comprador.",
      steps: [
        "Ele define saida antes do lance: venda, aluguel ou giro rapido.",
        "Prepara foto, titulo, descricao, canal e publico do anuncio como parte da tese.",
        "Se a liquidez exige desconto ou marketing, isso entra no teto desde o inicio.",
      ],
    },
    armadilhas: [
      "Achar que comprar bem garante vender bem.",
      "Anunciar como se todo comprador entendesse leilao e desconto.",
      "Esquecer corretagem, tempo de vacancia e custo de anuncio.",
    ],
    sentimento: "O dinheiro nao entra quando voce arremata; entra quando voce sai bem. A saida e parte da compra.",
  },
  "m04-aula-4": {
    caso: {
      scene: "Camila mostra uma oportunidade para um investidor e ele pergunta: 'onde esta o risco?' Ela nao disfarca; abre o dossie com cenario conservador, base, trava e plano de saida. A confianca nasce justamente porque ela nao vende fantasia.",
      steps: [
        "Ela monta um dossie que explica fonte, numeros, riscos, uso do capital e saida.",
        "Mostra cenario conservador antes do otimista.",
        "Registra quem recebeu, o que perguntou e qual objeção precisa virar melhoria no Radar.",
      ],
    },
    armadilhas: [
      "Levar oportunidade para investidor so com entusiasmo e print de desconto.",
      "Esconder risco para parecer mais profissional.",
      "Nao controlar versao do dossie e perder a historia da tese.",
    ],
    sentimento: "Investidor serio nao compra grito de oportunidade. Compra clareza, conservadorismo e operador que sabe dizer 'nao sei ainda'.",
  },
  "m04-editais": {
    caso: {
      scene: "O edital parece papelada ate alguem perder dinheiro por uma linha ignorada. Nessa aula, o documento deixa de ser anexo e vira o contrato operacional da operacao.",
      steps: [
        "O aluno procura credor, praca, pagamento, comissao, lance condicionado, dividas e posse.",
        "Marca no Radar o que esta escrito, o que foi inferido e o que ainda precisa de prova.",
        "Se a regra critica nao esta clara no edital, o caso volta para diligencia.",
      ],
    },
    armadilhas: [
      "Ler edital so para achar valor minimo.",
      "Ignorar lance condicionado e forma de pagamento.",
      "Copiar regra de outro edital achando que todo leiloeiro opera igual.",
    ],
    sentimento: "Edital nao e burocracia; e o manual de sobrevivencia daquela compra especifica.",
  },
  "m04-requerimento": {
    caso: {
      scene: "Depois da arrematacao, Patricia encontra um modelo de requerimento e quase copia tudo. Para antes: modelo ajuda, mas caso concreto manda.",
      steps: [
        "Ela trata o modelo como ponto de partida, nao como documento pronto.",
        "Reune carta, matricula, comprovantes e relato antes de pedir revisao juridica.",
        "O Radar guarda o artefato, mas nao dispara documento juridico sem profissional validar.",
      ],
    },
    armadilhas: [
      "Copiar requerimento como se fosse receita universal.",
      "Mandar documento sem adaptar fatos, datas e partes.",
      "Automatizar ato juridico sem revisao humana.",
    ],
    sentimento: "Modelo bom economiza tempo; modelo usado sem criterio cria problema com aparencia de solucao.",
  },
  "m04-sem-bolso": {
    caso: {
      scene: "Fernandes nao tinha o dinheiro redondo, mas tinha prazo, cartao, comprador provavel e nervo para girar. A pergunta nao era 'da para fazer?', era 'quanto custa se atrasar?'.",
      steps: [
        "Ele calcula prazo real do boleto, custo do cartao e margem depois do giro.",
        "So considera a estrutura porque a saida ja tem caminho provavel.",
        "Se o prazo apertar mais que a margem, a criatividade vira risco e o Radar trava.",
      ],
    },
    armadilhas: [
      "Confundir improviso que funcionou uma vez com metodo replicavel.",
      "Usar cartao como capital gratis.",
      "Entrar sem plano B para atraso na venda ou na posse.",
    ],
    sentimento: "Arrematar sem dinheiro pode ser brilhante ou perigoso. A diferenca e se voce calculou o tombo antes de comemorar o salto.",
  },
  "m04-distancia": {
    caso: {
      scene: "Andre esta em outra cidade e encontra um imovel interessante. Em vez de desistir ou confiar no achismo, monta uma pequena equipe relampago: cartorio online, prefeitura, vistoriador local e fotos de rua.",
      steps: [
        "Ele separa o que da para validar digitalmente do que precisa de olho na rua.",
        "Contrata prestador com escopo claro: fachada, entorno, ocupacao, acesso e fotos.",
        "Cada evidencia recebe fonte, data e confianca antes de entrar no dossie.",
      ],
    },
    armadilhas: [
      "Achar que operacao remota e operacao cega.",
      "Pedir 'da uma olhada la' sem checklist para o prestador.",
      "Aceitar foto sem data, endereco ou contexto.",
    ],
    sentimento: "Distancia nao impede diligencia. O que impede e pedir informacao vaga para gente que nao sabe o que voce precisa decidir.",
  },
  "m04-consorcio": {
    caso: {
      scene: "Sergio olha a carta de consorcio como se fosse so financiamento lento. A aula muda a leitura: carta, lance embutido, quitacao e reforma podem virar uma engrenagem de capital se a conta fechar.",
      steps: [
        "Ele separa administradora, carta, lance, capital complementar e uso permitido do credito.",
        "Modela quitacao, reforma, nota fiscal e aluguel sem misturar com lance padrao.",
        "Se o consorcio so funciona com sorte de contemplacao ou aluguel perfeito, fica fora da tese principal.",
      ],
    },
    armadilhas: [
      "Tratar consorcio como dinheiro disponivel imediatamente.",
      "Ignorar taxa, prazo, lance embutido e regra de uso do credito.",
      "Misturar estrategia de consorcio com avaliacao do imovel e perder clareza.",
    ],
    sentimento: "Consorcio nao e atalho magico; e ferramenta. Na mao certa, ajuda. Na pressa, vira nevoeiro financeiro.",
  },
  "m04-fim": {
    caso: {
      scene: "O curso acaba e a parte dificil comeca: abrir fontes, escolher candidatos, descartar sem apego e repetir. Quem fecha a ultima aula e nao cria rotina acabou de transformar conhecimento em lembranca.",
      steps: [
        "O aluno escolhe uma rotina semanal de garimpo e analise.",
        "Define primeira meta: base de fontes, candidatos simulados e um dossie completo.",
        "O Radar vira agenda de execucao, nao biblioteca de aula assistida.",
      ],
    },
    armadilhas: [
      "Confundir terminar curso com estar pronto para dar lance.",
      "Nao transformar as aulas em calendario de operacao.",
      "Esperar oportunidade perfeita antes de treinar com candidatos reais.",
    ],
    sentimento: "Fim de curso bom incomoda um pouco: agora nao falta aula, falta rotina. E rotina e onde o dinheiro comeca a aparecer.",
  },
});

function cleanAnalysis(text = "") {
  return text
    .replace(/^Analise resumida da aula:\s*/i, "")
    .replace(/\s*Aprendizado operacional:\s*/i, " ");
}

function sentence(text = "") {
  const trimmed = String(text).trim();
  if (!trimmed) return "";
  return /[.!?]$/.test(trimmed) ? trimmed : `${trimmed}.`;
}

function buildLessonStory({ lesson, module, transcriptStudy, learningEvaluation, appInsertion }) {
  const summary = sentence(transcriptStudy.summary);
  const analysis = sentence(cleanAnalysis(learningEvaluation));
  const application = sentence(appInsertion);
  const shortTitle = lesson.title.replace(/^Aula\s*\d+\s*-\s*/i, "").replace(/^Modulo\s*\d+\s*-\s*/i, "");
  const narrative = storyNarrativeByLesson[lesson.id];
  const visual = storyVisualByLesson[lesson.id] ?? {
    ...storyVisualAssets.metodoOperacional,
    caption: "A cena visual reforca a regra da aula antes de virar decisao no Radar.",
  };

  return {
    hook: summary,
    contexto: analysis,
    visual,
    caso: narrative?.caso ?? {
      scene: `Aparece um caso de "${shortTitle}" com cara de oportunidade. Antes de comemorar, o operador faz a pergunta que economiza dinheiro: qual prova transforma essa historia em decisao?`,
      steps: [
        `Comeca pela pista principal da aula: ${summary}`,
        `Traduz a licao para uma acao do Radar: ${application}`,
        "Se a prova nao aparece, o caso nao morre por drama; ele volta para diligencia ou sai da fila sem culpa.",
      ],
    },
    aplicar: [
      { label: "Na triagem", text: analysis },
      { label: "No candidato", text: application },
      { label: "No teto", text: "Recalcular margem somente depois que a regra da aula estiver evidenciada no dossie do imovel." },
      { label: "Na decisao", text: "Transformar a aula em go/no-go: avancar, pedir diligencia ou descartar sem custo emocional." },
    ],
    armadilhas: narrative?.armadilhas ?? [
      "Assistir a aula como conteudo interessante, mas sair sem um criterio que bloqueia ou libera candidato.",
      "Se encantar com desconto e pular a pergunta incomoda: onde esta a prova de fonte, risco, divida, ocupacao e saida?",
      "Guardar insight fora do Radar, obrigando a operacao a depender de memoria em vez de processo.",
    ],
    radar: application,
    sentimento: narrative?.sentimento ?? `Essa aula entra no Radar como freio inteligente. O objetivo nao e decorar "${shortTitle}", e impedir que uma oportunidade bonita avance sem prova, sem tese e sem plano de saida.`,
    sourceBasis: transcriptStudy.status === "analyzed_from_transcript" ? "transcricao" : "conteudo_textual",
    moduleTheme: moduleStoryMetaById[module.id]?.theme || "fundamentos",
  };
}

export const auctionCourseProgress = Object.freeze({
  id: "curso-1-milhao-com-leilao",
  title: "Curso 1 Milhao com Leilao",
  sourceUrl: "https://grupo-primo.circle.so/c/leilao/",
  studyLogPath: "docs/domain/radar-imobiliario/curso-1-milhao-com-leilao.md",
  operationalPlaybookPath: "docs/domain/radar-imobiliario/curso-1-milhao-com-leilao-playbook-operacional.md",
  captureManifestPath: "docs/domain/radar-imobiliario/curso-1-milhao-com-leilao-captura-validada.md",
  totalDuration: "14h22",
  updatedAt: "2026-06-01",
  modules: [
    {
      id: "modulo-01",
      title: "MODULO 01",
      duration: "3h59",
      lessons: [
        { id: "m01-boas-vindas", title: "Boas vindas do Granvas + COMUNIDADE DE ALUNOS", duration: "07:33" },
        { id: "m01-aula-1", title: "Aula 1 - Construcao de base de Leiloes para arrematacao", duration: "09:22" },
        { id: "m01-aula-2", title: "Aula 2 - Leilao Extrajudicial", duration: "01:06:35" },
        { id: "m01-aula-3", title: "Aula 3 - O Leilao Judicial \"O Pareto 80/20\"", duration: "01:27:43" },
        { id: "m01-aula-4", title: "Aula 4 - Leilao da Caixa", duration: "29:35" },
        { id: "m01-aula-5", title: "Aula 5 - Leiloes Presenciais, Leiloes Online, Leiloes Hibridos", duration: "38:15" },
      ],
    },
    {
      id: "modulo-02",
      title: "MODULO 02",
      duration: "2h32",
      lessons: [
        { id: "m02-aula-1", title: "Aula 1 - Leiloes da Justica Trabalhista", duration: "34:08" },
        { id: "m02-aula-2", title: "Aula 2 - Ferramentas de avaliacao online do imovel a ser arrematado", duration: "23:17" },
        { id: "m02-aula-3", title: "Aula 3 - Onde encontrar Leiloes e como selecionar as melhores ofertas", duration: "53:32" },
        { id: "m02-aula-4", title: "Aula 4 - Analise de dividas do imovel e do executado", duration: "41:45" },
      ],
    },
    {
      id: "modulo-03",
      title: "MODULO 03",
      duration: "3h23",
      lessons: [
        { id: "m03-aula-1", title: "Aula 1 - Comprando imoveis pela metade do preco e preco Vil", duration: "34:30" },
        { id: "m03-aula-2", title: "Aula 2 - Arrematar sem ou com pouco dinheiro", duration: "46:55" },
        { id: "m03-aula-3", title: "Aula 3 - Nocao de contabilidade legal do imovel", duration: "43:14" },
        { id: "m03-aula-4", title: "Aula 4 - Como obter informacoes sobre o ocupante", duration: "30:04" },
        { id: "m03-aula-5", title: "Aula 5 - Bonus / Checklist do Granvas", duration: "48:33" },
      ],
    },
    {
      id: "modulo-04",
      title: "MODULO 04",
      duration: "4h27",
      lessons: [
        { id: "m04-aula-1", title: "Aula 1 - Fazendo minha primeira arrematacao + Super Ultra Mega Bonus", duration: "43:48" },
        { id: "m04-aula-2", title: "Aula 2 - Desocupacao com eficiencia", duration: "29:50" },
        { id: "m04-aula-3", title: "Aula 3 - Vendendo ou alugando rapido meu imovel", duration: "31:36" },
        { id: "m04-aula-4", title: "Aula 4 - Dossie de investidores: como torna-se um arrematante insider", duration: "46:58" },
        { id: "m04-editais", title: "Modulo 4 - Analisando Editais", duration: "22:37" },
        { id: "m04-requerimento", title: "Modelos de Requerimento de Desocupacao de Imovel", duration: "" },
        { id: "m04-sem-bolso", title: "Modulo 4 - Formas de arrematar sem tirar dinheiro do bolso", duration: "19:29" },
        { id: "m04-distancia", title: "Modulo 4 - Arrematando e fazendo tudo a distancia", duration: "29:28" },
        { id: "m04-consorcio", title: "Aula Bonus - Monetizando com carta de Consorcio", duration: "43:54" },
        { id: "m04-fim", title: "O Fim do Curso, O Inicio do Seu Primeiro Milhao", duration: "" },
      ],
    },
  ].map((module) => ({
    ...module,
    storyMeta: moduleStoryMetaById[module.id],
    lessons: module.lessons.map((lesson, index) => {
      const descriptionCapture = descriptionCaptureByLesson[lesson.id] || { status: "not_captured", lines: [] };
      const transcriptStudy = transcriptStudyByLesson[lesson.id] || {
        status: "not_analyzed",
        lineCount: 0,
        summary: "Transcricao ainda nao analisada.",
      };
      const isAnalyzed = transcriptStudy.status === "analyzed_from_transcript" || transcriptStudy.status === "analyzed_from_static_content";
      return {
        status: isAnalyzed ? "analyzed" : "pending",
        analyzedAt: isAnalyzed ? "2026-06-01" : "",
        analysisBasis: isAnalyzed ? "transcricao_ou_conteudo_textual_analisado; dossie_local_criado" : "descricao_estatica_capturada_e_titulo; video_ainda_nao_consumido",
        capturedDescription: descriptionCapture.lines,
        descriptionCaptureStatus: descriptionCapture.status,
        descriptionCapturedAt: "2026-06-01",
        transcriptStudy,
        studyLogPath: "docs/domain/radar-imobiliario/curso-1-milhao-com-leilao.md",
        learningEvaluation: analysisByLesson[lesson.id] || "Analise resumida pendente.",
        appInsertion: appInsertionByLesson[lesson.id] || "Avaliar impacto no Radar Imobiliario, Teto Halley, fonte, ocupacao, dividas ou saida.",
        story: buildLessonStory({
          lesson,
          module,
          transcriptStudy,
          learningEvaluation: analysisByLesson[lesson.id] || "Analise resumida pendente.",
          appInsertion: appInsertionByLesson[lesson.id] || "Avaliar impacto no Radar Imobiliario, Teto Halley, fonte, ocupacao, dividas ou saida.",
        }),
        sequence: index + 1,
        ...lesson,
      };
    }),
  })),
});

export function getAuctionCourseStats(course = auctionCourseProgress) {
  const lessons = course.modules.flatMap((module) => module.lessons);
  const analyzed = lessons.filter((lesson) => lesson.status === "analyzed").length;
  const inProgress = lessons.filter((lesson) => lesson.status === "in_progress").length;
  const pending = lessons.length - analyzed - inProgress;

  return {
    analyzed,
    inProgress,
    pending,
    totalLessons: lessons.length,
    totalModules: course.modules.length,
  };
}

export function getNextAuctionCourseLesson(course = auctionCourseProgress) {
  for (const module of course.modules) {
    const lesson = module.lessons.find((item) => item.status !== "analyzed");
    if (lesson) return { module, lesson };
  }
  return null;
}

