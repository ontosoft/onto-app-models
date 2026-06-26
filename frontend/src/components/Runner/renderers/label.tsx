import {
  type JsonFormsProps,
  type RankedTester,
  rankWith,
  type UISchemaElement,
  uiTypeIs,
} from "@jsonforms/core"
import { withJsonFormsRendererProps } from "@jsonforms/react"

/**
 * The backend emits notification text as a uischema element of type "Label"
 * with a `text` field (see owlprocessor/form_elements.py OBOP.Label). Without a
 * renderer for it, JsonForms shows "No applicable renderer found", which blocks
 * every notification screen.
 */
type LabelElement = UISchemaElement & { text?: string }

const LabelBase = ({ uischema }: JsonFormsProps) => {
  const text = (uischema as LabelElement | undefined)?.text ?? ""
  if (!text) return null
  return <p className="my-2 text-sm text-foreground">{text}</p>
}

export const LabelRenderer = withJsonFormsRendererProps(LabelBase)
export const labelTester: RankedTester = rankWith(5, uiTypeIs("Label"))
