import React, { useState } from "react";
import { isSubmitButton } from "./ratingActionControlTester";
import {
  materialRenderers,
  materialCells,
} from "@jsonforms/material-renderers";
import { CustomButtonRenderer } from "./CustomButtonRenderer";
import { JsonForms } from "@jsonforms/react";
import { UISchemaElement } from "@jsonforms/core";
import isAction from "@jsonforms/core";
import { initiatePreviewModelList } from "../data/serverModelSlice";

interface FormJSXProps {
  node: string;
  schema: object;
  uischema: UISchemaElement;
  data: object;
}

interface Props {
  form: FormJSXProps;
}

const getDefaultLayout = (
  layout_type: string,
  message_content: any
): React.ReactElement => {
  return (
    <div>
      <h1>Default Layout</h1>
    </div>
  );
};

const renderers = [
  ...materialRenderers,
  {
    tester: isSubmitButton,
    renderer: CustomButtonRenderer,
  },
];

const FormComponent: React.FC<Props> = (props: Props) => {
  //const node = props.form.node;
  const schema = props.form.schema;
  const initialData = props.form.data;
  const [data, setData] = useState(initialData);

  const schema1 = {
    properties: {
      name: {
        type: "string",
        position: 1,
      },
    },
  };

  console.log("The schema is", schema);
  const uischema = props.form.uischema;
  console.log(uischema);

  const uischema1 = {
    type: "VerticalLayout",
    elements: [
      {
        type: "Control",
        scope: "#/properties/name",
        label: "Name",
      },
      {
        type: "HorizontalLayout",
        elements: [
          {
            type: "button",
            label: "Submit",
            onClick: "submit",
          },
          {
            type: "button",
            label: "Cancel",
            onClick: "cancel",
          },
        ],
      },
    ],
  };

  console.log("The uischema dynamic", uischema);

  // useEffect(() => {
  //     console.log("Printed from useEffect", formName);
  // }, []);

  return (
    <JsonForms
      schema={schema1}
      uischema={uischema1}
      data={data}
      renderers={renderers}
      cells={materialCells}
      onChange={({ data, errors }) => setData(data)}
    />
  );
};

const InputField = ({
  input,
  value,
  onChange,
}: {
  input: string;
  value: string;
  onChange: (e: string) => void;
}): JSX.Element => {
  return (
    <input
      type="text"
      id={input}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
};

const LabelJSX = ({
  label,
  input,
}: {
  label: string;
  input: string;
}): JSX.Element => {
  return <label htmlFor="field1"> {label} </label>;
};

const ImageJSX = ({
  src,
  url,
  alt,
  caption,
}: {
  src: string;
  url: string;
  alt: string;
  caption: string;
}): JSX.Element => {
  return <a href={url}>caption={caption}</a>;
};

export default FormComponent;
export { getDefaultLayout, LabelJSX, ImageJSX };
export type { FormJSXProps };
