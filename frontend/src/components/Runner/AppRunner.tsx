import { JsonForms } from "@jsonforms/react"
import { useNavigate } from "@tanstack/react-router"
import { Loader2, Power } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"

import type { AppExchangeGetOutput } from "~/client"
import { RunnerActionContext } from "~/components/Runner/ActionContext"
import { GraphPanel } from "~/components/Runner/GraphPanel"
import { shadcnRenderers } from "~/components/Runner/renderers"
import { Button } from "~/components/ui/button"
import useCustomToast from "~/hooks/useCustomToast"
import {
  appExchangeGet,
  appExchangePost,
  buildActionMessage,
  runAppModelById,
  stopApplication,
  type UiAction,
} from "~/lib/ontoRunnerApi"

interface AppRunnerProps {
  appModelId: string
  appModelTitle?: string
}

type Phase = "starting" | "ready" | "error"

/** message_content for a "form"/"message-box" layout. */
interface FormContent {
  graph_node: string
  schema: object
  uischema: object
  data: Record<string, unknown>
}

function asMessage(content: unknown): string {
  if (typeof content === "string") return content
  if (content && typeof content === "object") {
    const c = content as Record<string, unknown>
    return String(c.message_content ?? c.message ?? JSON.stringify(content))
  }
  return String(content ?? "")
}

export function AppRunner({ appModelId, appModelTitle }: AppRunnerProps) {
  const navigate = useNavigate()
  const { showErrorToast } = useCustomToast()

  const [phase, setPhase] = useState<Phase>("starting")
  const [errorMsg, setErrorMsg] = useState<string>("")
  const [page, setPage] = useState<AppExchangeGetOutput | null>(null)
  const [formData, setFormData] = useState<Record<string, unknown>>({})
  const [busy, setBusy] = useState(false)
  // Bumped on every page change so JsonForms re-initialises with fresh data.
  const [pageKey, setPageKey] = useState(0)
  // Latest non-empty output graph. The engine sends the cumulative graph on
  // every response, but if one ever arrives empty we keep showing the last one.
  const [graph, setGraph] = useState("")

  const startedRef = useRef(false)
  // One engine session per mounted runner, so each tab runs its own
  // independent application on the backend (X-Onto-Session header).
  const sessionId = useRef(crypto.randomUUID()).current

  const applyPage = useCallback((next: AppExchangeGetOutput) => {
    setPage(next)
    const content = next.message_content as Partial<FormContent>
    setFormData((content?.data as Record<string, unknown>) ?? {})
    setPageKey((k) => k + 1)
    if (next.output_knowledge_graph?.trim())
      setGraph(next.output_knowledge_graph)
  }, [])

  // Start the application once, then pull the first page.
  useEffect(() => {
    if (startedRef.current) return
    startedRef.current = true

    ;(async () => {
      try {
        await runAppModelById(appModelId, sessionId)
        await appExchangePost(
          {
            message_type: "initiate_exchange",
            message_content: {},
          },
          sessionId,
        )
        const first = await appExchangeGet(sessionId)
        applyPage(first)
        setPhase("ready")
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : String(err))
        setPhase("error")
      }
    })()
  }, [appModelId, applyPage, sessionId])

  const formGraphNode =
    (page?.message_content as Partial<FormContent> | undefined)?.graph_node ??
    ""

  const triggerAction = useCallback(
    (action: UiAction) => {
      setBusy(true)
      ;(async () => {
        try {
          await appExchangePost(
            buildActionMessage(action, formGraphNode, formData),
            sessionId,
          )
          const next = await appExchangeGet(sessionId)
          applyPage(next)
        } catch (err) {
          showErrorToast(
            err instanceof Error ? err.message : "Action failed on the server",
          )
        } finally {
          setBusy(false)
        }
      })()
    },
    [formGraphNode, formData, applyPage, showErrorToast, sessionId],
  )

  const handleStop = useCallback(() => {
    ;(async () => {
      try {
        await stopApplication(sessionId)
      } catch {
        // best-effort shutdown; navigate away regardless
      }
      navigate({ to: "/appmodels" })
    })()
  }, [navigate, sessionId])

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">
            {appModelTitle ?? "Running application"}
          </h1>
          {busy ? (
            <p className="flex items-center gap-1 text-sm text-muted-foreground">
              <Loader2 className="size-3 animate-spin" /> Working…
            </p>
          ) : null}
        </div>
        <Button variant="outline" onClick={handleStop}>
          <Power /> Stop
        </Button>
      </div>

      {phase === "starting" ? (
        <div className="flex items-center gap-2 py-16 text-muted-foreground">
          <Loader2 className="size-5 animate-spin" />
          Starting application on the server…
        </div>
      ) : null}

      {phase === "error" ? (
        <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4 text-destructive">
          <p className="font-medium">Could not start the application.</p>
          <p className="mt-1 text-sm">{errorMsg}</p>
        </div>
      ) : null}

      {phase === "ready" && page ? (
        <RunnerActionContext.Provider
          value={{ triggerAction, formGraphNode, busy }}
        >
          <RenderPage
            page={page}
            pageKey={pageKey}
            data={formData}
            onDataChange={setFormData}
          />
          <GraphPanel turtle={graph} />
        </RunnerActionContext.Provider>
      ) : null}
    </div>
  )
}

function RenderPage({
  page,
  pageKey,
  data,
  onDataChange,
}: {
  page: AppExchangeGetOutput
  pageKey: number
  data: Record<string, unknown>
  onDataChange: (d: Record<string, unknown>) => void
}) {
  if (page.message_type === "layout") {
    const content = page.message_content as unknown as FormContent
    return (
      <div className="rounded-lg border p-6">
        <JsonForms
          key={pageKey}
          schema={content.schema}
          // biome-ignore lint/suspicious/noExplicitAny: server-driven uischema
          uischema={content.uischema as any}
          data={data}
          renderers={shadcnRenderers}
          cells={[]}
          onChange={({ data: d }) => onDataChange(d as Record<string, unknown>)}
        />
      </div>
    )
  }

  if (page.message_type === "error") {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4 text-destructive">
        {asMessage(page.message_content)}
      </div>
    )
  }

  // notification / information
  return (
    <div className="rounded-lg border bg-muted/30 p-4">
      {asMessage(page.message_content)}
    </div>
  )
}
