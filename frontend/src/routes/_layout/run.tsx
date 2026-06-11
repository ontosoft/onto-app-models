import { createFileRoute } from "@tanstack/react-router"
import { z } from "zod"

import { AppRunner } from "~/components/Runner/AppRunner"

const searchSchema = z.object({
  id: z.string().catch(""),
  title: z.string().optional(),
})

export const Route = createFileRoute("/_layout/run")({
  component: RunPage,
  validateSearch: searchSchema,
  head: () => ({
    meta: [{ title: "Run Application - OntoUI" }],
  }),
})

function RunPage() {
  const { id, title } = Route.useSearch()

  if (!id) {
    return (
      <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4 text-destructive">
        No application model selected. Open one from the Application Models
        list.
      </div>
    )
  }

  return <AppRunner appModelId={id} appModelTitle={title} />
}
