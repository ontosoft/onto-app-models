import {
  type ControlProps,
  isBooleanControl,
  isEnumControl,
  isIntegerControl,
  isNumberControl,
  isStringControl,
  type RankedTester,
  rankWith,
} from "@jsonforms/core"
import { withJsonFormsControlProps } from "@jsonforms/react"

import { Checkbox } from "~/components/ui/checkbox"
import { Input } from "~/components/ui/input"
import { Label } from "~/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "~/components/ui/select"

/** Shared wrapper: label + control + validation errors. */
function Field({
  id,
  label,
  required,
  errors,
  children,
}: {
  id: string
  label: string
  required?: boolean
  errors?: string
  children: React.ReactNode
}) {
  return (
    <div className="grid gap-1.5 py-2">
      {label ? (
        <Label htmlFor={id}>
          {label}
          {required ? <span className="text-destructive"> *</span> : null}
        </Label>
      ) : null}
      {children}
      {errors ? <p className="text-sm text-destructive">{errors}</p> : null}
    </div>
  )
}

function labelOf(props: ControlProps): string {
  if (typeof props.label === "string") return props.label
  return props.path
}

// ---- string ----------------------------------------------------------------

const TextControlBase = (props: ControlProps) => {
  const { id, path, data, label, required, errors, enabled, handleChange } =
    props
  return (
    <Field
      id={id}
      label={labelOf({ ...props, label } as ControlProps)}
      required={required}
      errors={errors}
    >
      <Input
        id={id}
        value={(data as string) ?? ""}
        disabled={enabled === false}
        onChange={(e) => handleChange(path, e.target.value)}
      />
    </Field>
  )
}
export const TextControl = withJsonFormsControlProps(TextControlBase)
export const textControlTester: RankedTester = rankWith(2, isStringControl)

// ---- number / integer ------------------------------------------------------

const NumberControlBase = (props: ControlProps) => {
  const { id, path, data, required, errors, enabled, handleChange } = props
  return (
    <Field id={id} label={labelOf(props)} required={required} errors={errors}>
      <Input
        id={id}
        type="number"
        value={data ?? ""}
        disabled={enabled === false}
        onChange={(e) => {
          const v = e.target.value
          handleChange(path, v === "" ? undefined : Number(v))
        }}
      />
    </Field>
  )
}
export const NumberControl = withJsonFormsControlProps(NumberControlBase)
export const numberControlTester: RankedTester = rankWith(
  2,
  (uischema, schema, ctx) =>
    isNumberControl(uischema, schema, ctx) ||
    isIntegerControl(uischema, schema, ctx),
)

// ---- boolean ---------------------------------------------------------------

const BooleanControlBase = (props: ControlProps) => {
  const { id, path, data, required, errors, enabled, handleChange } = props
  return (
    <div className="flex items-center gap-2 py-2">
      <Checkbox
        id={id}
        checked={Boolean(data)}
        disabled={enabled === false}
        onCheckedChange={(checked) => handleChange(path, Boolean(checked))}
      />
      <Label htmlFor={id}>
        {labelOf(props)}
        {required ? <span className="text-destructive"> *</span> : null}
      </Label>
      {errors ? <p className="text-sm text-destructive">{errors}</p> : null}
    </div>
  )
}
export const BooleanControl = withJsonFormsControlProps(BooleanControlBase)
export const booleanControlTester: RankedTester = rankWith(3, isBooleanControl)

// ---- enum (select) ---------------------------------------------------------

const EnumControlBase = (props: ControlProps) => {
  const { id, path, data, required, errors, enabled, handleChange, schema } =
    props
  const options = (schema?.enum ?? []) as unknown[]
  return (
    <Field id={id} label={labelOf(props)} required={required} errors={errors}>
      <Select
        value={data != null ? String(data) : undefined}
        disabled={enabled === false}
        onValueChange={(v) => handleChange(path, v)}
      >
        <SelectTrigger id={id}>
          <SelectValue placeholder="Select…" />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={String(opt)} value={String(opt)}>
              {String(opt)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </Field>
  )
}
export const EnumControl = withJsonFormsControlProps(EnumControlBase)
export const enumControlTester: RankedTester = rankWith(3, isEnumControl)
