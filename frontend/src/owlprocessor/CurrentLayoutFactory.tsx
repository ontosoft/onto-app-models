import React, { useState } from "react";
import { isSubmitButton } from "./ratingActionControlTester";
import {
  materialRenderers,
  materialCells,
} from "@jsonforms/material-renderers";
import  CustomButtonRenderer  from "./CustomButtonRenderer";
import { JsonForms } from "@jsonforms/react";
import { UISchemaElement } from "@jsonforms/core";
import { updateCurrentJSONFormData } from "../data/modelSlice";
import { useAppDispatch } from "../app/hooks";

interface FormJSXProps {
  graph_node: string;
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
  const schema = props.form.schema;
  const initialData = props.form.data;
  const [data, setData] = useState(initialData);
  const dispatch = useAppDispatch();
  
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

  // const uischema1 = {
  //   type: "VerticalLayout",
  //   elements: [
  //     {
  //       type: "Control",
  //       scope: "#/properties/name",
  //       label: "Name",
  //     },
  //     {
  //       type: "HorizontalLayout",
  //       elements: [
  //         {
  //           type: "button",
  //           label: "Submit",
  //           onClick: "submit",
  //         },
  //         {
  //           type: "button",
  //           label: "Cancel",
  //           onClick: "cancel",
  //         },
  //       ],
  //     },
  //   ],
  // };

  console.log("The uischema dynamic", uischema);

  // useEffect(() => {
  //     console.log("Printed from useEffect", formName);
  // }, []);

  return (
    <JsonForms
      schema={schema}
      uischema={uischema}
      data={data}
      renderers={renderers}
      cells={materialCells}
      config = {{form_graph_node: props.form.graph_node}} 
      onChange={({ data, errors }) => {
        setData(data);
        dispatch(updateCurrentJSONFormData(data));
      }}
    />
  );
};



export default FormComponent;
export { getDefaultLayout};
export type { FormJSXProps };
