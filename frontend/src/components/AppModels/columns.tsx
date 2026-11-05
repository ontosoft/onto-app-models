import { Link } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import type { AppModelPublic } from "~/client"
import { Badge } from "~/components/ui/badge"
import { cn } from "~/lib/utils"
import { AppModelActionsMenu } from "./AppModelActionsMenu"

export const columns: ColumnDef<AppModelPublic>[] = [
  {
    accessorKey: "title",
    header: "Title",
    cell: ({ row }) => (
      <Link
        to="/appmodels/$id"
        params={{ id: row.original.id }}
        className={cn(
          "font-medium hover:underline",
          !row.original.title && "text-muted-foreground",
        )}
      >
        {row.original.title}
      </Link>
    ),
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => {
      const description = row.original.description
      return (
        <span
          className={cn(
            "max-w-xs truncate block text-muted-foreground",
            !description && "italic",
          )}
        >
          {description || "No description"}
        </span>
      )
    },
  },
  {
    accessorKey: "generation_method",
    header: "Origin",
    cell: ({ row }) =>
      row.original.generation_method ? (
        <Badge variant="outline">{row.original.generation_method}</Badge>
      ) : (
        <span className="text-muted-foreground text-xs">manual</span>
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
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <AppModelActionsMenu appmodel={row.original} />
      </div>
    ),
  },
]
