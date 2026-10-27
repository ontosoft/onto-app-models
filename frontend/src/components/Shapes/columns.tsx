import type { ColumnDef } from "@tanstack/react-table"
import type { ShapesDocumentPublic } from "~/client"
import { Badge } from "~/components/ui/badge"
import DeleteShapesDocument from "./DeleteShapesDocument"

export const columns: ColumnDef<ShapesDocumentPublic>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
  },
  {
    accessorKey: "format",
    header: "Format",
    cell: ({ row }) => <Badge variant="secondary">{row.original.format}</Badge>,
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
      <div className="flex justify-end">
        <DeleteShapesDocument id={row.original.id} />
      </div>
    ),
  },
]
