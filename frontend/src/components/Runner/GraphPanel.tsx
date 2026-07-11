import { Copy, Download, Maximize2, Network } from "lucide-react"
import { useCallback } from "react"

import { GraphPreview } from "~/components/Runner/GraphPreview"
import { Button } from "~/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "~/components/ui/sheet"
import useCustomToast from "~/hooks/useCustomToast"

/** Live, read-only preview of the running app's output knowledge graph.
 *
 * The engine sends the cumulative graph (Turtle) on every response, so this
 * panel re-renders after every operation. Always visible below the form; the
 * expand button opens a large view. */
export function GraphPanel({ turtle }: { turtle: string }) {
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(turtle)
      showSuccessToast("Turtle copied to clipboard")
    } catch {
      showErrorToast("Could not copy to clipboard")
    }
  }, [turtle, showSuccessToast, showErrorToast])

  const download = useCallback(() => {
    const blob = new Blob([turtle], { type: "text/turtle" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "output-knowledge-graph.ttl"
    a.click()
    URL.revokeObjectURL(url)
  }, [turtle])

  const hasData = turtle.trim().length > 0

  return (
    <div className="mt-4 rounded-lg border">
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Network className="size-4 text-muted-foreground" />
          Knowledge graph
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={copy}
            disabled={!hasData}
            title="Copy Turtle"
          >
            <Copy className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={download}
            disabled={!hasData}
            title="Download .ttl"
          >
            <Download className="size-4" />
          </Button>
          <Sheet>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                disabled={!hasData}
                title="Expand"
              >
                <Maximize2 className="size-4" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-full sm:max-w-3xl">
              <SheetHeader>
                <SheetTitle>Output knowledge graph</SheetTitle>
              </SheetHeader>
              <div className="relative h-[calc(100%-4rem)] px-4 pb-4">
                <GraphPreview turtle={turtle} className="relative h-full" />
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
      <GraphPreview turtle={turtle} className="relative h-72" />
    </div>
  )
}
