import React, { useState, useEffect, createContext, useContext } from "react";
import { person } from "@jsonforms/examples";
import {
  materialRenderers,
  materialCells,
} from "@jsonforms/material-renderers";
import { JsonForms } from "@jsonforms/react";
import { UISchemaElement } from "@jsonforms/core";

const initialData = {};

const ThemeContext = createContext(null);

interface FormJSXProps {
  node: string;
  schema: object;
  uischema: UISchemaElement;
}

interface FormElement {
  node: string;
  element_type: string;
  target_classes: string;
}

interface Props {
  form: FormJSXProps;
}

const getDefaultLayout = (
  layout_type: string,
  data: unknown
): React.JSX.Element => {
  return (
    <div>
      <h1>Default Layout</h1>
    </div>
  );
};

const handleSubmit = (e: string) => {
  console.log(e);
};

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const theme = useContext(ThemeContext);
  const className = "panel-" + theme;
  return (
    <section className={className}>
      <h1>{title}</h1>
      {children}
    </section>
  );
}

const FormComponent: React.FC<Props> = (props: Props) => {
  //const node = props.form.node;
  const schema1 = props.form.schema;
  const schema = {
    "properties": {
      "kame": {
        "type": "string",
        "position":1
      }
    }
  };

  console.log("The schema is", schema1);
  const uischema1 = props.form.uischema;
  const uischema = {
    "type": "VerticalLayout",
    "elements": [
        {
        "type": "Control",
        "scope": "#/properties/kame"
    }]
  };
  //console.log("The uischema generaten from the server", uischema);
  console.log("The uischema dynamic", uischema1);

  const [data, setData] = useState(initialData);

  // useEffect(() => {
  //     console.log("Printed from useEffect", formName);
  // }, []);

  return (
    //     <Panel title={""}>
    //     <div>
    //             <h1>{formName}</h1>
    //             <label>Name</label>
    //             <InputField input="" value = "", onChange = setField ()/>
    //          <button type="submit" onClick={() => handleSubmit(field1)}>Submit</button>
    //     </div>
    //    </Panel>
    <JsonForms
      schema={schema}
      uischema={uischema}
      data={data}
      renderers={materialRenderers}
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
