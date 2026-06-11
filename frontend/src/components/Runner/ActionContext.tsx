import { createContext, useContext } from "react"

import type { UiAction } from "~/lib/ontoRunnerApi"

/**
 * Bridges the JsonForms render tree back to the AppRunner. The action-button
 * renderer is created deep inside JsonForms and has no direct access to the
 * runner's exchange logic, so it reaches it through this context.
 */
export interface RunnerActionContextValue {
  /** Fire an action against the running engine and advance to the next page. */
  triggerAction: (action: UiAction) => void
  /** The graph node of the form currently on screen (submit needs it). */
  formGraphNode: string
  /** True while an exchange is in flight — used to disable buttons. */
  busy: boolean
}

export const RunnerActionContext =
  createContext<RunnerActionContextValue | null>(null)

export function useRunnerActions(): RunnerActionContextValue {
  const ctx = useContext(RunnerActionContext)
  if (!ctx) {
    throw new Error(
      "useRunnerActions must be used within a RunnerActionContext",
    )
  }
  return ctx
}
