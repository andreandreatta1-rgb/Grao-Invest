export const METODO_ONBOARDING_KEY = "graoinvest.metodo_onboarding_seen";

const ASSET_BASE = "/metodo/06_sequencia_09";
const SCREEN_IMAGE_BASE = "/metodo/imagens";

export type MetodoGraoScene = {
  step: string;
  title: string;
  nav: string;
  copy: string;
  proof: string;
  media: "video" | "image";
  video?: string;
  poster?: string;
  image?: string;
  audio: string;
  durationMs: number;
  videoDurationMs?: number;
  audioRate?: number;
  pauseAfterMs: number;
};

export const metodoGraoScenes: MetodoGraoScene[] = [
  {
    step: "01",
    title: "Sem sinal vazio",
    nav: "A dor: sinais sem fundamentação.",
    copy: "Você está cansado de sinais sem fundamentação? Bem-vindo ao laboratório. Aqui o objetivo não é ter fé, é ter prova.",
    proof: "Laboratório: prova antes de fé.",
    media: "video",
    video: `${ASSET_BASE}/video/01.mp4`,
    poster: `${ASSET_BASE}/poster/01.png`,
    videoDurationMs: 10_042,
    audio: `${ASSET_BASE}/audio/01.mp3`,
    durationMs: 8_720,
    pauseAfterMs: 800,
  },
  {
    step: "02",
    title: "Verdade testada",
    nav: "Anomalias, ciclos e robustez.",
    copy: "Nosso motor não aceita menos que a verdade. Observamos anomalias, testamos centenas de ciclos e provamos a robustez.",
    proof: "O risco vira uma linha no mapa.",
    media: "video",
    video: `${ASSET_BASE}/video/02.mp4`,
    poster: `${ASSET_BASE}/poster/02.png`,
    videoDurationMs: 10_042,
    audio: `${ASSET_BASE}/audio/02.mp3`,
    durationMs: 12_080,
    audioRate: 0.93,
    pauseAfterMs: 1_200,
  },
  {
    step: "03",
    title: "Grãos de evidência",
    nav: "Tese vira dado.",
    copy: "O resultado? Grãos de evidência. Tese que vira dado. Dado que vira riqueza no solo certo, no momento certo.",
    proof: "Cena estática mantida até o áudio terminar.",
    media: "image",
    image: `${ASSET_BASE}/image/03.png`,
    audio: `${ASSET_BASE}/audio/03.mp3`,
    durationMs: 8_560,
    pauseAfterMs: 900,
  },
  {
    step: "04",
    title: "Ruído em evidência",
    nav: "O conceito em uma frase.",
    copy: "Grão a grão, o método transforma ruído em evidência.",
    proof: "A assinatura começa a aparecer.",
    media: "video",
    video: `${ASSET_BASE}/video/04.mp4`,
    poster: `${ASSET_BASE}/poster/04.png`,
    videoDurationMs: 5_042,
    audio: `${ASSET_BASE}/audio/04.mp3`,
    durationMs: 4_320,
    pauseAfterMs: 1_200,
  },
  {
    step: "05",
    title: "Respirar",
    nav: "Transição visual e musical.",
    copy: "Um respiro para a ideia assentar: não é impulso, é processo. A tese atravessa o método antes de virar ação.",
    proof: "Interlúdio para reduzir pressa e aumentar clareza.",
    media: "video",
    video: `${ASSET_BASE}/video/05.mp4`,
    poster: `${ASSET_BASE}/poster/05.png`,
    videoDurationMs: 5_042,
    audio: `${ASSET_BASE}/audio/05.mp3`,
    durationMs: 6_000,
    pauseAfterMs: 650,
  },
  {
    step: "06",
    title: "Hipótese testável",
    nav: "Convencer não basta.",
    copy: "Uma hipótese boa não precisa convencer. Ela precisa poder ser testada.",
    proof: "Sem teste, é só narrativa.",
    media: "video",
    video: `${ASSET_BASE}/video/06.mp4`,
    poster: `${ASSET_BASE}/poster/06.png`,
    videoDurationMs: 5_042,
    audio: `${ASSET_BASE}/audio/06.mp3`,
    durationMs: 5_120,
    pauseAfterMs: 800,
  },
  {
    step: "07",
    title: "Padrão histórico",
    nav: "Uma vez não basta.",
    copy: "O Halley procura o padrão no histórico. Uma vez não basta.",
    proof: "Repetição, contexto e consistência.",
    media: "video",
    video: `${ASSET_BASE}/video/07.mp4`,
    poster: `${ASSET_BASE}/poster/07.png`,
    videoDurationMs: 5_042,
    audio: `${ASSET_BASE}/audio/07.mp3`,
    durationMs: 3_920,
    pauseAfterMs: 850,
  },
  {
    step: "08",
    title: "Virar rotina",
    nav: "Do método para o uso.",
    copy: "A análise deixa de ser um momento isolado. Ela vira rotina: observar, testar, acompanhar e aprender.",
    proof: "A jornada fica prática.",
    media: "video",
    video: `${ASSET_BASE}/video/08.mp4`,
    poster: `${ASSET_BASE}/poster/08.png`,
    videoDurationMs: 5_042,
    audio: `${ASSET_BASE}/audio/08.mp3`,
    durationMs: 5_920,
    pauseAfterMs: 750,
  },
  {
    step: "09",
    title: "Grão Invest",
    nav: "Método antes da convicção.",
    copy: "Grão Invest. Método antes da convicção. Grão a grão.",
    proof: "Conteúdo educacional; não é recomendação de investimento.",
    media: "video",
    video: `${ASSET_BASE}/video/09.mp4`,
    poster: `${ASSET_BASE}/poster/09.png`,
    videoDurationMs: 5_042,
    audio: `${ASSET_BASE}/audio/09.mp3`,
    durationMs: 5_440,
    audioRate: 1,
    pauseAfterMs: 1_200,
  },
];

export type MetodoGraoScreenImage = {
  src: string;
  alt: string;
};

export const metodoGraoScreenImages = {
  cockpit: {
    src: `${SCREEN_IMAGE_BASE}/01.webp`,
    alt: "Metodo Grao - Cockpit",
  },
  teses: {
    src: `${SCREEN_IMAGE_BASE}/02.webp`,
    alt: "Metodo Grao - Teses",
  },
  mercado: {
    src: `${SCREEN_IMAGE_BASE}/03.webp`,
    alt: "Metodo Grao - Mercado",
  },
  lab: {
    src: `${SCREEN_IMAGE_BASE}/04.webp`,
    alt: "Metodo Grao - Laboratorio",
  },
  decisoes: {
    src: `${SCREEN_IMAGE_BASE}/05.webp`,
    alt: "Metodo Grao - Decisoes",
  },
  metodo: {
    src: `${SCREEN_IMAGE_BASE}/06.webp`,
    alt: "Metodo Grao - Onboarding",
  },
  configuracao: {
    src: `${SCREEN_IMAGE_BASE}/07.webp`,
    alt: "Metodo Grao - Configuracao",
  },
  instalar: {
    src: `${SCREEN_IMAGE_BASE}/08.webp`,
    alt: "Metodo Grao - Instalacao",
  },
  teseDetalhe: {
    src: `${SCREEN_IMAGE_BASE}/09.webp`,
    alt: "Metodo Grao - Detalhe da tese",
  },
} satisfies Record<string, MetodoGraoScreenImage>;

export function getMetodoGraoScreenImage(pathname: string): MetodoGraoScreenImage {
  if (pathname.startsWith("/teses/")) return metodoGraoScreenImages.teseDetalhe;
  if (pathname === "/teses") return metodoGraoScreenImages.teses;
  if (pathname === "/mercado") return metodoGraoScreenImages.mercado;
  if (pathname === "/lab") return metodoGraoScreenImages.lab;
  if (pathname === "/decisoes") return metodoGraoScreenImages.decisoes;
  if (pathname === "/metodo") return metodoGraoScreenImages.metodo;
  if (pathname === "/config") return metodoGraoScreenImages.configuracao;
  if (pathname === "/instalar") return metodoGraoScreenImages.instalar;
  return metodoGraoScreenImages.cockpit;
}

export function markMetodoOnboardingSeen() {
  try {
    window.localStorage.setItem(METODO_ONBOARDING_KEY, "1");
  } catch {
    // LocalStorage can be unavailable in private or embedded browser modes.
  }
}

export function hasSeenMetodoOnboarding() {
  try {
    return window.localStorage.getItem(METODO_ONBOARDING_KEY) === "1";
  } catch {
    return true;
  }
}
