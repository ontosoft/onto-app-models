import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"

import { AppmodelsService } from "~/client"
import { BpmnDiagram, RdfView } from "~/components/AppModels/ModelViews"
import { Badge } from "~/components/ui/badge"
import { Button } from "~/components/ui/button"
import { Skeleton } from "~/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "~/components/ui/tabs"

// The trailing underscore in the file name (appmodels_.$id) keeps this route
// OUT of the appmodels table route, so /appmodels/$id is a sibling page with
// its own URL (deep-linkable) instead of a child rendered inside the table.
export const Route = createFileRoute("/_layout/appmodels_/$id")({
  component: AppModelDetail,
  head: () => ({
    meta: [
      {
        title: "Application Model - FastAPI Cloud",
      },
    ],
  }),
})

function AppModelDetail() {
  const { id } = Route.useParams()
  const {
    data: appmodel,
    isPending,
    error,
  } = useQuery({
    queryKey: ["appmodels", id],
    queryFn: async () =>
      (await AppmodelsService.readAppModel({ path: { id } })).data,
  })

  if (isPending) {
    return (
      <div className="flex flex-col gap-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[60vh] w-full" />
      </div>
    )
  }
  if (error || !appmodel) {
    return (
      <div className="flex flex-col items-start gap-4">
        <p className="text-sm text-destructive">
          Could not load this application model:{" "}
          {error instanceof Error ? error.message : "not found"}
        </p>
        <Button variant="outline" asChild>
          <Link to="/appmodels">
            <ArrowLeft />
            Back to Application Models
          </Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div>
        <Button variant="ghost" size="sm" asChild className="-ml-2 mb-2">
          <Link to="/appmodels">
            <ArrowLeft />
            Application Models
          </Link>
        </Button>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight">
            {appmodel.title}
          </h1>
          <Badge variant="outline">
            {appmodel.generation_method ?? "manual"}
          </Badge>
          {appmodel.is_public && <Badge variant="secondary">public</Badge>}
        </div>
        {appmodel.description && (
          <p className="text-muted-foreground">{appmodel.description}</p>
        )}
      </div>
      <Tabs defaultValue="bpmn" className="flex min-h-0 flex-1 flex-col">
        <TabsList className="self-start">
          <TabsTrigger value="bpmn">BPMN Diagram</TabsTrigger>
          <TabsTrigger value="rdf">RDF</TabsTrigger>
        </TabsList>
        {/* a fixed viewport share keeps the diagram tall even though the
            layout's content area grows with its content */}
        <TabsContent value="bpmn" className="h-[70vh]">
          <BpmnDiagram id={appmodel.id} title={appmodel.title} />
        </TabsContent>
        <TabsContent value="rdf" className="h-[70vh]">
          <RdfView
            rdf={
              appmodel.knowledge_graph_rdf ?? "This model has no RDF content."
            }
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
