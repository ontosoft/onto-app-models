import { useMutation } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { Play } from "lucide-react"
import { useState } from "react"

import { Button } from "~/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "~/components/ui/dialog"
import { DropdownMenuItem } from "~/components/ui/dropdown-menu"
import { LoadingButton } from "~/components/ui/loading-button"
import useCustomToast from "~/hooks/useCustomToast"
import { runAppModelById } from "~/lib/ontoRunnerApi"
import { handleError } from "~/utils"

interface RunAppModelProps {
  id: string
  onSuccess?: () => void
}

const RunAppModel = ({ id, onSuccess }: RunAppModelProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const navigate = useNavigate()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    // Fresh engine session per run (this action starts the app, then navigates
    // away; the runner route drives its own session).
    mutationFn: () => runAppModelById(id, crypto.randomUUID()),
    onSuccess: () => {
      showSuccessToast("Application started successfully")
      setIsOpen(false)
      onSuccess?.()
      navigate({ to: "/" })
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuItem
        onSelect={(e) => e.preventDefault()}
        onClick={() => setIsOpen(true)}
      >
        <Play />
        Run
      </DropdownMenuItem>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Run Application</DialogTitle>
          <DialogDescription>
            Are you sure you want to run this application model? This might stop
            any currently running application.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" disabled={mutation.isPending}>
              Cancel
            </Button>
          </DialogClose>
          <LoadingButton
            onClick={() => mutation.mutate()}
            loading={mutation.isPending}
          >
            Run
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default RunAppModel
