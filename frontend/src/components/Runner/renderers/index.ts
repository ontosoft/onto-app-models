import type { JsonFormsRendererRegistryEntry } from "@jsonforms/core"

import { ActionButtonControl, actionButtonTester } from "./ActionButtonControl"
import {
  BooleanControl,
  booleanControlTester,
  EnumControl,
  enumControlTester,
  NumberControl,
  numberControlTester,
  TextControl,
  textControlTester,
} from "./controls"
import { LabelRenderer, labelTester } from "./label"
import {
  GroupRenderer,
  groupTester,
  HorizontalLayoutRenderer,
  horizontalLayoutTester,
  VerticalLayoutRenderer,
  verticalLayoutTester,
} from "./layouts"

/**
 * Shadcn-styled JsonForms renderer set. The JsonForms engine handles schema
 * interpretation, scoping, validation and rules; these renderers only paint the
 * leaves and layouts in the app's own design system (no MUI).
 */
export const shadcnRenderers: JsonFormsRendererRegistryEntry[] = [
  // layouts
  { tester: verticalLayoutTester, renderer: VerticalLayoutRenderer },
  { tester: horizontalLayoutTester, renderer: HorizontalLayoutRenderer },
  { tester: groupTester, renderer: GroupRenderer },
  // controls
  { tester: textControlTester, renderer: TextControl },
  { tester: numberControlTester, renderer: NumberControl },
  { tester: booleanControlTester, renderer: BooleanControl },
  { tester: enumControlTester, renderer: EnumControl },
  // notification text
  { tester: labelTester, renderer: LabelRenderer },
  // actions
  { tester: actionButtonTester, renderer: ActionButtonControl },
]
