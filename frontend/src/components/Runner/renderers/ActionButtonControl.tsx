import {
  type JsonFormsProps,
  type RankedTester,
  rankWith,
  type UISchemaElement,
  uiTypeIs,
} from "@jsonforms/core"
import { withJsonFormsRendererProps } from "@jsonforms/react"
import { useRunnerActions } from "~/components/Runner/ActionContext"
import { Button } from "~/components/ui/button"
import type { UiAction } from "~/lib/ontoRunnerApi"

/** The backend emits buttons as uischema elements of type "button". */
type ButtonElement = UISchemaElement & {
  label?: string
  actions?: UiAction[]
  options?: { variant?: string }
}

// Typed against JsonFormsProps — the exact shape withJsonFormsRendererProps
// injects — so `uischema` is optional here and we guard it.
const ActionButtonBase = ({ uischema }: JsonFormsProps) => {
  const element = uischema as ButtonElement | undefined
  const actions = element?.actions ?? []
  const { triggerAction, busy } = useRunnerActions()

  const fire = (initiator: string) => {
    const action = actions.find((a) => a.initiators?.includes(initiator))
    if (action) {
      triggerAction(action)
    } else {
      console.error("No action found for initiator", initiator, uischema)
    }
  }

  // A submit-type action gets the primary look; everything else is secondary.
  const isSubmit = actions.some((a) => a.type === "submit")

  return (
    <Button
      type="button"
      variant={isSubmit ? "default" : "outline"}
      disabled={busy}
      className="my-2"
      onClick={() => fire("onClick")}
    >
      {element?.label ?? "Action"}
    </Button>
  )
}

export const ActionButtonControl = withJsonFormsRendererProps(ActionButtonBase)
export const actionButtonTester: RankedTester = rankWith(5, uiTypeIs("button"))
