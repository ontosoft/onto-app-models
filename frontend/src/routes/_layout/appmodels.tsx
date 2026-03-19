import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Search } from "lucide-react"
import { Suspense } from "react"

import { AppmodelsService } from "~/client"
import AddAppModel from "~/components/AppModels/AddAppModel"
import { columns } from "~/components/AppModels/columns"
import { DataTable } from "~/components/Common/DataTable"
import PendingAppModels from "~/components/Pending/PendingAppModels"

function getAppModelsQueryOptions() {
  return {
    queryKey: ["appmodels"],
    queryFn: () => AppmodelsService.readAppModels({ skip: 0, limit: 100 }),
  }
}

export const Route = createFileRoute("/_layout/appmodels")({
  component: AppModels,
  head: () => ({
    meta: [
      {
        title: "Application Models - FastAPI Cloud",
      },
    ],
  }),
})

function AppModelsTableContent() {
  const { data: appmodels } = useSuspenseQuery(getAppModelsQueryOptions())
  if (appmodels.data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12">
        No app models found.
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold">
          You don't have any application models yet
        </h3>
        <p className="text-muted-foreground">
          Add a new application model to get started
        </p>
      </div>
    )
  }
  return <DataTable columns={columns} data={appmodels.data} />
}

function AppModelsTable() {
  return (
    <Suspense fallback={<PendingAppModels />}>
      <AppModelsTableContent />
    </Suspense>
  )
}

function AppModels() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Application Models
          </h1>
          <p className="text-muted-foreground">
            Create and manage your application models
          </p>
        </div>
        <AddAppModel />
      </div>
      <AppModelsTable />
    </div>
  )
}
