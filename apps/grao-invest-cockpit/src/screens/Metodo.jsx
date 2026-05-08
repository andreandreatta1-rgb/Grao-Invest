import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, ChevronLeft, ChevronRight, Pause, Play, RotateCcw, Volume2, VolumeX } from "lucide-react";
import { Badge, C, alpha, mono, withAlpha } from "../components";

const ASSET_BASE = "/assets/metodo-sequencia-09";

export const metodoGraoScenes = [
  {
    step: "01",
    title: "Sem sinal vazio",
    nav: "A dor: sinais sem fundamentação.",
    copy: "Você está cansado de sinais sem fundamentação? Bem-vindo ao laboratório. Aqui o objetivo não é ter fé, é ter prova.",
    proof: "Prova antes de fé",
    media: "video",
    video: `${ASSET_BASE}/video/01.mp4`,
    poster: `${ASSET_BASE}/poster/01.webp`,
    videoDurationMs: 10042,
    audio: `${ASSET_BASE}/audio/01.mp3`,
    durationMs: 8720,
    pauseAfterMs: 800,
  },
  {
    step: "02",
    title: "Verdade testada",
    nav: "Anomalias, ciclos e robustez.",
    copy: "Nosso motor não aceita menos que a verdade. Observamos anomalias, testamos centenas de ciclos e provamos a robustez.",
    proof: "O risco vira uma linha no mapa",
    media: "video",
    video: `${ASSET_BASE}/video/02.mp4`,
    poster: `${ASSET_BASE}/poster/02.webp`,
    videoDurationMs: 10042,
    audio: `${ASSET_BASE}/audio/02.mp3`,
    durationMs: 12080,
    audioRate: 0.93,
    pauseAfterMs: 1200,
  },
  {
    step: "03",
    title: "Grãos de evidência",
    nav: "Tese vira dado.",
    copy: "O resultado? Grãos de evidência. Tese que vira dado. Dado que vira riqueza no solo certo, no momento certo.",
    proof: "Foto mantida até o áudio terminar",
    media: "image",
    image: `${ASSET_BASE}/image/03.webp`,
    audio: `${ASSET_BASE}/audio/03.mp3`,
    durationMs: 8560,
    pauseAfterMs: 900,
  },
  {
    step: "04",
    title: "Ruído em evidência",
    nav: "O conceito em uma frase.",
    copy: "Grão a grão, o método transforma ruído em evidência.",
    proof: "A assinatura começa a aparecer",
    media: "video",
    video: `${ASSET_BASE}/video/04.mp4`,
    poster: `${ASSET_BASE}/poster/04.webp`,
    videoDurationMs: 5042,
    audio: `${ASSET_BASE}/audio/04.mp3`,
    durationMs: 4320,
    pauseAfterMs: 1200,
  },
  {
    step: "05",
    title: "Respirar",
    nav: "Transição visual e musical.",
    copy: "Um respiro para a ideia assentar: não é impulso, é processo. A tese atravessa o método antes de virar ação.",
    proof: "Menos pressa, mais clareza",
    media: "video",
    video: `${ASSET_BASE}/video/05.mp4`,
    poster: `${ASSET_BASE}/poster/05.webp`,
    videoDurationMs: 5042,
    audio: `${ASSET_BASE}/audio/05.mp3`,
    durationMs: 6000,
    pauseAfterMs: 650,
  },
  {
    step: "06",
    title: "Hipótese testável",
    nav: "Convencer não basta.",
    copy: "Uma hipótese boa não precisa convencer. Ela precisa poder ser testada.",
    proof: "Sem teste é só narrativa",
    media: "video",
    video: `${ASSET_BASE}/video/06.mp4`,
    poster: `${ASSET_BASE}/poster/06.webp`,
    videoDurationMs: 5042,
    audio: `${ASSET_BASE}/audio/06.mp3`,
    durationMs: 5120,
    pauseAfterMs: 800,
  },
  {
    step: "07",
    title: "Padrão histórico",
    nav: "Uma vez não basta.",
    copy: "O Halley procura o padrão no histórico. Uma vez não basta.",
    proof: "Repetição, contexto e consistência",
    media: "video",
    video: `${ASSET_BASE}/video/07.mp4`,
    poster: `${ASSET_BASE}/poster/07.webp`,
    videoDurationMs: 5042,
    audio: `${ASSET_BASE}/audio/07.mp3`,
    durationMs: 3920,
    pauseAfterMs: 850,
  },
  {
    step: "08",
    title: "Virar rotina",
    nav: "Do método para o uso.",
    copy: "A análise deixa de ser um momento isolado. Ela vira rotina: observar, testar, acompanhar e aprender.",
    proof: "A jornada fica prática",
    media: "video",
    video: `${ASSET_BASE}/video/08.mp4`,
    poster: `${ASSET_BASE}/poster/08.webp`,
    videoDurationMs: 5042,
    audio: `${ASSET_BASE}/audio/08.mp3`,
    durationMs: 5920,
    pauseAfterMs: 750,
  },
  {
    step: "09",
    title: "Grão Invest",
    nav: "Método antes da convicção.",
    copy: "Grão Invest. Método antes da convicção. Grão a grão.",
    proof: "Conteúdo educacional; não é recomendação de investimento",
    media: "video",
    video: `${ASSET_BASE}/video/09.mp4`,
    poster: `${ASSET_BASE}/poster/09.webp`,
    videoDurationMs: 5042,
    audio: `${ASSET_BASE}/audio/09.mp3`,
    durationMs: 5440,
    audioRate: 1,
    pauseAfterMs: 1200,
  },
];

export function audioRate(scene) {
  return scene.audioRate ?? 0.94;
}

export function sceneDuration(scene) {
  return scene.durationMs / audioRate(scene) + scene.pauseAfterMs;
}

function mediaPlaybackRate(scene) {
  if (!scene.videoDurationMs) return 1;
  const rate = scene.videoDurationMs / sceneDuration(scene);
  return Math.max(0.65, Math.min(1, rate));
}

function formatTime(ms) {
  const total = Math.max(0, Math.round(ms / 1000));
  const minutes = String(Math.floor(total / 60)).padStart(2, "0");
  const seconds = String(total % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function IconButton({ label, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      style={{
        alignItems: "center",
        background: C.panel,
        border: `1px solid ${C.border}`,
        borderRadius: 10,
        color: C.muted,
        cursor: "pointer",
        display: "grid",
        height: 42,
        justifyItems: "center",
        width: 42,
      }}
    >
      {children}
    </button>
  );
}

function SceneNavigator({ index, onGoTo }) {
  return (
    <div data-testid="metodo-scene-navigator" style={{ display: "grid", gap: 8 }}>
      {metodoGraoScenes.map((item, itemIndex) => {
        const active = itemIndex === index;
        return (
          <button
            key={item.step}
            type="button"
            aria-label={item.title}
            onClick={() => onGoTo(itemIndex, false)}
            style={{
              background: active ? withAlpha(C.gold, "14") : withAlpha(C.panel, "c8"),
              border: `1px solid ${active ? withAlpha(C.gold, alpha.strong) : C.border}`,
              borderRadius: 10,
              color: active ? C.text : C.muted,
              cursor: "pointer",
              display: "grid",
              gap: 10,
              gridTemplateColumns: "38px 1fr",
              minHeight: 52,
              padding: "9px 10px",
              textAlign: "left",
            }}
          >
            <span
              style={{
                alignItems: "center",
                border: `1px solid ${active ? C.gold : C.line}`,
                borderRadius: "50%",
                color: active ? C.gold : C.dim,
                display: "flex",
                fontFamily: mono,
                fontSize: 11,
                fontWeight: 800,
                height: 34,
                justifyContent: "center",
                width: 34,
              }}
            >
              {item.step}
            </span>
            <span style={{ minWidth: 0 }}>
              <span style={{ color: active ? C.gold : C.text, display: "block", fontSize: 12, fontWeight: 800, lineHeight: 1.2 }}>
                {item.nav}
              </span>
              <span style={{ color: C.muted, display: "block", fontSize: 10, lineHeight: 1.45, marginTop: 3 }}>
                {item.proof}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function MediaStage({ scene, videoRef }) {
  return (
    <div data-testid="metodo-media-stage" style={{ aspectRatio: "16 / 9", background: C.bg, position: "relative", width: "100%" }}>
      {scene.media === "video" ? (
        <>
          {scene.poster && (
            <img
              key={`${scene.step}-poster`}
              src={scene.poster}
              alt=""
              decoding="async"
              fetchPriority="high"
              style={{ height: "100%", inset: 0, objectFit: "contain", objectPosition: "center center", opacity: 0.78, position: "absolute", width: "100%" }}
            />
          )}
          <video
            key={scene.video}
            ref={videoRef}
            data-testid="metodo-scene-video"
            src={scene.video}
            poster={scene.poster}
            muted
            playsInline
            preload="metadata"
            style={{ height: "100%", inset: 0, objectFit: "contain", objectPosition: "center center", position: "absolute", width: "100%" }}
          />
        </>
      ) : (
          <img
            key={scene.image}
            data-testid="metodo-scene-image"
            src={scene.image}
            alt=""
            decoding="async"
            loading="eager"
            style={{ height: "100%", inset: 0, objectFit: "contain", objectPosition: "center center", position: "absolute", width: "100%" }}
          />
      )}

      <div style={{ background: `linear-gradient(180deg, ${withAlpha(C.bg, "35")} 0%, ${withAlpha(C.bg, "18")} 42%, ${withAlpha(C.bg, "f2")} 100%)`, inset: 0, position: "absolute" }} />
    </div>
  );
}

export default function Metodo({ onOpenMethodExample }) {
  const [index, setIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [audioOn, setAudioOn] = useState(true);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [status, setStatus] = useState("Pronto para iniciar.");
  const videoRef = useRef(null);
  const audioRef = useRef(null);
  const rafRef = useRef(null);
  const elapsedRef = useRef(0);
  const audioOnRef = useRef(audioOn);
  const isPlayingRef = useRef(isPlaying);
  const hasStartedRef = useRef(hasStarted);
  const scene = metodoGraoScenes[index];

  const totalDuration = useMemo(() => sceneDuration(scene), [scene]);
  const totalTimeline = useMemo(() => metodoGraoScenes.reduce((sum, item) => sum + sceneDuration(item), 0), []);
  const elapsedTimeline = useMemo(
    () => metodoGraoScenes.slice(0, index).reduce((sum, item) => sum + sceneDuration(item), 0) + elapsedMs,
    [elapsedMs, index],
  );
  const progress = Math.min(1, elapsedMs / totalDuration);

  const stopTicker = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }, []);

  const stopMedia = useCallback(() => {
    stopTicker();
    if (videoRef.current && !videoRef.current.paused) videoRef.current.pause();
    if (audioRef.current && !audioRef.current.paused) audioRef.current.pause();
  }, [stopTicker]);

  const playMedia = useCallback((shouldPlayAudio = audioOnRef.current) => {
    const video = videoRef.current;
    const audio = audioRef.current;

    if (scene.media === "video" && video) {
      video.muted = true;
      video.playbackRate = mediaPlaybackRate(scene);
      const videoResult = video.play?.();
      videoResult?.catch?.(() => undefined);
    }

    if (shouldPlayAudio && audio) {
      audio.volume = 1;
      audio.muted = false;
      audio.defaultPlaybackRate = audioRate(scene);
      audio.playbackRate = audioRate(scene);
      const result = audio.play?.();
      if (result?.then) {
        result
          .then(() => setStatus("Áudio ativo."))
          .catch((error) => {
            audioOnRef.current = false;
            setAudioOn(false);
            setStatus(error?.name === "NotAllowedError" ? "Áudio bloqueado pelo navegador. Toque em Áudio para tentar de novo." : "Não consegui carregar o áudio desta cena. Seguindo com imagem e texto.");
          });
      }
      return;
    }

    setStatus("Reprodução visual sem áudio.");
  }, [scene]);

  useEffect(() => {
    audioOnRef.current = audioOn;
  }, [audioOn]);

  useEffect(() => {
    isPlayingRef.current = isPlaying;
  }, [isPlaying]);

  useEffect(() => {
    hasStartedRef.current = hasStarted;
  }, [hasStarted]);

  useEffect(() => {
    stopMedia();
    elapsedRef.current = 0;
    setElapsedMs(0);

    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.playbackRate = mediaPlaybackRate(scene);
    }

    if (audioRef.current) {
      audioRef.current.currentTime = 0;
      audioRef.current.defaultPlaybackRate = audioRate(scene);
      audioRef.current.playbackRate = audioRate(scene);
    }

    if (hasStartedRef.current && isPlayingRef.current) {
      window.setTimeout(() => playMedia(audioOnRef.current), 80);
    }
  }, [index, playMedia, scene, stopMedia]);

  useEffect(() => {
    if (!isPlaying) {
      stopMedia();
      return undefined;
    }

    const startedAt = performance.now() - elapsedRef.current;
    const tick = () => {
      const nextElapsed = performance.now() - startedAt;
      if (nextElapsed >= totalDuration) {
        if (index >= metodoGraoScenes.length - 1) {
          elapsedRef.current = totalDuration;
          setElapsedMs(totalDuration);
          setIsPlaying(false);
          isPlayingRef.current = false;
          setStatus("Apresentação concluída. Método antes da convicção.");
          return;
        }

        elapsedRef.current = 0;
        setIndex((current) => current + 1);
        setElapsedMs(0);
        return;
      }

      elapsedRef.current = nextElapsed;
      setElapsedMs(nextElapsed);
      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return stopTicker;
  }, [index, isPlaying, stopMedia, stopTicker, totalDuration]);

  function start(withAudio) {
    audioOnRef.current = withAudio;
    hasStartedRef.current = true;
    isPlayingRef.current = true;
    elapsedRef.current = elapsedMs;
    setAudioOn(withAudio);
    setHasStarted(true);
    setIsPlaying(true);
    setStatus(withAudio ? "Iniciando com áudio." : "Iniciando sem áudio.");
    playMedia(withAudio);
  }

  function togglePlay() {
    if (!hasStarted) {
      start(audioOnRef.current);
      return;
    }

    const nextPlaying = !isPlayingRef.current;
    isPlayingRef.current = nextPlaying;
    setIsPlaying(nextPlaying);
    if (nextPlaying) playMedia(audioOnRef.current);
    else stopMedia();
  }

  function goTo(nextIndex, keepPlaying = isPlaying) {
    const safeIndex = Math.max(0, Math.min(metodoGraoScenes.length - 1, nextIndex));
    elapsedRef.current = 0;
    setIndex(safeIndex);
    setElapsedMs(0);
    setHasStarted(true);
    hasStartedRef.current = true;
    setIsPlaying(keepPlaying);
    isPlayingRef.current = keepPlaying;
    setStatus(`Cena ${metodoGraoScenes[safeIndex].step} selecionada.`);
  }

  function restart() {
    stopMedia();
    elapsedRef.current = 0;
    hasStartedRef.current = false;
    isPlayingRef.current = false;
    setIndex(0);
    setElapsedMs(0);
    setHasStarted(false);
    setIsPlaying(false);
    setStatus("Pronto para reiniciar.");
  }

  function toggleAudio() {
    const nextAudioOn = !audioOnRef.current;
    audioOnRef.current = nextAudioOn;
    setAudioOn(nextAudioOn);

    if (nextAudioOn) {
      setStatus("Tentando ativar áudio.");
      if (isPlayingRef.current) playMedia(true);
      return;
    }

    if (audioRef.current && !audioRef.current.paused) audioRef.current.pause();
    setStatus("Reprodução visual sem áudio.");
  }

  function enterApp() {
    onOpenMethodExample?.();
  }

  return (
    <main style={{ background: C.bg, color: C.text, display: "flex", flexDirection: "column", fontFamily: "Sora, system-ui, sans-serif", gap: 18, minHeight: 640, padding: "24px 28px 40px" }}>
      <section style={{ display: "grid", gap: 16, gridTemplateColumns: "minmax(260px, 0.68fr) minmax(0, 1.32fr)", alignItems: "start" }}>
        <aside style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, display: "flex", flexDirection: "column", gap: 14, padding: 16 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ color: C.gold, fontFamily: mono, fontSize: 10, fontWeight: 800, letterSpacing: "0.1em", textTransform: "uppercase" }}>Onboarding</div>
            <p style={{ color: C.text, fontSize: 24, fontWeight: 800, lineHeight: 1.12, margin: 0 }}>Método antes da convicção</p>
            <p style={{ color: C.muted, fontSize: 13, lineHeight: 1.6, margin: 0 }}>
              Uma apresentação curta para entender o diferencial do Grão: transformar ruído em evidência antes de qualquer tese virar ação.
            </p>
          </div>

          <SceneNavigator index={index} onGoTo={goTo} />

          <div style={{ background: withAlpha(C.gold, "08"), border: `1px solid ${withAlpha(C.gold, alpha.subtle)}`, borderRadius: 12, color: C.muted, fontSize: 12, lineHeight: 1.6, padding: 13 }}>
            Conteúdo educacional. A apresentação explica o método, não recomenda compra ou venda de ativos.
          </div>
        </aside>

        <section style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 14, boxShadow: `0 18px 60px ${withAlpha(C.bg, "70")}`, overflow: "hidden" }}>
          <div style={{ position: "relative" }}>
            <MediaStage scene={scene} videoRef={videoRef} />
          </div>

          <audio
            key={scene.audio}
            ref={audioRef}
            data-testid="metodo-scene-audio"
            src={scene.audio}
            preload="metadata"
            onError={() => setStatus("Não consegui carregar o áudio desta cena.")}
          />

          <div style={{ borderTop: `1px solid ${C.border}`, background: withAlpha(C.bg, "c8"), padding: 14 }}>
            <div data-testid="metodo-scene-caption" style={{ borderBottom: `1px solid ${C.line}`, display: "grid", gap: 8, gridTemplateColumns: "minmax(0, 0.68fr) minmax(0, 1.32fr)", marginBottom: 12, paddingBottom: 12 }}>
              <div>
                <div style={{ alignItems: "center", color: C.gold, display: "flex", fontFamily: mono, fontSize: 10, fontWeight: 800, gap: 10, letterSpacing: "0.1em", marginBottom: 6, textTransform: "uppercase" }}>
                  <span>{scene.step}/09</span>
                  <span style={{ background: withAlpha(C.gold, alpha.strong), height: 1, width: 36 }} />
                  <span>{scene.proof}</span>
                </div>
                <div style={{ color: C.text, fontSize: 18, fontWeight: 800, lineHeight: 1.15 }}>{scene.title}</div>
              </div>
              <div style={{ alignSelf: "end", color: C.muted, fontSize: 12, lineHeight: 1.55 }}>{scene.copy}</div>
            </div>
            <div style={{ alignItems: "center", color: C.muted, display: "flex", fontSize: 11, justifyContent: "space-between", gap: 12, marginBottom: 10 }}>
              <span style={{ fontFamily: mono }}>{formatTime(elapsedTimeline)} / {formatTime(totalTimeline)}</span>
              <span style={{ textAlign: "right" }}>{status}</span>
            </div>
            <div role="progressbar" aria-label="Progresso da apresentação do método" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)} style={{ background: C.line, borderRadius: 999, height: 6, overflow: "hidden" }}>
              <div style={{ background: C.gold, borderRadius: 999, height: "100%", transition: "width 0.2s linear", width: `${progress * 100}%` }} />
            </div>
            <div style={{ alignItems: "center", display: "grid", gap: 12, gridTemplateColumns: "auto 1fr auto", marginTop: 12 }}>
              <div style={{ display: "flex", gap: 8 }}>
                <IconButton label="Cena anterior" onClick={() => goTo(index - 1, false)}><ChevronLeft size={17} /></IconButton>
                <IconButton label="Reiniciar" onClick={restart}><RotateCcw size={16} /></IconButton>
              </div>

              <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
                <button
                  type="button"
                  onClick={togglePlay}
                  style={{ alignItems: "center", background: C.gold, border: `1px solid ${C.gold}`, borderRadius: 11, color: C.bg, cursor: "pointer", display: "inline-flex", fontSize: 13, fontWeight: 800, gap: 8, justifyContent: "center", minHeight: 44, minWidth: 134, padding: "0 18px" }}
                >
                  {isPlaying ? <Pause size={16} /> : <Play size={16} />}
                  {isPlaying ? "Pausar" : hasStarted ? "Continuar" : audioOn ? "Começar com áudio" : "Começar sem áudio"}
                </button>
                <button
                  type="button"
                  onClick={toggleAudio}
                  aria-label={audioOn ? "Desativar áudio" : "Ativar áudio"}
                  style={{ alignItems: "center", background: audioOn ? withAlpha(C.gold, "14") : C.panel, border: `1px solid ${audioOn ? withAlpha(C.gold, alpha.border) : C.border}`, borderRadius: 11, color: audioOn ? C.gold : C.muted, cursor: "pointer", display: "inline-flex", fontSize: 12, fontWeight: 800, gap: 8, justifyContent: "center", minHeight: 44, padding: "0 13px" }}
                >
                  {audioOn ? <Volume2 size={16} /> : <VolumeX size={16} />}
                  Áudio
                </button>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <IconButton label="Próxima cena" onClick={() => goTo(index + 1, false)}><ChevronRight size={17} /></IconButton>
              </div>
            </div>
          </div>
        </section>
      </section>

      <section style={{ display: "grid", gap: 14, gridTemplateColumns: "minmax(0, 1fr) auto", alignItems: "center" }}>
        <div style={{ alignItems: "flex-start", background: withAlpha(C.gold, "08"), border: `1px solid ${withAlpha(C.gold, alpha.subtle)}`, borderRadius: 14, display: "flex", gap: 12, padding: 16 }}>
          <CheckCircle2 color={C.gold} size={20} style={{ flexShrink: 0, marginTop: 2 }} />
          <div>
            <div style={{ color: C.text, fontSize: 15, fontWeight: 800, marginBottom: 5 }}>Depois da apresentação, a jornada continua no cockpit.</div>
            <div style={{ color: C.muted, fontSize: 12, lineHeight: 1.6 }}>
              Você pode rever este método pelo menu sempre que quiser recalibrar a leitura do app.
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={enterApp}
          style={{ background: C.gold, border: `1px solid ${C.gold}`, borderRadius: 11, color: C.bg, cursor: "pointer", fontFamily: mono, fontSize: 12, fontWeight: 900, minHeight: 48, padding: "0 18px", textTransform: "uppercase" }}
        >
          Entrar no app
        </button>
      </section>

      <section style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>
        {[
          ["Grão de evidência", "Cada tese precisa virar dado observável antes de ganhar espaço."],
          ["Grão de método", "O Halley testa ciclos, mede erro e registra aprendizado."],
          ["Grão de prudência", "Nenhuma cena promete certeza. Ela mostra critério para decidir melhor."],
        ].map(([title, description], itemIndex) => (
          <article key={title} style={{ background: C.card, border: `1px solid ${C.border}`, borderLeft: `3px solid ${[C.gold, C.teal, C.purple][itemIndex]}`, borderRadius: 12, padding: 14 }}>
            <Badge label={`0${itemIndex + 1}`} type={itemIndex === 0 ? "warning" : itemIndex === 1 ? "success" : "info"} />
            <div style={{ color: C.text, fontSize: 14, fontWeight: 800, marginTop: 10 }}>{title}</div>
            <div style={{ color: C.muted, fontSize: 12, lineHeight: 1.6, marginTop: 5 }}>{description}</div>
          </article>
        ))}
      </section>
    </main>
  );
}
