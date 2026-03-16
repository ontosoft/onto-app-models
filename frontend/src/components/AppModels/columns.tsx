import { ColumnDef } from "@tanstack/react-table";
import { Check, Copy } from "lucide-react";
import { useCopyToClipboard } from "~/hooks/useCopyToClipboard";
import { Button } from "~/components/ui/button";
import { AppModelPublic } from "~/client";
import { cn } from "~/lib/utils";
import { AppModelActionsMenu } from "./AppModelActionsMenu";

function CopyId({ id }: { id: string }) {
  const [copiedText, copy] = useCopyToClipboard();
  const isCopied = copiedText === id;

  return (
    <div className="flex items-center gap-1.5 group">
      <span className="font-mono text-xs text-muted-foreground">{id}</span>
      <Button
        variant="ghost"
        size="icon"
        className="size-6 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={() => copy(id)}
      >
        {isCopied ? (
          <Check className="size-3 text-green-500" />
        ) : (
          <Copy className="size-3" />
        )}
        <span className="sr-only">Copy ID</span>
      </Button>
    </div>
  );
}

export const columns: ColumnDef<AppModelPublic>[] = [
  {
    accessorKey: "id",
    header: "ID",
    cell: ({ row }) => <CopyId id={row.original.id} />,
  },
  {
    accessorKey: "title",
    header: "Title",
    cell: ({ row }) => (
      <span
        className={cn(
          "font-medium",
          !row.original.title && "text-muted-foreground",
        )}
      >
        {row.original.title}{" "}
      </span>
    ),
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => {
      const description = row.original.description;
      return (
        <span
          className={cn(
            "max-w-xs truncate block text-muted-foreground",
            !description && "italic",
          )}
        >
          {description || "No description"}
        </span>
      );
    },
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
];
