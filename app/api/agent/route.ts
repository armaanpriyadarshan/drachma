/**
 * Runs both scenarios through OpenAI function calling and streams tool-call /
 * tool-result / message events as Server-Sent Events.
 *
 * Event shape (JSON per SSE message):
 *   { type: "start", scenario }
 *   { type: "tool_call", scenario, name, args }
 *   { type: "tool_result", scenario, name, result }
 *   { type: "message", scenario, content }
 *   { type: "done", scenario }
 *   { type: "error", scenario, message }
 */

import OpenAI from "openai";
import {
  DEFAULT_USER_REQUEST,
  DRACHMA_TOOLS,
  SYSTEM_PROMPT_DRACHMA,
  SYSTEM_PROMPT_TRADITIONAL,
  TOOL_IMPLS,
  TRADITIONAL_TOOLS,
} from "@/app/lib/agent-tools";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MODEL = process.env.OPENAI_MODEL ?? "gpt-4.1";

type Scenario = "traditional" | "drachma";

type Emit = (event: Record<string, unknown>) => void;

async function runScenario(
  client: OpenAI,
  scenario: Scenario,
  userRequest: unknown,
  emit: Emit
): Promise<void> {
  const systemPrompt =
    scenario === "traditional" ? SYSTEM_PROMPT_TRADITIONAL : SYSTEM_PROMPT_DRACHMA;
  const tools = scenario === "traditional" ? TRADITIONAL_TOOLS : DRACHMA_TOOLS;

  emit({ type: "start", scenario });

  const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
    { role: "system", content: systemPrompt },
    { role: "user", content: JSON.stringify(userRequest) },
  ];

  for (let step = 0; step < 8; step++) {
    const resp = await client.chat.completions.create({
      model: MODEL,
      messages,
      tools,
      tool_choice: "auto",
    });
    const msg = resp.choices[0].message;

    messages.push(msg);

    if (msg.tool_calls && msg.tool_calls.length > 0) {
      for (const call of msg.tool_calls) {
        if (call.type !== "function") continue;
        let args: Record<string, unknown> = {};
        try {
          args = JSON.parse(call.function.arguments || "{}");
        } catch {
          args = {};
        }
        emit({ type: "tool_call", scenario, name: call.function.name, args });
        const impl = TOOL_IMPLS[call.function.name];
        let result: unknown;
        try {
          result = impl
            ? await impl(args)
            : { error: `no implementation for ${call.function.name}` };
        } catch (e) {
          result = { error: (e as Error).message };
        }
        emit({ type: "tool_result", scenario, name: call.function.name, result });
        messages.push({
          role: "tool",
          tool_call_id: call.id,
          content: JSON.stringify(result).slice(0, 6000),
        });
      }
      continue;
    }

    const content = msg.content ?? "";
    emit({ type: "message", scenario, content });
    emit({ type: "done", scenario });
    return;
  }

  emit({ type: "error", scenario, message: "step budget exhausted" });
}

export async function POST(req: Request) {
  if (!process.env.OPENAI_API_KEY) {
    return new Response("OPENAI_API_KEY not set", { status: 500 });
  }

  let body: { user_request?: unknown } = {};
  try {
    body = await req.json();
  } catch {
    // allow empty body
  }
  const userRequest = body.user_request ?? DEFAULT_USER_REQUEST;

  const client = new OpenAI();
  const encoder = new TextEncoder();

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const emit: Emit = (event) => {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
      };
      try {
        await Promise.all([
          runScenario(client, "traditional", userRequest, emit),
          runScenario(client, "drachma", userRequest, emit),
        ]);
      } catch (e) {
        emit({ type: "error", scenario: "*", message: (e as Error).message });
      } finally {
        controller.enqueue(encoder.encode("event: end\ndata: {}\n\n"));
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "content-type": "text/event-stream",
      "cache-control": "no-cache, no-transform",
      connection: "keep-alive",
    },
  });
}
