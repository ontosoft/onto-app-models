import { useQuery } from "@tanstack/react-query"

import { ShapesService } from "~/client"
import { AppModelActionsMenu } from "~/components/AppModels/AppModelActionsMenu"
import { Badge } from "~/components/ui/badge"

interface ShapesCandidatesProps {
  id: string
}

/**
 * The FAM candidates generated from one shapes document, shown inline under
 * its expanded row in the Shapes table. The query is lazy by construction:
 * this component only mounts while the row is open.
 */
const ShapesCandidates = ({ id }: ShapesCandidatesProps) => {
  const { data, isPending, isError } = useQuery({
    queryKey: ["shapes", id, "appmodels"],
    queryFn: () => ShapesService.readShapesDocumentAppmodels({ id }),
  })

  if (isPending) {
    return (
      <p className="px-12 py-3 text-sm text-muted-foreground">
        Loading generated models...
      </p>
    )
  }
  if (isError) {
    return (
      <p className="px-12 py-3 text-sm text-destructive">
        Could not load the generated models.
      </p>
    )
  }
  if (data.data.length === 0) {
    return (
      <p className="px-12 py-3 text-sm text-muted-foreground">
        No models generated from this document yet.
      </p>
    )
  }

  return (
    <div className="px-12 py-2">
      <p className="mb-1 text-xs font-medium text-muted-foreground">
        Generated models ({data.count})
      </p>
      <ul className="divide-y">
        {data.data.map((model) => (
          <li key={model.id} className="flex items-center gap-3 py-1">
            <span className="flex-1 truncate text-sm font-medium">
              {model.title}
            </span>
            {model.generation_method ? (
              <Badge variant="outline">{model.generation_method}</Badge>
            ) : (
              <span className="text-muted-foreground text-xs">manual</span>
            )}
            {model.is_public ? (
              <Badge variant="secondary">public</Badge>
            ) : (
              <span className="text-muted-foreground text-xs">private</span>
            )}
            <span className="text-muted-foreground text-xs">
              {model.created_at
                ? new Date(model.created_at).toLocaleString()
                : ""}
            </span>
            <AppModelActionsMenu appmodel={model} />
          </li>
        ))}
      </ul>
    </div>
  )
}

export default ShapesCandidates
