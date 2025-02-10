import React, { ReactElement } from "react";
import { createElement } from "react";
import  AppExchangeResponse  from "./AppExchangeResponse";
import { FormComponent, getDefaultLayout} from "./CurrentLayoutFactory";
import { Form } from "react-router-dom";
import {FormJSXProps} from "./CurrentLayoutFactory";

const Layout = (serverExchangeResponse: AppExchangeResponse): React.JSX.Element => { 
    let layout : ReactElement = React.createElement(React.Fragment);
    console.log("The server exchange response is", serverExchangeResponse);
    console.log("The message type is", serverExchangeResponse.message_type);
    if (serverExchangeResponse.message_type === 'layout') {
        layout = getDefaultLayout( 
            serverExchangeResponse.layout_type as "form" | "table" | "list" | "tree" | "chart",
            serverExchangeResponse.message_content);
    } else if (serverExchangeResponse.message_type === 'form') {
        const formProps:FormJSXProps = JSON.parse(serverExchangeResponse.message_content) as FormJSXProps;
        console.log("The form props are", formProps);
        layout = FormComponent(formProps); 
    }else { 
        layout = React.createElement('div', null, 'No layout available');
    }
    
    return layout;
}

export { Layout};