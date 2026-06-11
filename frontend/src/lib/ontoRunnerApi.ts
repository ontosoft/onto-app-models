import {
  type AppExchangeGetOutput,
  OntoModelGeneratorService,
  OpenAPI,
} from "~/client"

/**
 * Thin API layer for the OntoUI runtime ("generator") engine.
 *
 * Two of the engine endpoints can't go through the generated client:
 *  - POST /generator/app_exchange_post reads a raw `Request` on the backend,
 *    so openapi-ts produced a body-less method. We send the JSON body here.
 *  - POST /appmodels/run/{id} exists on the backend but is missing from the
 *    (stale) generated client, so we call it directly.
 *
 * The read-only GETs (`app_exchange_get`, `stop_application`) DO exist in the
 * generated client, so we reuse those.
 */

/** Resolve the bearer token the same way the generated client does. */
async function authHeader(): Promise<Record<string, string>> {
  const token = OpenAPI.TOKEN
  const value =
    typeof token === "function"
      ? // biome-ignore lint/suspicious/noExplicitAny: resolver signature
        await (token as any)({})
      : token
  return value ? { Authorization: `Bearer ${value}` } : {}
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${OpenAPI.BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(await authHeader()),
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(`Request to ${path} failed with status ${res.status}`)
  }
  return (await res.json()) as T
}

/**
 * Load THIS app model's RDF into the engine and start it.
 * (POST /api/v1/appmodels/run/{id} — auth + ownership enforced server-side.)
 */
export async function runAppModelById(id: string): Promise<unknown> {
  return postJson(`/api/v1/appmodels/run/${id}`, undefined)
}

// ---- The data-exchange loop -------------------------------------------------

export type FrontendMessage =
  | {
      message_type: "initiate_exchange"
      message_content: Record<string, never>
    }
  | { message_type: "action"; message_content: Record<string, unknown> }

/** Send a message to the running engine (initiate the exchange or an action). */
export async function appExchangePost(
  message: FrontendMessage,
): Promise<unknown> {
  return postJson("/api/v1/generator/app_exchange_post", message)
}

/** Read the current UI page the engine wants the frontend to render. */
export async function appExchangeGet(): Promise<AppExchangeGetOutput> {
  return OntoModelGeneratorService.readCurrentAppDataFromModel()
}

/** Shut the running application down on the server. */
export async function stopApplication(): Promise<unknown> {
  return OntoModelGeneratorService.stopApplication()
}

// ---- Action payload builders ------------------------------------------------

/**
 * A button element in the JsonForms uischema carries the actions it can fire.
 * Each action has a graph_node, a type, and the DOM initiators (e.g. "onClick")
 * that trigger it.
 */
export interface UiAction {
  graph_node: string
  type: "submit" | "reset" | "shacl_validation" | "other" | string
  initiators: string[]
}

/**
 * Build the `message_content` for an action exchange, mirroring the contract the
 * backend ProcessEngine expects (see owlprocessor/process_engine.py).
 */
export function buildActionMessage(
  action: UiAction,
  formGraphNode: string,
  formData: Record<string, unknown>,
): FrontendMessage {
  switch (action.type) {
    case "submit":
      return {
        message_type: "action",
        message_content: {
          action_type: "submit",
          action_graph_node: action.graph_node,
          form_graph_node: formGraphNode,
          form_data: formData,
        },
      }
    case "reset":
      return {
        message_type: "action",
        message_content: { action: "reset", form_data: {} },
      }
    case "shacl_validation":
      return {
        message_type: "action",
        message_content: {
          action_type: "shacl_validation",
          action_graph_node: action.graph_node,
        },
      }
    default:
      return {
        message_type: "action",
        message_content: {
          action_type: "other",
          action_graph_node: action.graph_node,
          form_graph_node: formGraphNode,
        },
      }
  }
}
