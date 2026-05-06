import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Pause,
  Play,
  RotateCcw,
  Volume2,
  VolumeX,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  markMetodoOnboardingSeen,
  metodoGraoScenes,
  type MetodoGraoScene,
} from "@/lib/metodo-grao-scenes";

function audioRate(scene: MetodoGraoScene) {
  return scene.audioRate ?? 0.94;
}

function sceneDuration(scene: MetodoGraoScene) {
  return (scene.durationMs / audioRate(scene)) + scene.pauseAfterMs;
}

function mediaPlaybackRate(scene: MetodoGraoScene) {
  if (!scene.videoDurationMs) return 1;
  const rate = scene.videoDurationMs / sceneDuration(scene);
  return Math.max(0.65, Math.min(1, rate));
}

function formatTime(ms: number) {
  const total = Math.max(0, Math.round(ms / 1000));
  const minutes = String(Math.floor(total / 60)).padStart(2, "0");
  const seconds = String(total % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

export default function MetodoGrao() {
  const navigate = useNavigate();
  const [index, setIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [audioOn, setAudioOn] = useState(true);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [status, setStatus] = useState("Pronto para iniciar.");
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const elapsedRef = useRef(0);
  const audioOnRef = useRef(audioOn);
  const isPlayingRef = useRef(isPlaying);
  const hasStartedRef = useRef(hasStarted);

  const scene = metodoGraoScenes[index];
  const totalDuration = useMemo(() => sceneDuration(scene), [scene]);
  const progress = Math.min(1, elapsedMs / totalDuration);
  const totalTimeline = useMemo(
    () => metodoGraoScenes.reduce((sum, item) => sum + sceneDuration(item), 0),
    [],
  );
  const elapsedTimeline = useMemo(
    () => metodoGraoScenes.slice(0, index).reduce((sum, item) => sum + sceneDuration(item), 0) + elapsedMs,
    [elapsedMs, index],
  );

  const finishOnboarding = useCallback(() => {
    markMetodoOnboardingSeen();
    setIsPlaying(false);
    isPlayingRef.current = false;
    navigate("/", { replace: true });
  }, [navigate]);

  const stopTicker = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }, []);

  const stopMedia = useCallback(() => {
    stopTicker();
    videoRef.current?.pause();
    audioRef.current?.pause();
  }, [stopTicker]);

  const playMedia = useCallback((shouldPlayAudio = audioOnRef.current) => {
    const video = videoRef.current;
    const audio = audioRef.current;

    if (scene.media === "video" && video) {
      video.muted = true;
      video.playbackRate = mediaPlaybackRate(scene);
      video.play().catch(() => undefined);
    }

    if (shouldPlayAudio && audio) {
      audio.volume = 1;
      audio.muted = false;
      audio.defaultPlaybackRate = audioRate(scene);
      audio.playbackRate = audioRate(scene);
      audio.play().then(() => {
        setStatus("Áudio ativo.");
      }).catch((error: Error) => {
        audioOnRef.current = false;
        setAudioOn(false);
        setStatus(error.name === "NotAllowedError"
          ? "Áudio bloqueado pelo navegador. Toque em Áudio para tentar de novo."
          : "Não consegui carregar o áudio desta cena. Seguindo com imagem e texto.");
      });
    } else {
      setStatus("Reprodução visual sem áudio.");
    }
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

    const video = videoRef.current;
    if (video) {
      video.currentTime = 0;
      video.playbackRate = mediaPlaybackRate(scene);
      video.load();
    }

    const audio = audioRef.current;
    if (audio) {
      audio.currentTime = 0;
      audio.defaultPlaybackRate = audioRate(scene);
      audio.playbackRate = audioRate(scene);
      audio.load();
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
          markMetodoOnboardingSeen();
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

  function start(withAudio: boolean) {
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
    if (nextPlaying) {
      playMedia(audioOnRef.current);
    } else {
      stopMedia();
    }
  }

  function goTo(nextIndex: number, keepPlaying = isPlaying) {
    elapsedRef.current = 0;
    setIndex(Math.max(0, Math.min(metodoGraoScenes.length - 1, nextIndex)));
    setElapsedMs(0);
    isPlayingRef.current = keepPlaying;
    hasStartedRef.current = true;
    setIsPlaying(keepPlaying);
    setHasStarted(true);
  }

  function restart() {
    stopMedia();
    elapsedRef.current = 0;
    isPlayingRef.current = false;
    hasStartedRef.current = false;
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
      if (isPlayingRef.current) {
        playMedia(nextAudioOn);
      }
      return;
    }

    audioRef.current?.pause();
    setStatus("Reprodução visual sem áudio.");
  }

  return (
    <div className="animate-fade-up space-y-4">
      <section className="grid gap-4 lg:grid-cols-[0.78fr_1.22fr] lg:items-stretch">
        <aside className="glass-card order-2 lg:order-1 p-4 space-y-4">
          <div className="space-y-2">
            <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Onboarding</p>
            <h1 className="font-display text-3xl font-semibold leading-tight">Método Grão</h1>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Uma apresentação curta para entender o diferencial do Grão: transformar ruído em evidência antes de qualquer convicção.
            </p>
          </div>

          <div className="grid gap-1.5">
            {metodoGraoScenes.map((item, itemIndex) => (
              <button
                key={item.step}
                type="button"
                onClick={() => goTo(itemIndex)}
                className={cn(
                  "grid grid-cols-[2.1rem_1fr] gap-3 rounded-lg border p-2.5 text-left transition-colors",
                  itemIndex === index
                    ? "border-accent/60 bg-accent/10 text-foreground"
                    : "border-border/50 bg-surface-1/50 text-muted-foreground hover:border-primary/35 hover:text-foreground",
                )}
              >
                <span className="grid h-8 w-8 place-items-center rounded-full border border-current/30 text-[11px] font-bold tabular text-gold">
                  {item.step}
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold leading-tight">{item.title}</span>
                  <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">{item.nav}</span>
                </span>
              </button>
            ))}
          </div>

          <div className="rounded-lg border border-border/50 bg-surface-1/70 p-3 text-xs leading-relaxed text-muted-foreground">
            Conteúdo educacional. A apresentação explica o método, não recomenda compra ou venda de ativos.
          </div>
        </aside>

        <section className="relative order-1 lg:order-2 overflow-hidden rounded-xl border border-border/70 bg-surface-1 shadow-elevated">
          <div className="relative aspect-[9/13] sm:aspect-video min-h-[32rem] max-h-[72vh] bg-background">
            {scene.media === "video" ? (
              <>
                {scene.poster && (
                  <img
                    key={`${scene.step}-poster`}
                    src={scene.poster}
                    alt=""
                    className="absolute inset-0 h-full w-full object-cover opacity-80"
                  />
                )}
                <video
                  key={scene.video}
                  ref={videoRef}
                  src={scene.video}
                  poster={scene.poster}
                  className="absolute inset-0 h-full w-full object-cover"
                  playsInline
                  muted
                  preload="metadata"
                />
              </>
            ) : (
              <img
                key={scene.image}
                src={scene.image}
                alt=""
                className="absolute inset-0 h-full w-full object-cover"
              />
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-background via-background/20 to-background/20" />

            {!hasStarted && (
              <div className="absolute inset-0 z-10 grid place-items-center bg-background/55 backdrop-blur-sm">
                <div className="mx-4 max-w-sm rounded-xl border border-border/70 bg-background/85 p-4 text-center shadow-elevated">
                  <h2 className="font-display text-xl font-semibold">Começar pelo método</h2>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    O áudio precisa de um toque para ser liberado pelo navegador.
                  </p>
                  <div className="mt-4 grid gap-2">
                    <button
                      type="button"
                      onClick={() => start(true)}
                      className="rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
                    >
                      Iniciar com áudio
                    </button>
                    <button
                      type="button"
                      onClick={() => start(false)}
                      className="rounded-lg border border-border/60 bg-surface-1 px-4 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-surface-2"
                    >
                      Assistir sem áudio
                    </button>
                  </div>
                </div>
              </div>
            )}

            <div className="absolute inset-x-0 bottom-0 z-20 p-4 sm:p-6">
              <div className="max-w-2xl space-y-2">
                <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-accent">
                  <span>{scene.step}/09</span>
                  <span className="h-px w-8 bg-accent/50" />
                  <span>{scene.proof}</span>
                </div>
                <h2 className="font-display text-3xl font-semibold leading-[0.98] sm:text-5xl">{scene.title}</h2>
                <p className="max-w-xl text-sm leading-relaxed text-foreground/82 sm:text-base">{scene.copy}</p>
              </div>
            </div>
          </div>

          <audio
            key={scene.audio}
            ref={audioRef}
            src={scene.audio}
            preload="metadata"
            onError={() => setStatus("Não consegui carregar o áudio desta cena.")}
          />

          <div className="border-t border-border/70 bg-background/92 p-3">
            <div className="mb-3 flex items-center justify-between gap-3 text-[11px] text-muted-foreground">
              <span className="tabular">{formatTime(elapsedTimeline)} / {formatTime(totalTimeline)}</span>
              <span className="truncate text-right">{status}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-surface-2">
              <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${progress * 100}%` }} />
            </div>
            <div className="mt-3 grid grid-cols-[auto_1fr_auto] items-center gap-2">
              <div className="flex gap-1.5">
                <button type="button" onClick={() => goTo(index - 1, false)} className="grid h-10 w-10 place-items-center rounded-lg border border-border/60 bg-surface-1 text-muted-foreground hover:text-foreground" aria-label="Cena anterior">
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button type="button" onClick={restart} className="grid h-10 w-10 place-items-center rounded-lg border border-border/60 bg-surface-1 text-muted-foreground hover:text-foreground" aria-label="Reiniciar">
                  <RotateCcw className="h-4 w-4" />
                </button>
              </div>

              <div className="flex justify-center gap-2">
                <button
                  type="button"
                  onClick={togglePlay}
                  className="inline-flex h-11 min-w-32 items-center justify-center gap-2 rounded-lg bg-primary px-5 text-sm font-semibold text-primary-foreground shadow-glow transition-colors hover:bg-primary/90"
                >
                  {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  {isPlaying ? "Pausar" : hasStarted ? "Continuar" : "Começar"}
                </button>
                <button
                  type="button"
                  onClick={toggleAudio}
                  className={cn(
                    "inline-flex h-11 w-11 items-center justify-center gap-2 rounded-lg border text-sm font-semibold sm:w-auto sm:px-3",
                    audioOn ? "border-primary/40 bg-primary/10 text-primary" : "border-border/60 bg-surface-1 text-muted-foreground",
                  )}
                  aria-label={audioOn ? "Desativar áudio" : "Ativar áudio"}
                >
                  {audioOn ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
                  <span className="hidden sm:inline">Áudio</span>
                </button>
              </div>

              <div className="flex justify-end gap-1.5">
                <button type="button" onClick={() => goTo(index + 1, false)} className="grid h-10 w-10 place-items-center rounded-lg border border-border/60 bg-surface-1 text-muted-foreground hover:text-foreground" aria-label="Próxima cena">
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </section>
      </section>

      <section className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-center">
        <div className="rounded-xl border border-primary/20 bg-primary/8 p-4">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
            <div>
              <h3 className="font-display text-base font-semibold">Depois da apresentação, a jornada continua no Cockpit.</h3>
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                Você pode rever este método pelo menu sempre que quiser recalibrar a leitura da app.
              </p>
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={finishOnboarding}
          className="rounded-lg bg-accent px-5 py-3 text-sm font-bold text-accent-foreground transition-colors hover:bg-accent/90"
        >
          Entrar no app
        </button>
      </section>
    </div>
  );
}
