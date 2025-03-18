import React, { ReactElement } from "react";
import { createElement, Fragment } from "react";
import AppExchangeResponse from "./AppExchangeResponse";
import { getDefaultLayout } from "./CurrentLayoutFactory";
import { FormJSXProps } from "./CurrentLayoutFactory";
import FormComponent from "./CurrentLayoutFactory";
import { Form } from "react-router-dom";

const getLayout: React.FC<AppExchangeResponse> = (
  serverExchangeResponse: AppExchangeResponse
) => {
  let layout: React.ReactNode = null;
  if (serverExchangeResponse.message_type === "layout") {
    layout = getDefaultLayout(
      serverExchangeResponse.layout_type as
        | "form"
        | "table"
        | "list"
        | "tree"
        | "chart",
      serverExchangeResponse.message_content
    );
  } else if (serverExchangeResponse.message_type === "form") {
      const formProps: FormJSXProps = 
        serverExchangeResponse.message_content;
        console.log("The form props are", formProps);
    layout = React.createElement(FormComponent, { form: formProps });
  } else {
    layout = React.createElement("div", null, "No layout available");
  }

  return layout;
};

const Layout: React.FC<AppExchangeResponse> = (
  serverExchangeResponse: AppExchangeResponse
) => {
  console.log("The server exchange response is", serverExchangeResponse);
  console.log("The message type is", serverExchangeResponse.message_type);

  return <div> {getLayout(serverExchangeResponse)} </div>;
};

export { Layout };
