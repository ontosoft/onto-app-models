import { useQuery } from "@tanstack/react-query"
import NavigatedViewer from "bpmn-js/lib/NavigatedViewer"
import type Canvas from "diagram-js/lib/core/Canvas"
import { Check, Copy, Download } from "lucide-react"
import { useEffect, useRef, useState } from "react"

import "bpmn-js/dist/assets/diagram-js.css"
import "bpmn-js/dist/assets/bpmn-js.css"
import "bpmn-js/dist/assets/bpmn-font/css/bpmn.css"

import { AppmodelsService } from "~/client"
import { Button } from "~/components/ui/button"
import { Skeleton } from "~/components/ui/skeleton"

/**
 * Renders the model's workflow with bpmn-js. The XML comes from
 * GET /appmodels/{id}/bpmn, which already contains the diagram layout
 * (BPMNDiagram section), so the viewer only has to draw it.
 *
 * Used by the View Model dialog and the /appmodels/$id detail page.
 */
export const BpmnDiagram = ({ id, title }: { id: string; title: string }) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [renderError, setRenderError] = useState<string | null>(null)

  const {
    data: xml,
    isPending,
    error,
  } = useQuery({
    queryKey: ["appmodels", id, "bpmn"],
    // The endpoint responds with application/xml; axios hands non-JSON
    // bodies through as a plain string.
    queryFn: async () =>
      (await AppmodelsService.exportAppModelBpmn({ id })) as string,
  })

  useEffect(() => {
    if (!xml || !containerRef.current) return
    let cancelled = false
    setRenderError(null)
    const viewer = new NavigatedViewer({ container: containerRef.current })
    viewer
      .importXML(xml)
      .then(() => {
        if (cancelled) return
        // scale the whole process into view instead of showing the top-left corner
        const canvas = viewer.get("canvas") as Canvas
        canvas.zoom("fit-viewport")
      })
      .catch((err: Error) => {
        // destroying the viewer while importXML is in flight (tab switched,
        // dialog closed, or React StrictMode's dev double-mount) rejects the
        // import promise - that is teardown, not a render failure
        if (!cancelled) setRenderError(err.message)
      })
    // tear the viewer down when the tab/dialog closes, otherwise every
    // reopen would stack another canvas into the container
    return () => {
      cancelled = true
      viewer.destroy()
    }
  }, [xml])

  const downloadBpmn = () => {
    if (!xml) return
    const url = URL.createObjectURL(
      new Blob([xml], { type: "application/xml" }),
    )
    const a = document.createElement("a")
    a.href = url
    a.download = `${title.replace(/[^\w.-]+/g, "-")}.bpmn`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (isPending) return <Skeleton className="h-full w-full" />
  if (error || renderError)
    return (
      <div className="p-4 text-sm text-destructive">
        Could not render the BPMN diagram:{" "}
        {renderError ??
          (error instanceof Error ? error.message : "unknown error")}
      </div>
    )

  return (
    <div className="relative h-full w-full">
      {/* bpmn-js draws black strokes on a transparent canvas - a fixed white
          background keeps the diagram readable in dark mode too */}
      <div ref={containerRef} className="h-full w-full rounded-md bg-white" />
      <Button
        variant="outline"
        size="sm"
        className="absolute top-2 right-2"
        onClick={downloadBpmn}
      >
        <Download />
        .bpmn
      </Button>
    </div>
  )
}

/** The model's RDF/Turtle source as a scrollable block with a copy button. */
export const RdfView = ({ rdf }: { rdf: string }) => {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(rdf)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative h-full">
      <pre className="h-full overflow-auto rounded-md bg-muted p-4 text-xs leading-relaxed">
        {rdf}
      </pre>
      <Button
        variant="outline"
        size="sm"
        className="absolute top-2 right-2"
        onClick={copy}
      >
        {copied ? <Check /> : <Copy />}
        {copied ? "Copied" : "Copy"}
      </Button>
    </div>
  )
}
