/**
 * Thin proxy to the Drachma /outcomes endpoint — used by the feedback-loop panel.
 */

const DRACHMA_URL = process.env.DRACHMA_URL ?? "http://localhost:8000";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const body = await req.json();
  const r = await fetch(`${DRACHMA_URL}/outcomes`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  const text = await r.text();
  return new Response(text, {
    status: r.status,
    headers: { "content-type": r.headers.get("content-type") ?? "application/json" },
  });
}
