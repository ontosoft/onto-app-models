import {
  type LayoutProps,
  type RankedTester,
  rankWith,
  type UISchemaElement,
  uiTypeIs,
} from "@jsonforms/core"
import { JsonFormsDispatch, withJsonFormsLayoutProps } from "@jsonforms/react"

type Layout = UISchemaElement & {
  elements?: UISchemaElement[]
  label?: string
}

/** Render the child elements of a layout through JsonForms' dispatcher. */
function renderChildren(props: LayoutProps) {
  const { schema, path, renderers, cells, enabled } = props
  const elements = (props.uischema as Layout).elements ?? []
  return elements.map((child, index) => (
    <JsonFormsDispatch
      key={`${child.type}-${index}`}
      uischema={child}
      schema={schema}
      path={path}
      enabled={enabled}
      renderers={renderers}
      cells={cells}
    />
  ))
}

const VerticalLayoutBase = (props: LayoutProps) => {
  if (props.visible === false) return null
  return <div className="flex flex-col">{renderChildren(props)}</div>
}
export const VerticalLayoutRenderer =
  withJsonFormsLayoutProps(VerticalLayoutBase)
export const verticalLayoutTester: RankedTester = rankWith(
  1,
  uiTypeIs("VerticalLayout"),
)

const HorizontalLayoutBase = (props: LayoutProps) => {
  if (props.visible === false) return null
  return (
    <div className="flex flex-row flex-wrap items-end gap-4">
      {renderChildren(props)}
    </div>
  )
}
export const HorizontalLayoutRenderer =
  withJsonFormsLayoutProps(HorizontalLayoutBase)
export const horizontalLayoutTester: RankedTester = rankWith(
  1,
  uiTypeIs("HorizontalLayout"),
)

const GroupLayoutBase = (props: LayoutProps) => {
  if (props.visible === false) return null
  const label = (props.uischema as Layout).label
  return (
    <fieldset className="rounded-lg border p-4">
      {label ? (
        <legend className="px-1 text-sm font-medium">{label}</legend>
      ) : null}
      <div className="flex flex-col">{renderChildren(props)}</div>
    </fieldset>
  )
}
export const GroupRenderer = withJsonFormsLayoutProps(GroupLayoutBase)
export const groupTester: RankedTester = rankWith(1, uiTypeIs("Group"))
