import { useState } from "react";
import { AlertTriangle, BookOpenText, CheckCircle2, ChevronLeft, ChevronRight, Lightbulb, Map, MonitorSmartphone, Wrench } from "lucide-react";
import { C, alpha, mono, withAlpha } from "../components";
import {
  auctionCourseProgress,
  getAuctionCourseStats,
  getNextAuctionCourseLesson,
} from "../data/auctionCourseProgress.js";

function statusCopy(status) {
  if (status === "analyzed") return "Analisada";
  if (status === "in_progress") return "Em analise";
  return "Pendente";
}

function statusColor(status) {
  if (status === "analyzed") return C.teal;
  if (status === "in_progress") return C.amber;
  return C.muted;
}

function descriptionStatusCopy(status, lineCount) {
  if (lineCount > 0) return `Descricao completa capturada (${lineCount} linhas)`;
  if (status === "capture_failed") return "Descricao nao capturada: falha no acesso";
  if (status === "not_exposed") return "Descricao nao exposta pelo Circle";
  return "Sem descricao textual capturada";
}

function transcriptStatusCopy(study) {
  if (!study || study.status === "not_analyzed") return "Resumo da aula pendente";
  if (study.status === "analyzed_from_static_content") return "Resumo da aula - conteudo textual analisado";
  return `Resumo da aula - transcricao analisada (${study.lineCount || 0} linhas)`;
}

const storyThemes = Object.freeze({
  fundamentos: { accent: C.teal, muted: withAlpha(C.teal, "18"), soft: withAlpha(C.teal, "08") },
  avaliacao: { accent: C.purple, muted: withAlpha(C.purple, "18"), soft: withAlpha(C.purple, "08") },
  arrematacao: { accent: C.amber, muted: withAlpha(C.amber, "20"), soft: withAlpha(C.amber, "09") },
  "pos-leilao": { accent: C.coral, muted: withAlpha(C.coral, "20"), soft: withAlpha(C.coral, "09") },
});

function getTheme(module) {
  return storyThemes[module?.storyMeta?.theme] || storyThemes.fundamentos;
}

function SectionBlock({ icon: Icon, label, children, accent = C.gold, tone = "neutral" }) {
  const isAlert = tone === "alert";
  const border = isAlert ? withAlpha(C.coral, "28") : withAlpha(accent, "24");
  const background = isAlert ? withAlpha(C.coral, "07") : C.card;

  return (
    <section
      style={{
        background,
        border: `1px solid ${border}`,
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          alignItems: "center",
          borderBottom: `1px solid ${C.border}`,
          display: "flex",
          gap: 10,
          padding: "11px 13px",
        }}
      >
        <span
          aria-hidden="true"
          style={{
            alignItems: "center",
            background: withAlpha(accent, "14"),
            border: `1px solid ${withAlpha(accent, "28")}`,
            borderRadius: 8,
            color: accent,
            display: "inline-flex",
            height: 30,
            justifyContent: "center",
            width: 30,
          }}
        >
          <Icon size={16} strokeWidth={2.2} />
        </span>
        <div
          style={{
            color: isAlert ? C.coral : accent,
            fontFamily: mono,
            fontSize: 9,
            fontWeight: 900,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
          }}
        >
          {label}
        </div>
      </div>
      <div style={{ color: C.muted, fontSize: 12, lineHeight: 1.65, padding: "13px 14px" }}>
        {children}
      </div>
    </section>
  );
}

function StoryVisualPanel({ visual, accent }) {
  if (!visual?.src) return null;

  return (
    <figure
      style={{
        background: C.card,
        border: `1px solid ${withAlpha(accent, "28")}`,
        borderRadius: 8,
        margin: 0,
        minWidth: 0,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          aspectRatio: "16 / 10",
          background: C.panel,
          overflow: "hidden",
        }}
      >
        <img
          alt={visual.alt || "Cena operacional da aula"}
          loading="lazy"
          src={visual.src}
          style={{
            display: "block",
            height: "100%",
            objectFit: "cover",
            width: "100%",
          }}
        />
      </div>
      <figcaption
        style={{
          borderTop: `1px solid ${C.border}`,
          color: C.muted,
          fontSize: 12,
          lineHeight: 1.55,
          padding: "11px 13px",
        }}
      >
        <div
          style={{
            color: accent,
            fontFamily: mono,
            fontSize: 9,
            fontWeight: 900,
            letterSpacing: "0.08em",
            marginBottom: 5,
            textTransform: "uppercase",
          }}
        >
          Cena visual
        </div>
        {visual.caption}
      </figcaption>
    </figure>
  );
}

function CourseStoryNotebook({ course }) {
  const [activeModuleIndex, setActiveModuleIndex] = useState(0);
  const [activeLessonByModule, setActiveLessonByModule] = useState({});
  const activeModule = course.modules[activeModuleIndex] || course.modules[0];
  const activeLessonIndex = activeLessonByModule[activeModule.id] || 0;
  const activeLesson = activeModule.lessons[activeLessonIndex] || activeModule.lessons[0];
  const theme = getTheme(activeModule);
  const story = activeLesson.story;

  function setLesson(index) {
    setActiveLessonByModule((current) => ({ ...current, [activeModule.id]: index }));
  }

  function goToModule(index) {
    setActiveModuleIndex(index);
  }

  function goPrev() {
    if (activeLessonIndex > 0) {
      setLesson(activeLessonIndex - 1);
      return;
    }
    if (activeModuleIndex > 0) {
      const previousModule = course.modules[activeModuleIndex - 1];
      setActiveModuleIndex(activeModuleIndex - 1);
      setActiveLessonByModule((current) => ({
        ...current,
        [previousModule.id]: Math.max(0, previousModule.lessons.length - 1),
      }));
    }
  }

  function goNext() {
    if (activeLessonIndex < activeModule.lessons.length - 1) {
      setLesson(activeLessonIndex + 1);
      return;
    }
    if (activeModuleIndex < course.modules.length - 1) {
      setActiveModuleIndex(activeModuleIndex + 1);
    }
  }

  const isFirst = activeModuleIndex === 0 && activeLessonIndex === 0;
  const isLast = activeModuleIndex === course.modules.length - 1 && activeLessonIndex === activeModule.lessons.length - 1;

  return (
    <section
      aria-label="Caderno storytelling do curso"
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          background: C.panel,
          borderBottom: `1px solid ${C.border}`,
          display: "flex",
          overflowX: "auto",
        }}
      >
        {course.modules.map((module, index) => {
          const moduleTheme = getTheme(module);
          const isActive = index === activeModuleIndex;
          return (
            <button
              key={module.id}
              onClick={() => goToModule(index)}
              style={{
                background: isActive ? withAlpha(moduleTheme.accent, "10") : "transparent",
                border: 0,
                borderBottom: `2px solid ${isActive ? moduleTheme.accent : "transparent"}`,
                color: isActive ? C.text : C.muted,
                cursor: "pointer",
                flex: "0 0 auto",
                fontFamily: mono,
                fontSize: 10,
                fontWeight: 900,
                letterSpacing: "0.07em",
                padding: "14px 16px",
                textAlign: "left",
                textTransform: "uppercase",
              }}
              type="button"
            >
              {module.title}
              <span
                style={{
                  background: withAlpha(moduleTheme.accent, isActive ? "18" : "10"),
                  borderRadius: 999,
                  color: isActive ? moduleTheme.accent : C.dim,
                  display: "inline-block",
                  marginLeft: 8,
                  padding: "2px 7px",
                }}
              >
                {module.lessons.length}
              </span>
            </button>
          );
        })}
      </div>

      <div
        style={{
          background: `linear-gradient(135deg, ${withAlpha(theme.accent, "16")}, ${C.card})`,
          borderBottom: `1px solid ${C.border}`,
          padding: "20px 22px",
        }}
      >
        <div style={{ color: theme.accent, fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.1em", textTransform: "uppercase" }}>
          Caderno storytelling
        </div>
        <h2 style={{ color: C.text, fontSize: 22, lineHeight: 1.2, margin: "7px 0 4px" }}>
          {activeModule.storyMeta?.name || activeModule.title}
        </h2>
        <div style={{ color: C.muted, fontSize: 13, lineHeight: 1.6, maxWidth: 900 }}>
          {activeModule.storyMeta?.subtitle}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 7, marginTop: 13 }}>
          {(activeModule.storyMeta?.tags || []).map((tag) => (
            <span
              key={tag}
              style={{
                border: `1px solid ${withAlpha(theme.accent, "28")}`,
                borderRadius: 999,
                color: theme.accent,
                fontFamily: mono,
                fontSize: 9,
                fontWeight: 800,
                padding: "4px 9px",
              }}
            >
              {tag}
            </span>
          ))}
          <span
            style={{
              border: `1px solid ${withAlpha(C.teal, "28")}`,
              borderRadius: 999,
              color: C.teal,
              fontFamily: mono,
              fontSize: 9,
              fontWeight: 800,
              padding: "4px 9px",
            }}
          >
            {activeModule.lessons.filter((lesson) => lesson.status === "analyzed").length}/{activeModule.lessons.length} analisadas
          </span>
        </div>
      </div>

      <div
        style={{
          borderBottom: `1px solid ${C.border}`,
          display: "flex",
          overflowX: "auto",
          padding: "0 12px",
        }}
      >
        {activeModule.lessons.map((lesson, index) => {
          const isActive = index === activeLessonIndex;
          return (
            <button
              key={lesson.id}
              onClick={() => setLesson(index)}
              style={{
                background: "transparent",
                border: 0,
                borderBottom: `2px solid ${isActive ? theme.accent : "transparent"}`,
                color: isActive ? C.text : C.muted,
                cursor: "pointer",
                flex: "0 0 auto",
                fontSize: 12,
                fontWeight: isActive ? 800 : 600,
                padding: "12px 13px",
                textAlign: "left",
                whiteSpace: "nowrap",
              }}
              type="button"
            >
              {String(index + 1).padStart(2, "0")} - {lesson.title.replace(/^Aula\s*\d+\s*-\s*/i, "").replace(/^Modulo\s*\d+\s*-\s*/i, "")}
            </button>
          );
        })}
      </div>

      <div style={{ padding: 22 }}>
        <div style={{ alignItems: "center", display: "flex", flexWrap: "wrap", gap: 9, marginBottom: 9 }}>
          <span style={{ color: C.dim, fontFamily: mono, fontSize: 10, fontWeight: 900, letterSpacing: "0.1em", textTransform: "uppercase" }}>
            Aula {String(activeLessonIndex + 1).padStart(2, "0")}
          </span>
          <span style={{ border: `1px solid ${C.border}`, borderRadius: 999, color: C.muted, fontFamily: mono, fontSize: 10, fontWeight: 800, padding: "3px 9px" }}>
            {activeLesson.duration || "material"}
          </span>
          <span style={{ alignItems: "center", color: C.teal, display: "inline-flex", fontFamily: mono, fontSize: 10, fontWeight: 900, gap: 5 }}>
            <CheckCircle2 size={13} /> Analisada
          </span>
          <span style={{ color: theme.accent, fontFamily: mono, fontSize: 10, fontWeight: 800 }}>
            Base: {story.sourceBasis === "transcricao" ? "transcricao" : "conteudo textual"}
          </span>
        </div>
        <h3 style={{ color: C.text, fontSize: 21, lineHeight: 1.25, margin: "0 0 8px" }}>{activeLesson.title}</h3>
        <div style={{ color: C.muted, fontSize: 14, fontStyle: "italic", lineHeight: 1.7, marginBottom: 18, maxWidth: 980 }}>
          {story.hook}
        </div>

        <div style={{ display: "grid", gap: 14, gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 300px), 1fr))" }}>
          <StoryVisualPanel accent={theme.accent} visual={story.visual} />
          <SectionBlock accent={theme.accent} icon={Map} label="Contexto - o que esta aula resolve">
            {story.contexto}
          </SectionBlock>
          <SectionBlock accent={theme.accent} icon={BookOpenText} label="Caso operacional">
            <div style={{ color: C.text, fontStyle: "italic", marginBottom: 10 }}>{story.caso.scene}</div>
            <ol style={{ display: "grid", gap: 8, margin: 0, paddingLeft: 18 }}>
              {story.caso.steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </SectionBlock>
        </div>

        <div style={{ display: "grid", gap: 14, gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 260px), 1fr))", marginTop: 14 }}>
          <SectionBlock accent={theme.accent} icon={Wrench} label="Como aplicar na pratica">
            <div style={{ display: "grid", gap: 10 }}>
              {story.aplicar.map((item) => (
                <div key={item.label} style={{ borderLeft: `2px solid ${withAlpha(theme.accent, "55")}`, paddingLeft: 10 }}>
                  <div style={{ color: theme.accent, fontFamily: mono, fontSize: 9, fontWeight: 900, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                    {item.label}
                  </div>
                  <div style={{ marginTop: 3 }}>{item.text}</div>
                </div>
              ))}
            </div>
          </SectionBlock>
          <SectionBlock accent={C.coral} icon={AlertTriangle} label="Armadilhas comuns" tone="alert">
            <ul style={{ display: "grid", gap: 8, margin: 0, paddingLeft: 18 }}>
              {story.armadilhas.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </SectionBlock>
          <SectionBlock accent={C.sky} icon={MonitorSmartphone} label="Como entra no Radar Imobiliario">
            {story.radar}
          </SectionBlock>
        </div>

        <div
          style={{
            alignItems: "start",
            background: C.panel,
            border: `1px solid ${C.border}`,
            borderRadius: 8,
            display: "flex",
            gap: 12,
            marginTop: 16,
            padding: "13px 15px",
          }}
        >
          <Lightbulb aria-hidden="true" color={theme.accent} size={20} />
          <div style={{ color: C.muted, fontSize: 13, fontStyle: "italic", lineHeight: 1.65 }}>
            {story.sentimento}
          </div>
        </div>

        <div
          style={{
            alignItems: "center",
            borderTop: `1px solid ${C.border}`,
            display: "flex",
            gap: 12,
            justifyContent: "space-between",
            marginTop: 18,
            paddingTop: 16,
          }}
        >
          <button
            disabled={isFirst}
            onClick={goPrev}
            style={{
              alignItems: "center",
              background: isFirst ? C.card : C.panel,
              border: `1px solid ${C.border}`,
              borderRadius: 999,
              color: isFirst ? C.dim : C.text,
              cursor: isFirst ? "default" : "pointer",
              display: "inline-flex",
              fontFamily: mono,
              fontSize: 10,
              fontWeight: 900,
              gap: 6,
              padding: "8px 12px",
            }}
            type="button"
          >
            <ChevronLeft size={14} /> Anterior
          </button>
          <div style={{ display: "flex", gap: 6 }}>
            {activeModule.lessons.map((lesson, index) => (
              <button
                aria-label={`Ir para aula ${index + 1}`}
                key={lesson.id}
                onClick={() => setLesson(index)}
                style={{
                  background: index === activeLessonIndex ? theme.accent : C.line,
                  border: 0,
                  borderRadius: 999,
                  cursor: "pointer",
                  height: 7,
                  padding: 0,
                  transition: "width 0.15s",
                  width: index === activeLessonIndex ? 22 : 7,
                }}
                type="button"
              />
            ))}
          </div>
          <button
            disabled={isLast}
            onClick={goNext}
            style={{
              alignItems: "center",
              background: isLast ? C.card : C.panel,
              border: `1px solid ${C.border}`,
              borderRadius: 999,
              color: isLast ? C.dim : C.text,
              cursor: isLast ? "default" : "pointer",
              display: "inline-flex",
              fontFamily: mono,
              fontSize: 10,
              fontWeight: 900,
              gap: 6,
              padding: "8px 12px",
            }}
            type="button"
          >
            Proxima <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </section>
  );
}

function StatTile({ label, value, color = C.gold }) {
  return (
    <div
      style={{
        background: C.card,
        border: `1px solid ${withAlpha(color, "35")}`,
        borderRadius: 8,
        minWidth: 130,
        padding: "12px 14px",
      }}
    >
      <div
        style={{
          color,
          fontFamily: mono,
          fontSize: 18,
          fontWeight: 900,
          lineHeight: 1.2,
        }}
      >
        {value}
      </div>
      <div
        style={{
          color: C.muted,
          fontSize: 10,
          fontWeight: 800,
          letterSpacing: "0.08em",
          marginTop: 5,
          textTransform: "uppercase",
        }}
      >
        {label}
      </div>
    </div>
  );
}

function LessonRow({ lesson }) {
  const color = statusColor(lesson.status);
  const capturedDescription = Array.isArray(lesson.capturedDescription)
    ? lesson.capturedDescription.filter(Boolean)
    : [];
  const descriptionLabel = descriptionStatusCopy(lesson.descriptionCaptureStatus, capturedDescription.length);
  const transcriptLabel = transcriptStatusCopy(lesson.transcriptStudy);
  const transcriptAnalyzed = lesson.transcriptStudy?.status === "analyzed_from_transcript";
  const textualAnalyzed = lesson.transcriptStudy?.status === "analyzed_from_static_content";

  return (
    <article
      style={{
        borderTop: `1px solid ${C.border}`,
        display: "flex",
        flexDirection: "column",
        gap: 10,
        padding: "12px 0",
      }}
    >
      <div
        style={{
          alignItems: "start",
          display: "grid",
          gap: 12,
          gridTemplateColumns: "minmax(0, 1fr) 74px 108px",
        }}
      >
        <div
          style={{
            color: C.text,
            fontSize: 13,
            fontWeight: 800,
            lineHeight: 1.35,
          }}
        >
          {lesson.title}
        </div>
        <div style={{ color: C.muted, fontFamily: mono, fontSize: 11, fontWeight: 800, textAlign: "right" }}>
          {lesson.duration || "--"}
        </div>
        <div
          style={{
            background: withAlpha(color, alpha.glow),
            border: `1px solid ${withAlpha(color, alpha.border)}`,
            borderRadius: 999,
            color,
            fontFamily: mono,
            fontSize: 9,
            fontWeight: 900,
            justifySelf: "end",
            padding: "5px 8px",
            textTransform: "uppercase",
            whiteSpace: "nowrap",
          }}
        >
          {statusCopy(lesson.status)}
        </div>
      </div>
      <details
        style={{
          background: withAlpha(C.sky, "08"),
          border: `1px solid ${withAlpha(C.sky, "18")}`,
          borderRadius: 8,
          padding: "8px 10px",
        }}
      >
        <summary
          style={{
            color: capturedDescription.length ? C.sky : C.dim,
            cursor: "pointer",
            fontFamily: mono,
            fontSize: 9,
            fontWeight: 900,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          {descriptionLabel}
        </summary>
        {capturedDescription.length > 0 ? (
          <ul
            style={{
              color: C.muted,
              fontSize: 11,
              lineHeight: 1.55,
              margin: "8px 0 0",
              paddingLeft: 16,
            }}
          >
            {capturedDescription.map((line) => (
              <li key={line} style={{ marginBottom: 4, overflowWrap: "anywhere" }}>
                {line}
              </li>
            ))}
          </ul>
        ) : (
          <div style={{ color: C.dim, fontSize: 11, lineHeight: 1.55, marginTop: 8 }}>
            O Circle nao expos descricao estatica visivel nesta aula durante a captura.
          </div>
        )}
      </details>
      <details
        style={{
          background: withAlpha(C.teal, "08"),
          border: `1px solid ${withAlpha(C.teal, "22")}`,
          borderRadius: 8,
          padding: "8px 10px",
        }}
      >
        <summary
          style={{
            color: transcriptAnalyzed || textualAnalyzed ? C.teal : C.dim,
            cursor: "pointer",
            fontFamily: mono,
            fontSize: 9,
            fontWeight: 900,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          {transcriptLabel}
        </summary>
        <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, marginTop: 8 }}>
          {lesson.transcriptStudy?.summary || "Resumo da transcricao pendente."}
        </div>
        <div
          style={{
            color: C.dim,
            fontFamily: mono,
            fontSize: 9,
            fontWeight: 800,
            marginTop: 8,
            overflowWrap: "anywhere",
          }}
        >
          Dossie local: {lesson.studyLogPath}
        </div>
      </details>
      <div
        style={{
          display: "grid",
          gap: 8,
          gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 210px), 1fr))",
        }}
      >
        <div style={{ borderLeft: `2px solid ${C.line}`, paddingLeft: 10 }}>
          <div style={{ color: C.dim, fontFamily: mono, fontSize: 9, fontWeight: 900, textTransform: "uppercase" }}>
            Analise resumida
          </div>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, marginTop: 4 }}>
            {lesson.learningEvaluation}
          </div>
        </div>
        <div style={{ borderLeft: `2px solid ${withAlpha(C.gold, "55")}`, paddingLeft: 10 }}>
          <div style={{ color: C.gold, fontFamily: mono, fontSize: 9, fontWeight: 900, textTransform: "uppercase" }}>
            Aplicacao pratica na app
          </div>
          <div style={{ color: C.muted, fontSize: 11, lineHeight: 1.55, marginTop: 4 }}>
            {lesson.appInsertion}
          </div>
        </div>
      </div>
    </article>
  );
}

function ModuleBlock({ module }) {
  const analyzedCount = module.lessons.filter((lesson) => lesson.status === "analyzed").length;

  return (
    <section
      aria-label={module.title}
      style={{
        background: C.card,
        border: `1px solid ${C.border}`,
        borderRadius: 8,
        padding: "16px 18px 4px",
      }}
    >
      <div
        style={{
          alignItems: "baseline",
          display: "flex",
          gap: 12,
          justifyContent: "space-between",
          marginBottom: 10,
        }}
      >
        <div>
          <div
            style={{
              color: C.gold,
              fontFamily: mono,
              fontSize: 10,
              fontWeight: 900,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            {module.title}
          </div>
          <div style={{ color: C.text, fontSize: 15, fontWeight: 900, marginTop: 5 }}>
            {module.lessons.length} aulas - {module.duration}
          </div>
        </div>
        <div style={{ color: C.muted, fontFamily: mono, fontSize: 11, fontWeight: 800 }}>
          {analyzedCount}/{module.lessons.length} analisadas
        </div>
      </div>
      {module.lessons.map((lesson) => (
        <LessonRow key={lesson.id} lesson={lesson} />
      ))}
    </section>
  );
}

export function AuctionCourseKnowledge({ course = auctionCourseProgress }) {
  const stats = getAuctionCourseStats(course);
  const next = getNextAuctionCourseLesson(course);

  return (
    <section
      aria-label="Controle do curso de leilao"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 18,
        margin: "0 auto",
        maxWidth: 1180,
        width: "100%",
      }}
    >
      <div
        style={{
          borderBottom: `1px solid ${C.border}`,
          display: "flex",
          flexWrap: "wrap",
          gap: 18,
          justifyContent: "space-between",
          paddingBottom: 18,
        }}
      >
        <div
          style={{ minWidth: 0 }}
        >
          <div
            style={{
              color: C.gold,
              fontFamily: mono,
              fontSize: 10,
              fontWeight: 900,
              letterSpacing: "0.09em",
              marginBottom: 8,
              textTransform: "uppercase",
            }}
          >
            Caderno operacional
          </div>
          <h1 style={{ color: C.text, fontSize: 26, lineHeight: 1.15, margin: 0 }}>
            {course.title}
          </h1>
          <a
            href={course.sourceUrl}
            rel="noreferrer"
            target="_blank"
            style={{
              color: C.sky,
              display: "inline-block",
              fontFamily: mono,
              fontSize: 11,
              fontWeight: 800,
              marginTop: 10,
              overflowWrap: "anywhere",
              textDecoration: "none",
            }}
          >
            {course.sourceUrl}
          </a>
          <div
            style={{
              color: C.dim,
              fontFamily: mono,
              fontSize: 10,
              fontWeight: 800,
              lineHeight: 1.5,
              marginTop: 7,
              overflowWrap: "anywhere",
            }}
          >
            Dossie local: {course.studyLogPath}
          </div>
          <div
            style={{
              color: C.dim,
              fontFamily: mono,
              fontSize: 10,
              fontWeight: 800,
              lineHeight: 1.5,
              marginTop: 5,
              overflowWrap: "anywhere",
            }}
          >
            Playbook operacional: {course.operationalPlaybookPath}
          </div>
          <div
            style={{
              color: C.dim,
              fontFamily: mono,
              fontSize: 10,
              fontWeight: 800,
              lineHeight: 1.5,
              marginTop: 5,
              overflowWrap: "anywhere",
            }}
          >
            Captura validada: {course.captureManifestPath}
          </div>
        </div>
        <div
          style={{
            background: withAlpha(C.gold, alpha.glow),
            border: `1px solid ${withAlpha(C.gold, alpha.border)}`,
            borderRadius: 8,
            minWidth: 260,
            padding: "13px 14px",
          }}
        >
          <div
            style={{
              color: C.gold,
              fontFamily: mono,
              fontSize: 9,
              fontWeight: 900,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Proxima analise
          </div>
          <div style={{ color: C.text, fontSize: 13, fontWeight: 900, lineHeight: 1.45, marginTop: 7 }}>
            {next ? `${next.module.title} / ${next.lesson.title}` : "Curso totalmente analisado"}
          </div>
        </div>
      </div>

      <CourseStoryNotebook course={course} />

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <StatTile label="modulos" value={`${stats.totalModules} modulos`} />
        <StatTile label="aulas" value={`${stats.totalLessons} aulas`} color={C.sky} />
        <StatTile label="carga" value={course.totalDuration} color={C.purple} />
        <StatTile label="pendencias" value={`${stats.pending} pendentes`} color={stats.pending ? C.amber : C.teal} />
        <StatTile label="analisadas" value={`${stats.analyzed} analisadas`} color={C.teal} />
      </div>

      <div
        style={{
          display: "grid",
          gap: 14,
          gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 420px), 1fr))",
        }}
      >
        {course.modules.map((module) => (
          <ModuleBlock key={module.id} module={module} />
        ))}
      </div>
    </section>
  );
}

export default function Conhecimento({ course = auctionCourseProgress }) {
  return (
    <main
      style={{
        background: C.bg,
        color: C.text,
        minHeight: "100vh",
        padding: "26px 28px 44px",
      }}
    >
      <AuctionCourseKnowledge course={course} />
    </main>
  );
}
