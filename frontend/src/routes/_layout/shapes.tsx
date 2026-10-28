import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import type { ExpandedState } from "@tanstack/react-table"
import { Search } from "lucide-react"
import { Suspense, useMemo, useState } from "react"

import { ShapesService } from "~/client"
import { DataTable } from "~/components/Common/DataTable"
import PendingAppModels from "~/components/Pending/PendingAppModels"
import AddShapesDocument from "~/components/Shapes/AddShapesDocument"
import { buildColumns } from "~/components/Shapes/columns"
import ShapesCandidates from "~/components/Shapes/ShapesCandidates"

function getShapesQueryOptions() {
  return {
    queryKey: ["shapes"],
    queryFn: () => ShapesService.readShapesDocuments({ skip: 0, limit: 100 }),
  }
}

export const Route = createFileRoute("/_layout/shapes")({
  component: ShapesPage,
  head: () => ({
    meta: [
      {
        title: "Shapes - OntoUI",
      },
    ],
  }),
})

function ShapesTableContent() {
  const { data: shapes } = useSuspenseQuery(getShapesQueryOptions())
  // Expanded rows, keyed by shapes document id (getRowId below). Kept here so
  // a successful Generate can open its row and show the new candidate.
  const [expanded, setExpanded] = useState<ExpandedState>({})
  const columns = useMemo(
    () =>
      buildColumns({
        onGenerated: (id) =>
          setExpanded((prev) =>
            prev === true ? prev : { ...prev, [id]: true },
          ),
      }),
    [],
  )
  if (shapes.data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">
          You don't have any shapes documents yet
        </h3>
        <p className="text-muted-foreground">
          Upload SHACL shapes to generate application models from them
        </p>
      </div>
    )
  }
  return (
    <DataTable
      columns={columns}
      data={shapes.data}
      getRowId={(shapesDocument) => shapesDocument.id}
      expanded={expanded}
      onExpandedChange={setExpanded}
      renderSubRow={(shapesDocument) => (
        <ShapesCandidates id={shapesDocument.id} />
      )}
    />
  )
}

function ShapesTable() {
  return (
    <Suspense fallback={<PendingAppModels />}>
      <ShapesTableContent />
    </Suspense>
  )
}

function ShapesPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Shapes</h1>
          <p className="text-muted-foreground">
            Upload shapes documents (SHACL for now) and generate application
            model candidates from them; expand a row to see its candidates.
          </p>
        </div>
        <AddShapesDocument />
      </div>
      <ShapesTable />
    </div>
  )
}
