import React  from "react";
import { getDefaultLayout } from "./CurrentLayoutFactory";
import { FormJSXProps } from "./CurrentLayoutFactory";
import FormComponent from "./CurrentLayoutFactory";

interface LayoutProps {
  layout_type: string;
  message_content: any;
}

export const getLayout: React.FC<LayoutProps> = (layoutProps: LayoutProps) => {
  console.log("The layout type is:", layoutProps.layout_type);
  console.log("The server message content is", layoutProps.message_content);

  let layout: React.ReactNode = null;
  if (layoutProps.layout_type === "form") {
      const formProps: FormJSXProps = layoutProps.message_content;
      console.log("The form props are", formProps);
      layout = React.createElement(FormComponent, { form: formProps });
  } else if (layoutProps.layout_type === "message-box") {
      const formProps: FormJSXProps = layoutProps.message_content;
      console.log("The form props are", formProps);
      layout = React.createElement(FormComponent, { form: formProps });
  } else {
    layout = getDefaultLayout(
    layoutProps.layout_type as
        | "table"
        | "list"
        | "tree"
        | "chart",
      layoutProps.message_content
    );
  };

  return layout;
};

