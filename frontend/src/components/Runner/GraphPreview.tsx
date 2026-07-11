import cytoscape, { type Core, type ElementDefinition } from "cytoscape"
import { Parser as N3Parser, type Quad } from "n3"
import { useEffect, useMemo, useRef, useState } from "react"

/** Short, human-readable label for an IRI: the fragment or last path segment. */
function localName(iri: string): string {
  const hash = iri.lastIndexOf("#")
  if (hash >= 0 && hash < iri.length - 1) return iri.slice(hash + 1)
  const slash = iri.lastIndexOf("/")
  if (slash >= 0 && slash < iri.length - 1) return iri.slice(slash + 1)
  return iri
}

function truncate(s: string, n = 40): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s
}

/** Parse a Turtle string into Cytoscape nodes + edges.
 *
 * IRIs and blank nodes become shared nodes keyed by value (so the graph
 * structure connects up); literals become a fresh node per occurrence (two
 * fields that both hold "" should not collapse into one node). Predicates are
 * directed, labelled edges. Returns [] on a parse error or empty input. */
function turtleToElements(turtle: string): ElementDefinition[] {
  if (!turtle.trim()) return []
  let quads: Quad[]
  try {
    quads = new N3Parser().parse(turtle)
  } catch {
    return []
  }

  const nodes = new Map<string, ElementDefinition>()
  const edges: ElementDefinition[] = []
  let litSeq = 0

  const ensureResource = (value: string, kind: "iri" | "blank") => {
    if (!nodes.has(value)) {
      nodes.set(value, {
        data: {
          id: value,
          label: kind === "blank" ? "( )" : truncate(localName(value)),
          full: value,
          kind,
        },
      })
    }
    return value
  }

  for (const q of quads) {
    const s =
      q.subject.termType === "BlankNode"
        ? ensureResource(q.subject.value, "blank")
        : ensureResource(q.subject.value, "iri")

    let target: string
    if (q.object.termType === "Literal") {
      target = `lit:${litSeq++}`
      nodes.set(target, {
        data: {
          id: target,
          label: truncate(q.object.value) || '""',
          full: q.object.value,
          kind: "literal",
        },
      })
    } else if (q.object.termType === "BlankNode") {
      target = ensureResource(q.object.value, "blank")
    } else {
      target = ensureResource(q.object.value, "iri")
    }

    edges.push({
      data: {
        id: `e${edges.length}`,
        source: s,
        target,
        label: truncate(localName(q.predicate.value), 24),
      },
    })
  }

  return [...nodes.values(), ...edges]
}

/** Tracks the viewer's effective theme (matchMedia + the app's data-theme). */
function useIsDark(): boolean {
  const [dark, setDark] = useState(() => {
    if (typeof document === "undefined") return false
    const attr = document.documentElement.getAttribute("data-theme")
    if (attr) return attr === "dark"
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false
  })

  useEffect(() => {
    const read = () => {
      const attr = document.documentElement.getAttribute("data-theme")
      setDark(
        attr
          ? attr === "dark"
          : (window.matchMedia?.("(prefers-color-scheme: dark)").matches ??
              false),
      )
    }
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)")
    mq?.addEventListener?.("change", read)
    const obs = new MutationObserver(read)
    obs.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme", "class"],
    })
    return () => {
      mq?.removeEventListener?.("change", read)
      obs.disconnect()
    }
  }, [])

  return dark
}

function stylesheet(dark: boolean): cytoscape.StylesheetJson {
  const text = dark ? "#e5e7eb" : "#1f2937"
  const textBg = dark ? "#0b0f19" : "#ffffff"
  return [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "font-size": 10,
        color: text,
        "text-background-color": textBg,
        "text-background-opacity": 0.85,
        "text-background-shape": "roundrectangle",
        "text-background-padding": "2px",
        "text-valign": "center",
        "text-halign": "center",
        width: 16,
        height: 16,
        "border-width": 1.5,
      },
    },
    {
      // IRI resources
      selector: 'node[kind = "iri"]',
      style: { "background-color": "#3b82f6", "border-color": "#1d4ed8" },
    },
    {
      selector: 'node[kind = "blank"]',
      style: { "background-color": "#a78bfa", "border-color": "#7c3aed" },
    },
    {
      selector: 'node[kind = "literal"]',
      style: {
        "background-color": "#22c55e",
        "border-color": "#15803d",
        shape: "round-rectangle",
      },
    },
    {
      selector: "edge",
      style: {
        label: "data(label)",
        "font-size": 8,
        color: text,
        "text-background-color": textBg,
        "text-background-opacity": 0.8,
        "text-background-padding": "1px",
        width: 1,
        "line-color": dark ? "#4b5563" : "#9ca3af",
        "target-arrow-color": dark ? "#4b5563" : "#9ca3af",
        "target-arrow-shape": "triangle",
        "arrow-scale": 0.8,
        "curve-style": "bezier",
        "text-rotation": "autorotate",
      },
    },
  ]
}

/** Read-only node-link view of a Turtle knowledge graph. Pan/zoom + click a node
 * to see its full IRI/value. Re-lays out whenever the graph content changes. */
export function GraphPreview({
  turtle,
  className,
}: {
  turtle: string
  className?: string
}) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const cyRef = useRef<Core | null>(null)
  const dark = useIsDark()
  const [selected, setSelected] = useState<string | null>(null)

  const elements = useMemo(() => turtleToElements(turtle), [turtle])

  // Create the Cytoscape instance once (styling is applied by the theme effect
  // below, which also runs on mount — so this effect needs no reactive deps).
  useEffect(() => {
    if (!containerRef.current) return
    const cy = cytoscape({
      container: containerRef.current,
      elements: [],
      minZoom: 0.2,
      maxZoom: 3,
      wheelSensitivity: 0.2,
    })
    cy.on("tap", "node", (e) => setSelected(String(e.target.data("full"))))
    cy.on("tap", (e) => {
      if (e.target === cy) setSelected(null)
    })
    cyRef.current = cy
    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [])

  // Apply styling on mount and whenever the theme changes.
  useEffect(() => {
    cyRef.current?.style(stylesheet(dark))
  }, [dark])

  // Swap in new elements and re-layout when the graph content changes.
  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    cy.batch(() => {
      cy.elements().remove()
      cy.add(elements)
    })
    if (elements.length > 0) {
      cy.layout({
        name: "cose",
        animate: false,
        padding: 20,
        nodeRepulsion: () => 8000,
      } as cytoscape.LayoutOptions).run()
      cy.fit(undefined, 24)
    }
  }, [elements])

  const isEmpty = elements.length === 0

  return (
    <div className={className}>
      <div
        ref={containerRef}
        className="h-full w-full"
        style={{ minHeight: 240 }}
      />
      {isEmpty ? (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
          No graph data yet — submit a step to see it grow.
        </div>
      ) : null}
      {selected ? (
        <div className="absolute inset-x-2 bottom-2 truncate rounded border bg-background/95 px-2 py-1 text-xs text-muted-foreground shadow">
          {selected}
        </div>
      ) : null}
    </div>
  )
}
