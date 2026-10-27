import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { Suspense } from "react"

import { ShapesService } from "~/client"
import { DataTable } from "~/components/Common/DataTable"
import PendingAppModels from "~/components/Pending/PendingAppModels"
import AddShapesDocument from "~/components/Shapes/AddShapesDocument"
import { columns } from "~/components/Shapes/columns"

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
  return <DataTable columns={columns} data={shapes.data} />
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
            Upload shapes documents (SHACL for now) and manage them; model
            generation from shapes follows here.
          </p>
        </div>
        <AddShapesDocument />
      </div>
      <ShapesTable />
    </div>
  )
}
