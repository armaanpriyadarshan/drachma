"use client";

import { Fragment, useCallback, useMemo, useRef, useState } from "react";
import { PROFILES, type ProfileId, type ProfilePreset } from "@/app/lib/profiles";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Scenario = "traditional" | "drachma";

type AgentEvent =
  | { type: "profile"; profile: ProfilePreset }
  | { type: "start"; scenario: Scenario }
  | { type: "tool_call"; scenario: Scenario; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; scenario: Scenario; name: string; result: Record<string, unknown> }
  | { type: "message"; scenario: Scenario; content: string }
  | { type: "done"; scenario: Scenario }
  | { type: "error"; scenario: Scenario | "*"; message: string };

type ScoreBreakdown = {
  quality: number;
  coverage: number;
  outcome: number;
  value: number;
};

type Candidate = {
  product_id: string;
  name: string;
  brand?: string;
  price_usd: number;
  popularity_score?: number;
  composite_score?: number;
  review_volume?: number;
  seo_authority?: number;
  attestation_count?: number;
  scores?: ScoreBreakdown;
  rationale?: string;
};

type Attestation = {
  creator_name?: string;
  creator_reputation?: number;
  creator_specialties?: string[];
  testing_duration_days?: number;
  scores?: Record<string, number>;
};

type ReputationDelta = {
  creator_id: string;
  creator_name?: string;
  attestation_id: string;
  predicted: number;
  observed: number;
  delta: number;
  new_reputation: number;
};

type OutcomeResponse = {
  accepted: boolean;
  reputation_deltas: ReputationDelta[];
  reranked_candidates: Candidate[];
};

// ---------------------------------------------------------------------------
// Top-level Demo
// ---------------------------------------------------------------------------

export default function Demo() {
  const [profileId, setProfileId] = useState<ProfileId>("A");
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [doneScenarios, setDoneScenarios] = useState<Set<Scenario>>(new Set());
  const [feedback, setFeedback] = useState<OutcomeResponse | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const profile = PROFILES[profileId];

  const eventsByScenario = useMemo(() => {
    const t: AgentEvent[] = [];
    const d: AgentEvent[] = [];
    for (const e of events) {
      const s = (e as { scenario?: Scenario }).scenario;
      if (s === "traditional") t.push(e);
      else if (s === "drachma") d.push(e);
    }
    return { traditional: t, drachma: d };
  }, [events]);

  const changeProfile = useCallback((id: ProfileId) => {
    if (running) return;
    setProfileId(id);
    setEvents([]);
    setDoneScenarios(new Set());
    setFeedback(null);
  }, [running]);

  const run = useCallback(async () => {
    if (running) return;
    setEvents([]);
    setDoneScenarios(new Set());
    setFeedback(null);
    setRunning(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const res = await fetch("/api/agent", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ profile_id: profileId }),
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
  }, [running, profileId]);

  const drachmaMessage = eventsByScenario.drachma.find((e) => e.type === "message") as
    | Extract<AgentEvent, { type: "message" }>
    | undefined;

  const drachmaFinalId = drachmaMessage?.content.match(/FINAL:\s*(\S+)/)?.[1];
  const drachmaCandidates = extractCandidatesFromDrachma(eventsByScenario.drachma, feedback);
  const drachmaFinalName = drachmaFinalId
    ? drachmaCandidates?.find((c) => c.product_id === drachmaFinalId)?.name
    : undefined;

  return (
    <div className="flex flex-col gap-10">
      <ProfileSection
        profileId={profileId}
        profile={profile}
        onChange={changeProfile}
        onRun={run}
        running={running}
        hasRun={events.length > 0}
      />

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
          title="Mandarins feed"
          subtitle="Quality · expert coverage · outcome · value"
          tone="accent"
          events={eventsByScenario.drachma}
          done={doneScenarios.has("drachma")}
          running={running}
          overrideCandidates={drachmaCandidates}
          outcomeLabel={feedback ? "Post-outcome ranking" : undefined}
        />
      </div>

      <FeedbackLoop
        ready={doneScenarios.has("drachma") && !!drachmaFinalId}
        productId={drachmaFinalId}
        productName={drachmaFinalName}
        preferenceVector={profile.preference_profile.weights}
        feedback={feedback}
        onSubmitted={setFeedback}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Profile picker + user request card
// ---------------------------------------------------------------------------

function ProfileSection({
  profileId,
  profile,
  onChange,
  onRun,
  running,
  hasRun,
}: {
  profileId: ProfileId;
  profile: ProfilePreset;
  onChange: (id: ProfileId) => void;
  onRun: () => void;
  running: boolean;
  hasRun: boolean;
}) {
  return (
    <section className="bg-panel border border-hairline">
      <div className="flex items-stretch border-b border-hairline">
        {(Object.keys(PROFILES) as ProfileId[]).map((id) => {
          const p = PROFILES[id];
          const active = id === profileId;
          return (
            <button
              key={id}
              onClick={() => onChange(id)}
              disabled={running}
              className={
                "flex-1 text-left px-6 py-5 border-r border-hairline last:border-r-0 transition-colors " +
                (active
                  ? "bg-foreground text-background"
                  : running
                    ? "text-muted cursor-not-allowed"
                    : "hover:bg-background text-foreground")
              }
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={"label-strong " + (active ? "text-background" : "text-accent")}>
                  Profile {id}
                </span>
              </div>
              <div className="text-[14px] leading-tight font-medium">{p.label}</div>
            </button>
          );
        })}
      </div>

      <div className="flex items-start justify-between gap-6 px-8 py-7 border-b border-hairline">
        <div className="flex flex-col gap-2">
          <span className="label">User agent request</span>
          <p className="display text-[20px] leading-[1.3] max-w-3xl text-foreground">
            “{profile.summary}”
          </p>
          <p className="label mt-1">{profile.narrative}</p>
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

      <div className="grid grid-cols-1 md:grid-cols-2 divide-x divide-hairline">
        <WeightsPanel
          label="Attribute weights"
          weights={profile.preference_profile.weights}
          sub="What the user cares about in a knife."
        />
        <WeightsPanel
          label="Composite weights"
          weights={profile.preference_profile.composite_weights}
          sub="How the four Mandarins dimensions are blended for this user."
          tone="accent"
        />
      </div>

      <div className="flex gap-8 px-8 py-4 border-t border-hairline text-sm text-muted">
        <span>
          <span className="label">Budget</span>
          <span className="ml-2 text-foreground">
            ≤ ${String(profile.preference_profile.constraints.max_price_usd)}
          </span>
        </span>
        {Array.isArray(profile.preference_profile.constraints.blade_length_mm) && (
          <span>
            <span className="label">Blade length</span>
            <span className="ml-2 text-foreground">
              {(profile.preference_profile.constraints.blade_length_mm as number[])[0]}–
              {(profile.preference_profile.constraints.blade_length_mm as number[])[1]} mm
            </span>
          </span>
        )}
      </div>
    </section>
  );
}

function WeightsPanel({
  label,
  weights,
  sub,
  tone = "muted",
}: {
  label: string;
  weights: Record<string, number>;
  sub: string;
  tone?: "muted" | "accent";
}) {
  const bar = tone === "accent" ? "bg-accent" : "bg-foreground";
  const entries = Object.entries(weights).sort((a, b) => b[1] - a[1]);
  return (
    <div className="px-7 py-5 flex flex-col gap-2.5">
      <div className="flex items-baseline justify-between">
        <span className="label">{label}</span>
        <span className="label text-muted">{sub}</span>
      </div>
      <div className="grid grid-cols-[auto_1fr_auto] gap-x-3 gap-y-1.5 items-center">
        {entries.map(([k, v]) => (
          <Fragment key={k}>
            <span className="label whitespace-nowrap">{k.replace(/_/g, " ")}</span>
            <div className="h-[3px] bg-hairline overflow-hidden">
              <div className={"h-full " + bar} style={{ width: `${Math.round(v * 100)}%` }} />
            </div>
            <span className="font-mono text-[12px] tabular-nums w-[36px] text-right">
              {v.toFixed(2)}
            </span>
          </Fragment>
        ))}
      </div>
    </div>
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
  overrideCandidates,
  outcomeLabel,
}: {
  label: string;
  title: string;
  subtitle: string;
  tone: "muted" | "accent";
  events: AgentEvent[];
  done: boolean;
  running: boolean;
  overrideCandidates?: Candidate[];
  outcomeLabel?: string;
}) {
  const toolEvents = events.filter(
    (e) => e.type === "tool_call" || e.type === "tool_result"
  );
  const message = events.find((e) => e.type === "message") as
    | Extract<AgentEvent, { type: "message" }>
    | undefined;
  const finalId = finalProductId(message?.content);
  const matchedCandidate = findCandidateById(toolEvents, finalId, overrideCandidates);

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

      <div className="flex-1 px-7 py-6 flex flex-col gap-5 min-h-[240px]">
        {toolEvents.length === 0 && !running && (
          <p className="text-muted text-sm italic">
            Pick a profile, press Run demo.
          </p>
        )}
        {pairSteps(toolEvents).map((step, i) => (
          <StepCard
            key={i}
            index={i + 1}
            step={step}
            tone={tone}
            finalId={finalId}
            overrideCandidates={overrideCandidates && step.name === "drachma_feed_query" ? overrideCandidates : undefined}
            overrideLabel={outcomeLabel && step.name === "drachma_feed_query" ? outcomeLabel : undefined}
          />
        ))}
        {running && !message && toolEvents.length > 0 && <ThinkingRow />}
      </div>

      {message && (
        <RecommendationCard
          content={message.content}
          tone={tone}
          matchedCandidate={matchedCandidate}
        />
      )}
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

function ThinkingRow() {
  return (
    <div className="slide-in flex items-center gap-2 text-muted text-sm">
      <span className="inline-block size-1.5 rounded-full bg-muted pulse-dot" />
      <span className="label">Reasoning…</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Step pairing / extraction
// ---------------------------------------------------------------------------

type Step = {
  name: string;
  args: Record<string, unknown>;
  result?: Record<string, unknown>;
};

function pairSteps(events: AgentEvent[]): Step[] {
  const calls = events.filter((e) => e.type === "tool_call") as Extract<AgentEvent, { type: "tool_call" }>[];
  const results = events.filter((e) => e.type === "tool_result") as Extract<AgentEvent, { type: "tool_result" }>[];
  return calls.map((call, i) => ({
    name: call.name,
    args: call.args,
    result: results[i]?.result,
  }));
}

function finalProductId(content?: string): string | undefined {
  if (!content) return undefined;
  return content.match(/FINAL:\s*(\S+)/)?.[1];
}

function findCandidateById(
  events: AgentEvent[],
  productId: string | undefined,
  overrides?: Candidate[],
): Candidate | undefined {
  if (!productId) return undefined;
  if (overrides) {
    const hit = overrides.find((c) => c.product_id === productId);
    if (hit) return hit;
  }
  for (const e of events) {
    if (e.type !== "tool_result") continue;
    const cands = (e.result as { candidates?: Candidate[] }).candidates;
    if (!cands) continue;
    const hit = cands.find((c) => c.product_id === productId);
    if (hit) return hit;
  }
  return undefined;
}

function extractCandidatesFromDrachma(
  events: AgentEvent[],
  feedback: OutcomeResponse | null,
): Candidate[] | undefined {
  if (feedback) return feedback.reranked_candidates;
  for (const e of events) {
    if (e.type !== "tool_result") continue;
    if (e.name !== "drachma_feed_query") continue;
    const cands = (e.result as { candidates?: Candidate[] }).candidates;
    if (cands) return cands;
  }
  return undefined;
}

// ---------------------------------------------------------------------------
// Step card
// ---------------------------------------------------------------------------

function StepCard({
  index,
  step,
  tone,
  finalId,
  overrideCandidates,
  overrideLabel,
}: {
  index: number;
  step: Step;
  tone: "muted" | "accent";
  finalId?: string;
  overrideCandidates?: Candidate[];
  overrideLabel?: string;
}) {
  const { headline, blurb } = describeStep(step);
  return (
    <div className="slide-in flex flex-col gap-2.5">
      <div className="flex items-baseline gap-3">
        <span className="label-strong w-5 text-right tabular-nums">
          {String(index).padStart(2, "0")}
        </span>
        <div className="flex flex-col">
          <span className="font-sans text-[14px] text-foreground leading-tight">
            {overrideLabel ?? headline}
          </span>
          {blurb && <span className="label">{blurb}</span>}
        </div>
      </div>
      <div className="pl-8">
        <StepResult
          step={step}
          tone={tone}
          finalId={finalId}
          overrideCandidates={overrideCandidates}
        />
      </div>
    </div>
  );
}

function describeStep(step: Step): { headline: string; blurb?: string } {
  switch (step.name) {
    case "traditional_search":
      return {
        headline: "Searched products ranked by popularity",
        blurb: "SEO · review volume · ad spend",
      };
    case "get_product_reviews_summary":
      return {
        headline: `Fetched aggregate reviews for ${shortId(step.args.product_id)}`,
        blurb: "Star rating · review count",
      };
    case "drachma_feed_query":
      return {
        headline: "Queried the Mandarins feed",
        blurb: "Quality · coverage · outcome · value",
      };
    case "drachma_get_attestations":
      return {
        headline: `Inspected attestations for ${shortId(step.args.product_id)}`,
        blurb: "Creator-verified evidence",
      };
    default:
      return { headline: step.name };
  }
}

function shortId(v: unknown): string {
  if (typeof v !== "string") return "?";
  return v.replace(/^prod_/, "").split("_").slice(0, 2).join(" ");
}

function StepResult({
  step,
  tone,
  finalId,
  overrideCandidates,
}: {
  step: Step;
  tone: "muted" | "accent";
  finalId?: string;
  overrideCandidates?: Candidate[];
}) {
  if (overrideCandidates) {
    return (
      <CandidateTable candidates={overrideCandidates} tone={tone} finalId={finalId} showBreakdown />
    );
  }
  if (!step.result) {
    return <div className="label text-muted">waiting…</div>;
  }
  if ("error" in step.result) {
    return (
      <div className="label text-negative">
        error: {String(step.result.error)}
      </div>
    );
  }
  if (Array.isArray(step.result.candidates)) {
    const candidates = step.result.candidates as Candidate[];
    const showBreakdown = step.name === "drachma_feed_query";
    return (
      <CandidateTable
        candidates={candidates}
        tone={tone}
        finalId={finalId}
        showBreakdown={showBreakdown}
      />
    );
  }
  if ("average_stars" in step.result) {
    return (
      <ReviewsCard
        stars={step.result.average_stars as number}
        count={step.result.review_count as number}
      />
    );
  }
  if ("attestations" in step.result) {
    return (
      <AttestationsCard
        attestations={step.result.attestations as Attestation[]}
        count={(step.result.attestation_count as number) ?? (step.result.attestations as unknown[]).length}
        tone={tone}
      />
    );
  }
  return (
    <div className="label text-muted truncate">
      {JSON.stringify(step.result).slice(0, 80)}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Candidate table
// ---------------------------------------------------------------------------

const DIM_LABELS: Array<{ key: keyof ScoreBreakdown; short: string }> = [
  { key: "quality", short: "Q" },
  { key: "coverage", short: "C" },
  { key: "outcome", short: "O" },
  { key: "value", short: "V" },
];

function CandidateTable({
  candidates,
  tone,
  finalId,
  showBreakdown,
}: {
  candidates: Candidate[];
  tone: "muted" | "accent";
  finalId?: string;
  showBreakdown?: boolean;
}) {
  const score = (c: Candidate) => c.composite_score ?? c.popularity_score ?? 0;
  const barColor = tone === "accent" ? "bg-accent" : "bg-foreground";

  return (
    <div className="flex flex-col border border-hairline">
      <div className="grid grid-cols-[22px_1fr_auto_auto] gap-x-3 px-3 py-2 border-b border-hairline label">
        <span>#</span>
        <span>Product</span>
        <span className="text-right">Price</span>
        <span className="text-right">
          {showBreakdown ? "Composite" : "Score"}
        </span>
      </div>
      {candidates.map((c, i) => {
        const isFinal = c.product_id === finalId;
        return (
          <div
            key={c.product_id}
            className={
              "border-b border-hairline last:border-b-0 " +
              (isFinal ? "bg-accent-soft/40" : "")
            }
          >
            <div className="grid grid-cols-[22px_1fr_auto_auto] gap-x-3 items-center px-3 py-2">
              <span className="label-strong tabular-nums">{i + 1}</span>
              <div className="flex flex-col min-w-0">
                <span className="text-[13px] text-foreground truncate leading-tight">
                  {c.name}
                </span>
                <span className="label truncate">
                  {c.brand}
                  {c.attestation_count !== undefined && <>  ·  {c.attestation_count} attest.</>}
                  {c.review_volume !== undefined && <>  ·  {c.review_volume.toLocaleString()} reviews</>}
                </span>
              </div>
              <span className="font-mono text-[12px] text-foreground tabular-nums">
                ${c.price_usd}
              </span>
              <div className="flex items-center gap-2 w-[110px] justify-end">
                <div className="flex-1 h-[3px] bg-hairline overflow-hidden">
                  <div
                    className={"h-full " + barColor}
                    style={{ width: `${Math.round(score(c) * 100)}%` }}
                  />
                </div>
                <span className="font-mono text-[11px] text-foreground tabular-nums w-[32px] text-right">
                  {score(c).toFixed(2)}
                </span>
              </div>
            </div>
            {showBreakdown && c.scores && (
              <div className="grid grid-cols-4 gap-x-3 px-3 pb-2">
                {DIM_LABELS.map(({ key, short }) => (
                  <div key={key} className="flex items-center gap-2">
                    <span className="label text-[9.5px]">{short}</span>
                    <div className="flex-1 h-[2px] bg-hairline overflow-hidden">
                      <div
                        className={"h-full " + barColor}
                        style={{ width: `${Math.round((c.scores![key] ?? 0) * 100)}%` }}
                      />
                    </div>
                    <span className="font-mono text-[10px] tabular-nums text-muted w-[22px] text-right">
                      {(c.scores![key] ?? 0).toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Reviews card
// ---------------------------------------------------------------------------

function ReviewsCard({ stars, count }: { stars: number; count: number }) {
  return (
    <div className="flex items-center gap-4 border border-hairline px-4 py-2.5">
      <div className="flex items-baseline gap-1.5">
        <span className="font-sans text-2xl tabular-nums">{stars.toFixed(2)}</span>
        <span className="label">/ 5</span>
      </div>
      <div className="h-8 w-px bg-hairline" />
      <div className="flex flex-col">
        <span className="label">Reviews</span>
        <span className="font-sans text-[15px] tabular-nums">
          {count.toLocaleString()}
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Attestations card
// ---------------------------------------------------------------------------

function AttestationsCard({
  attestations,
  count,
  tone,
}: {
  attestations: Attestation[];
  count: number;
  tone: "muted" | "accent";
}) {
  const attrs = ["edge_retention", "steel_quality", "balance", "handle_ergonomics"] as const;
  const means = attrs.map((attr) => {
    const vals = attestations
      .map((a) => a.scores?.[attr])
      .filter((v): v is number => typeof v === "number");
    const mean = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
    return { attr, mean };
  });
  const specialties = Array.from(
    new Set(
      attestations.flatMap((a) => a.creator_specialties ?? [])
    )
  ).slice(0, 8);
  const avgRep = attestations.length
    ? attestations
        .map((a) => a.creator_reputation ?? 0)
        .reduce((a, b) => a + b, 0) / attestations.length
    : 0;
  const avgDays = attestations.length
    ? attestations
        .map((a) => a.testing_duration_days ?? 0)
        .reduce((a, b) => a + b, 0) / attestations.length
    : 0;
  const barColor = tone === "accent" ? "bg-accent" : "bg-foreground";
  return (
    <div className="flex flex-col gap-3 border border-hairline px-4 py-3">
      <div className="flex items-baseline gap-5">
        <Stat label="Creators" value={String(count)} />
        <Divider />
        <Stat label="Avg reputation" value={avgRep.toFixed(2)} />
        <Divider />
        <Stat label="Avg testing days" value={avgDays.toFixed(0)} />
      </div>

      <div className="grid grid-cols-[auto_1fr_auto] gap-x-3 gap-y-1.5 items-center">
        {means.map(({ attr, mean }) => (
          <Fragment key={attr}>
            <span className="label whitespace-nowrap">{attr.replace(/_/g, " ")}</span>
            <div className="h-[3px] bg-hairline overflow-hidden">
              <div
                className={"h-full " + barColor}
                style={{ width: `${Math.round((mean / 10) * 100)}%` }}
              />
            </div>
            <span className="font-mono text-[12px] tabular-nums w-[34px] text-right">
              {mean.toFixed(1)}
            </span>
          </Fragment>
        ))}
      </div>

      {specialties.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-1 border-t border-hairline">
          {specialties.map((s) => (
            <span key={s} className="label border border-hairline px-1.5 py-0.5">
              {s.replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="label">{label}</span>
      <span className="font-sans text-[15px] tabular-nums">{value}</span>
    </div>
  );
}
function Divider() {
  return <div className="h-8 w-px bg-hairline" />;
}

// ---------------------------------------------------------------------------
// Recommendation card
// ---------------------------------------------------------------------------

function RecommendationCard({
  content,
  tone,
  matchedCandidate,
}: {
  content: string;
  tone: "muted" | "accent";
  matchedCandidate?: Candidate;
}) {
  const finalMatch = content.match(/FINAL:\s*(\S+)/);
  const productId = finalMatch?.[1];
  const rationale = finalMatch
    ? content.slice(0, finalMatch.index).trim()
    : content.trim();
  const name = matchedCandidate?.name;
  const price = matchedCandidate?.price_usd;
  return (
    <div
      className={
        "px-7 py-6 border-t " +
        (tone === "accent"
          ? "border-hairline bg-accent-soft/40"
          : "border-hairline bg-background")
      }
    >
      <div className="flex items-baseline justify-between gap-4 mb-3">
        <div className="flex flex-col gap-0.5">
          <span className="label">Final recommendation</span>
          {name ? (
            <span className="display text-[18px] leading-tight text-foreground">{name}</span>
          ) : (
            productId && (
              <span className="font-mono text-[13px] text-foreground">{productId}</span>
            )
          )}
        </div>
        {price !== undefined && (
          <span className="font-sans text-xl tabular-nums">${price}</span>
        )}
      </div>
      <p className="text-[14px] leading-[1.6] text-foreground/90 max-w-[62ch]">{rationale}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Feedback loop
// ---------------------------------------------------------------------------

function FeedbackLoop({
  ready,
  productId,
  productName,
  preferenceVector,
  feedback,
  onSubmitted,
}: {
  ready: boolean;
  productId?: string;
  productName?: string;
  preferenceVector: Record<string, number>;
  feedback: OutcomeResponse | null;
  onSubmitted: (r: OutcomeResponse) => void;
}) {
  const [event, setEvent] = useState<"kept" | "returned" | "repurchased">("kept");
  const [satisfaction, setSatisfaction] = useState(0.9);
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
          preference_vector: preferenceVector,
          event,
          satisfaction,
        }),
      });
      const data = (await res.json()) as OutcomeResponse;
      onSubmitted(data);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="bg-panel border border-hairline">
      <div className="px-8 py-7 border-b border-hairline flex flex-col gap-1">
        <span className="label">Feedback loop</span>
        <h2 className="display text-2xl">Close the loop. Watch the ranking move.</h2>
        <p className="text-sm text-muted max-w-2xl">
          Submit an outcome for the recommended product. Creator reputations update
          based on how well each attestation predicted this user&apos;s satisfaction, and
          the Mandarins ranking above re-renders with the new signal.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr] gap-px bg-hairline">
        <div className="bg-panel px-8 py-7 flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <span className="label">Product under review</span>
            <span className="display text-[18px] text-foreground">
              {productName ?? (
                <span className="text-sm italic text-muted">— run the demo first —</span>
              )}
            </span>
          </div>

          <div className="flex flex-col gap-2">
            <span className="label">What happened after the purchase?</span>
            <div className="flex flex-wrap gap-2 mt-1">
              {(["kept", "returned", "repurchased"] as const).map((opt) => (
                <button
                  key={opt}
                  onClick={() => setEvent(opt)}
                  disabled={!ready}
                  className={
                    "label-strong px-4 py-2 rounded-full border transition-colors " +
                    (event === opt
                      ? "border-accent bg-accent text-background"
                      : "border-hairline-strong text-muted hover:text-foreground hover:border-foreground")
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

        <div className="bg-panel px-8 py-7 flex flex-col gap-3 min-h-[220px]">
          <span className="label">Reputation deltas</span>
          {feedback && feedback.reputation_deltas.length > 0 ? (
            <div className="flex flex-col gap-1.5">
              {feedback.reputation_deltas.slice(0, 6).map((d) => (
                <div
                  key={d.attestation_id}
                  className="grid grid-cols-[1fr_auto_auto] items-center gap-2 text-[12.5px]"
                >
                  <span className="truncate">{d.creator_name}</span>
                  <span
                    className={
                      "font-mono tabular-nums " +
                      (d.delta >= 0 ? "text-positive" : "text-negative")
                    }
                  >
                    {d.delta >= 0 ? "+" : ""}{d.delta.toFixed(3)}
                  </span>
                  <span className="font-mono text-[11px] tabular-nums text-muted w-[42px] text-right">
                    → {d.new_reputation.toFixed(2)}
                  </span>
                </div>
              ))}
              <p className="label text-[10px] pt-2 border-t border-hairline text-muted leading-relaxed">
                Direction depends on how close each creator&apos;s predicted
                satisfaction came to this user&apos;s observed satisfaction.
              </p>
            </div>
          ) : feedback ? (
            <p className="text-sm text-muted italic">
              No specialist attestations moved. Try a stronger outcome.
            </p>
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
