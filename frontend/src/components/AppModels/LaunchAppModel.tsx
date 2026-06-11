import { useNavigate } from "@tanstack/react-router"
import { Rocket } from "lucide-react"

import { DropdownMenuItem } from "~/components/ui/dropdown-menu"

interface LaunchAppModelProps {
  id: string
  title?: string
  onSuccess?: () => void
}

/**
 * Opens the interactive runtime screen for this app model. The actual run +
 * data-exchange loop is orchestrated by the /run route (AppRunner), so this
 * just navigates there with the model id.
 */
const LaunchAppModel = ({ id, title, onSuccess }: LaunchAppModelProps) => {
  const navigate = useNavigate()

  return (
    <DropdownMenuItem
      onClick={() => {
        onSuccess?.()
        navigate({ to: "/run", search: { id, title } })
      }}
    >
      <Rocket />
      Launch (interactive)
    </DropdownMenuItem>
  )
}

export default LaunchAppModel
