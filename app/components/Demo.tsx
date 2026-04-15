"use client";

import { useCallback, useMemo, useRef, useState } from "react";

type Scenario = "traditional" | "drachma";

type AgentEvent =
  | { type: "start"; scenario: Scenario }
  | { type: "tool_call"; scenario: Scenario; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; scenario: Scenario; name: string; result: Record<string, unknown> }
  | { type: "message"; scenario: Scenario; content: string }
  | { type: "done"; scenario: Scenario }
  | { type: "error"; scenario: Scenario; message: string };

const DEFAULT_REQUEST = {
  summary:
    "A chef's knife for daily serious home cooking. I maintain my own edges on a whetstone and don't mind reactive carbon steel. Edge retention and steel quality matter most.",
  preference_profile: {
    weights: {
      edge_retention: 0.45,
      steel_quality: 0.3,
      balance: 0.15,
      handle_ergonomics: 0.1,
    },
    constraints: {
      max_price_usd: 400,
      blade_length_mm: [200, 240],
    },
  },
};

export default function Demo() {
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [doneScenarios, setDoneScenarios] = useState<Set<Scenario>>(new Set());
  const abortRef = useRef<AbortController | null>(null);

  const eventsByScenario = useMemo(() => {
    const t: AgentEvent[] = [];
    const d: AgentEvent[] = [];
    for (const e of events) {
      if ((e as { scenario: Scenario }).scenario === "traditional") t.push(e);
      else if ((e as { scenario: Scenario }).scenario === "drachma") d.push(e);
    }
    return { traditional: t, drachma: d };
  }, [events]);

  const run = useCallback(async () => {
    if (running) return;
    setEvents([]);
    setDoneScenarios(new Set());
    setRunning(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const res = await fetch("/api/agent", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ user_request: DEFAULT_REQUEST }),
        signal: ctrl.signal,
      });
      if (!res.ok || !res.body) {
        setRunning(false);
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const part of parts) {
          const dataLine = part.split("\n").find((l) => l.startsWith("data: "));
          if (!dataLine) continue;
          const payload = dataLine.slice(6);
          if (!payload) continue;
          try {
            const ev = JSON.parse(payload) as AgentEvent;
            setEvents((prev) => [...prev, ev]);
            if (ev.type === "done") {
              setDoneScenarios((prev) => new Set(prev).add(ev.scenario));
            }
          } catch {
            // ignore
          }
        }
      }
    } finally {
      setRunning(false);
    }
  }, [running]);

  return (
    <div className="flex flex-col gap-10">
      <UserRequestCard onRun={run} running={running} hasRun={events.length > 0} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-px bg-hairline">
        <ScenarioColumn
          label="Scenario A"
          title="Traditional ranking"
          subtitle="SEO authority · review volume · ad spend"
          tone="muted"
          events={eventsByScenario.traditional}
          done={doneScenarios.has("traditional")}
          running={running}
        />
        <ScenarioColumn
          label="Scenario B"
          title="Drachma feed"
          subtitle="Creator attestations · outcome data · niche fit"
          tone="accent"
          events={eventsByScenario.drachma}
          done={doneScenarios.has("drachma")}
          running={running}
        />
      </div>
      <FeedbackLoop doneScenarios={doneScenarios} events={eventsByScenario.drachma} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// User request card
// ---------------------------------------------------------------------------

function UserRequestCard({
  onRun,
  running,
  hasRun,
}: {
  onRun: () => void;
  running: boolean;
  hasRun: boolean;
}) {
  return (
    <section className="bg-panel border border-hairline">
      <div className="flex items-start justify-between gap-6 px-8 py-7 border-b border-hairline">
        <div className="flex flex-col gap-2">
          <span className="label">User agent request</span>
          <p className="display text-[22px] leading-[1.25] max-w-3xl text-foreground">
            “{DEFAULT_REQUEST.summary}”
          </p>
        </div>
        <button
          onClick={onRun}
          disabled={running}
          className={
            "shrink-0 label-strong px-5 py-3 border transition-colors " +
            (running
              ? "border-hairline text-muted cursor-not-allowed"
              : "border-foreground text-foreground hover:bg-foreground hover:text-background")
          }
        >
          {running ? "Running…" : hasRun ? "Run again" : "Run demo"}
        </button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 border-t border-hairline">
        {Object.entries(DEFAULT_REQUEST.preference_profile.weights).map(([k, v]) => (
          <div key={k} className="px-6 py-4 border-r border-hairline last:border-r-0">
            <div className="label">{k.replace(/_/g, " ")}</div>
            <div className="mt-1 font-sans text-2xl tracking-tight">
              {Number(v).toFixed(2)}
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-8 px-8 py-4 border-t border-hairline text-sm text-muted">
        <span>
          <span className="label">Budget</span>
          <span className="ml-2 text-foreground">
            ≤ ${DEFAULT_REQUEST.preference_profile.constraints.max_price_usd}
          </span>
        </span>
        <span>
          <span className="label">Blade length</span>
          <span className="ml-2 text-foreground">
            {DEFAULT_REQUEST.preference_profile.constraints.blade_length_mm[0]}–
            {DEFAULT_REQUEST.preference_profile.constraints.blade_length_mm[1]} mm
          </span>
        </span>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Scenario column
// ---------------------------------------------------------------------------

function ScenarioColumn({
  label,
  title,
  subtitle,
  tone,
  events,
  done,
  running,
}: {
  label: string;
  title: string;
  subtitle: string;
  tone: "muted" | "accent";
  events: AgentEvent[];
  done: boolean;
  running: boolean;
}) {
  const toolEvents = events.filter(
    (e) => e.type === "tool_call" || e.type === "tool_result"
  );
  const message = events.find((e) => e.type === "message") as
    | Extract<AgentEvent, { type: "message" }>
    | undefined;

  return (
    <div className="bg-panel flex flex-col">
      <header className="px-7 py-6 border-b border-hairline flex flex-col gap-1">
        <div className="flex items-center gap-3">
          <span
            className={
              "label-strong " + (tone === "accent" ? "text-accent" : "text-foreground")
            }
          >
            {label}
          </span>
          {running && !done && <LivePulse />}
          {done && <span className="label text-positive">Done</span>}
        </div>
        <h2 className="display text-2xl text-foreground">{title}</h2>
        <span className="label">{subtitle}</span>
      </header>

      <div className="flex-1 px-7 py-6 flex flex-col gap-2 min-h-[220px]">
        {toolEvents.length === 0 && !running && (
          <p className="text-muted text-sm italic">
            Press <span className="label-strong">Run demo</span> to see the agent think.
          </p>
        )}
        {toolEvents.map((e, i) => (
          <ToolEventRow key={i} event={e} />
        ))}
      </div>

      {message && <RecommendationCard content={message.content} tone={tone} />}
    </div>
  );
}

function LivePulse() {
  return (
    <span className="label flex items-center gap-1.5">
      <span className="inline-block size-1.5 rounded-full bg-accent pulse-dot" />
      Live
    </span>
  );
}

function ToolEventRow({ event }: { event: AgentEvent }) {
  if (event.type === "tool_call") {
    return (
      <div className="slide-in flex items-baseline gap-2 font-mono text-[12.5px] text-foreground">
        <span className="label text-accent">call</span>
        <span className="truncate">
          {event.name}
          <span className="text-muted">({formatArgs(event.args)})</span>
        </span>
      </div>
    );
  }
  if (event.type === "tool_result") {
    return (
      <div className="slide-in flex items-baseline gap-2 font-mono text-[12.5px] text-muted">
        <span className="label">recv</span>
        <span className="truncate">{summarizeResult(event.name, event.result)}</span>
      </div>
    );
  }
  return null;
}

function formatArgs(args: Record<string, unknown>): string {
  const parts: string[] = [];
  for (const [k, v] of Object.entries(args)) {
    if (typeof v === "string") parts.push(`${k}: "${v}"`);
    else if (typeof v === "number" || typeof v === "boolean")
      parts.push(`${k}: ${v}`);
    else parts.push(`${k}: …`);
  }
  const s = parts.join(", ");
  return s.length > 90 ? s.slice(0, 87) + "…" : s;
}

function summarizeResult(name: string, result: Record<string, unknown>): string {
  if ("error" in result) return `error: ${result.error}`;
  if (Array.isArray(result.candidates)) {
    const top = (result.candidates as Record<string, unknown>[])[0];
    return `${(result.candidates as unknown[]).length} candidates, top: ${top?.name}`;
  }
  if ("attestations" in result) {
    return `${result.attestation_count ?? (result.attestations as unknown[]).length} attestations for ${result.product_name}`;
  }
  if ("average_stars" in result) {
    return `${result.average_stars}★ over ${result.review_count} reviews`;
  }
  return JSON.stringify(result).slice(0, 80);
}

// ---------------------------------------------------------------------------
// Recommendation card
// ---------------------------------------------------------------------------

function RecommendationCard({
  content,
  tone,
}: {
  content: string;
  tone: "muted" | "accent";
}) {
  const finalMatch = content.match(/FINAL:\s*(\S+)/);
  const productId = finalMatch?.[1];
  const rationale = finalMatch
    ? content.slice(0, finalMatch.index).trim()
    : content.trim();
  return (
    <div
      className={
        "px-7 py-6 border-t " +
        (tone === "accent"
          ? "border-hairline bg-accent-soft/40"
          : "border-hairline bg-background")
      }
    >
      <div className="label mb-2">Final recommendation</div>
      {productId && (
        <div className="mb-3 font-mono text-[13px] text-foreground">{productId}</div>
      )}
      <p className="text-[15px] leading-[1.6] text-foreground max-w-[62ch]">
        {rationale}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Feedback loop
// ---------------------------------------------------------------------------

function FeedbackLoop({
  doneScenarios,
  events,
}: {
  doneScenarios: Set<Scenario>;
  events: AgentEvent[];
}) {
  const drachmaMessage = events.find((e) => e.type === "message") as
    | Extract<AgentEvent, { type: "message" }>
    | undefined;
  const productId = drachmaMessage?.content.match(/FINAL:\s*(\S+)/)?.[1];
  const ready = doneScenarios.has("drachma") && !!productId;

  const [event, setEvent] = useState<"kept" | "returned" | "repurchased">("kept");
  const [satisfaction, setSatisfaction] = useState(0.95);
  const [submitted, setSubmitted] = useState<null | Record<string, unknown>>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!ready || !productId) return;
    setSubmitting(true);
    try {
      const res = await fetch("/api/outcomes", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          product_id: productId,
          user_profile_tag: "edge_retention_heavy",
          event,
          satisfaction,
        }),
      });
      const data = await res.json();
      setSubmitted(data);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="bg-panel border border-hairline">
      <div className="px-8 py-7 border-b border-hairline flex flex-col gap-1">
        <span className="label">Feedback loop</span>
        <h2 className="display text-2xl">Close the loop.</h2>
        <p className="text-sm text-muted max-w-2xl">
          Once the user keeps or returns the product, the agent reports back.
          That signal updates creator reputation and refines matching for the next user with
          a similar preference profile. The outcome data is the moat.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr] gap-px bg-hairline">
        <div className="bg-panel px-8 py-7 flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <span className="label">Product under review</span>
            <span className="font-mono text-[13px]">
              {productId ?? <span className="text-muted">— run the demo first —</span>}
            </span>
          </div>

          <div className="flex flex-col gap-2">
            <span className="label">Outcome event</span>
            <div className="flex gap-0">
              {(["kept", "returned", "repurchased"] as const).map((opt) => (
                <button
                  key={opt}
                  onClick={() => setEvent(opt)}
                  disabled={!ready}
                  className={
                    "label-strong px-4 py-2.5 border -ml-px first:ml-0 transition-colors " +
                    (event === opt
                      ? "border-foreground bg-foreground text-background"
                      : "border-hairline-strong text-muted hover:text-foreground")
                  }
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <span className="label">Satisfaction · {satisfaction.toFixed(2)}</span>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={satisfaction}
              onChange={(e) => setSatisfaction(parseFloat(e.target.value))}
              disabled={!ready}
              className="accent-[var(--accent)]"
            />
          </div>

          <button
            onClick={submit}
            disabled={!ready || submitting}
            className={
              "label-strong self-start px-5 py-3 border transition-colors " +
              (!ready || submitting
                ? "border-hairline text-muted cursor-not-allowed"
                : "border-accent text-accent hover:bg-accent hover:text-background")
            }
          >
            {submitting ? "Submitting…" : "Submit outcome"}
          </button>
        </div>

        <div className="bg-panel px-8 py-7 flex flex-col gap-3">
          <span className="label">Signal impact</span>
          {submitted ? (
            <>
              <div className="flex flex-col gap-1">
                <span className="label">Accepted</span>
                <span className="font-sans text-2xl text-positive">
                  {String((submitted as { accepted?: boolean }).accepted ?? false)}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="label">Attestations affected</span>
                <span className="font-sans text-2xl">
                  {String(
                    (submitted as { affected_attestations?: number })
                      .affected_attestations ?? 0
                  )}
                </span>
              </div>
              <p className="text-xs text-muted leading-relaxed pt-2 border-t border-hairline">
                Creator reputation for each of the attestations above shifts toward
                alignment with this outcome. The next query against this profile sees
                the updated ranking.
              </p>
            </>
          ) : (
            <p className="text-sm text-muted italic">
              No signal submitted yet.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
