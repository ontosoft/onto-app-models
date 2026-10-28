import type { ColumnDef } from "@tanstack/react-table"
import { ChevronDown, ChevronRight } from "lucide-react"
import type { ShapesDocumentPublic } from "~/client"
import { Badge } from "~/components/ui/badge"
import { Button } from "~/components/ui/button"
import DeleteShapesDocument from "./DeleteShapesDocument"
import GenerateAppModel from "./GenerateAppModel"

interface BuildColumnsOptions {
  // Called with the shapes document id after a successful Generate, so the
  // page can expand that row and show the new candidate in place.
  onGenerated: (id: string) => void
}

export function buildColumns({
  onGenerated,
}: BuildColumnsOptions): ColumnDef<ShapesDocumentPublic>[] {
  return [
    {
      id: "expander",
      header: () => <span className="sr-only">Generated models</span>,
      cell: ({ row }) => (
        <Button
          variant="ghost"
          size="icon"
          className="size-6"
          onClick={row.getToggleExpandedHandler()}
        >
          {row.getIsExpanded() ? (
            <ChevronDown className="size-4" />
          ) : (
            <ChevronRight className="size-4" />
          )}
          <span className="sr-only">Toggle generated models</span>
        </Button>
      ),
    },
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <span className="font-medium">{row.original.name}</span>
      ),
    },
    {
      accessorKey: "format",
      header: "Format",
      cell: ({ row }) => (
        <Badge variant="secondary">{row.original.format}</Badge>
      ),
    },
    {
      accessorKey: "is_public",
      header: "Visibility",
      cell: ({ row }) =>
        row.original.is_public ? (
          <Badge variant="secondary">public</Badge>
        ) : (
          <span className="text-muted-foreground text-xs">private</span>
        ),
    },
    {
      accessorKey: "created_at",
      header: "Uploaded",
      cell: ({ row }) => {
        const created = row.original.created_at
        return (
          <span className="text-muted-foreground">
            {created ? new Date(created).toLocaleString() : ""}
          </span>
        )
      },
    },
    {
      id: "actions",
      header: () => <span className="sr-only">Actions</span>,
      cell: ({ row }) => (
        <div className="flex justify-end gap-2">
          <GenerateAppModel
            id={row.original.id}
            onSuccess={() => onGenerated(row.original.id)}
          />
          <DeleteShapesDocument id={row.original.id} />
        </div>
      ),
    },
  ]
}
