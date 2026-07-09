import { type AppExchangeGetOutput, OpenAPI } from "~/client"

/**
 * Thin API layer for the OntoUI runtime ("generator") engine.
 *
 * Every call carries an `X-Onto-Session` header identifying the caller's engine
 * session, so concurrent tabs/users run independent applications on the backend
 * (see app/core/session_service.py). The session id is minted once per running
 * app in AppRunner and passed into each function here.
 *
 * All four calls go through the hand-rolled fetch helpers below rather than the
 * generated client, so we control the session header without a client regen.
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

/** Common headers: auth + the engine session id. */
async function sessionHeaders(
  sessionId: string,
): Promise<Record<string, string>> {
  return { "X-Onto-Session": sessionId, ...(await authHeader()) }
}

async function postJson<T>(
  path: string,
  body: unknown,
  sessionId: string,
): Promise<T> {
  const res = await fetch(`${OpenAPI.BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(await sessionHeaders(sessionId)),
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(`Request to ${path} failed with status ${res.status}`)
  }
  return (await res.json()) as T
}

async function getJson<T>(path: string, sessionId: string): Promise<T> {
  const res = await fetch(`${OpenAPI.BASE}${path}`, {
    method: "GET",
    headers: await sessionHeaders(sessionId),
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
export async function runAppModelById(
  id: string,
  sessionId: string,
): Promise<unknown> {
  return postJson(`/api/v1/appmodels/run/${id}`, undefined, sessionId)
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
  sessionId: string,
): Promise<unknown> {
  return postJson("/api/v1/generator/app_exchange_post", message, sessionId)
}

/** Read the current UI page the engine wants the frontend to render. */
export async function appExchangeGet(
  sessionId: string,
): Promise<AppExchangeGetOutput> {
  return getJson("/api/v1/generator/app_exchange_get", sessionId)
}

/** Shut the running application down on the server. */
export async function stopApplication(sessionId: string): Promise<unknown> {
  return getJson("/api/v1/generator/stop_application", sessionId)
}

// ---- Action payload builders ------------------------------------------------

/**
 * A button element in the JsonForms uischema carries the actions it can fire.
 * Each action has a graph_node, a type, and the DOM initiators (e.g. "onClick")
 * that trigger it.
 */
export interface UiAction {
  graph_node: string
  type: "submit" | "reset" | "shacl_validation" | "cancel" | "other" | string
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
    case "cancel":
      // The engine routes on action_graph_node alone (the exclusive gateway
      // matches it to the cancel ConditionExpression); no form data is sent,
      // since cancel discards the current entry rather than submitting it.
      return {
        message_type: "action",
        message_content: {
          action_type: "cancel",
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
