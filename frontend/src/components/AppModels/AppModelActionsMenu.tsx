import { EllipsisVertical } from "lucide-react"
import { useState } from "react"

import type { AppModelPublic } from "~/client"
import { Button } from "~/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "~/components/ui/dropdown-menu";
import DeleteAppModel from "./DeleteAppModel";
import EditAppModel from "./EditAppModel"

interface AppModelActionsMenuProps {
  appmodel: AppModelPublic
}

export const AppModelActionsMenu = ({ appmodel }: AppModelActionsMenuProps) => {
  const [open, setOpen] = useState(false)

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <EllipsisVertical />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <EditAppModel appmodel={appmodel} onSuccess={() => setOpen(false)} />
        <DeleteAppModel id={appmodel.id} onSuccess={() => setOpen(false)} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
