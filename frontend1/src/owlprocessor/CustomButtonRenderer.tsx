import React from "react";
import { useAppSelector, useAppDispatch } from "../app/hooks";
import { triggerAction } from "../data/modelSlice";
import {Action} from "../owlprocessor/Action";
import { withJsonFormsControlProps } from "@jsonforms/react";

interface CustomButtonRendererProps {
  uischema: any;
  config?: any;
}

const CustomButtonRenderer: React.FC<CustomButtonRendererProps> = ({
  uischema,
  config,
}) => {
  const dispatch = useAppDispatch();
  const appRunningOnServer = useAppSelector(
    (state) => state.stateData.runningOnServer
  );
  console.log("CustomButtonRenderer has schema",uischema);
  console.log("CustomButtonRenderer has a configuration",config);
  const handleFunction = ( initiator : string) => {
    if (appRunningOnServer) {
      console.log("The app is running on the server");
      console.log("It is executed a function ", initiator," on the button" , uischema.label); 
      const action : Action = uischema.actions.find((a:Action) => a.initiators.includes(initiator));
      /* It has be found an action that contains in the list of action initiators 
      the initiator that corresponds to the event attribtute of the HTML button
      In the case of buttons it is mostly "onClick" for the "onclick" event, but for   
      it is possible to usse other characteristic attributes of an HTML `<button>` element 
      such as `onmousedown`, `onmouseup`, `onkeydown`, `onkeyup`, `onchange`,
 .    `onmouseover`, `onfocus`, `onblur`, etc.*/
      if (action) {
        dispatch(triggerAction({ action: action, form_graph_node: config.form_graph_node }));
      } else {
        console.error("No action found for the given initiator", initiator);
      }
      
    }
  };

  return (
    <button onClick={() => handleFunction("onClick")} style={{ margin: "8px 0" }}>
      {uischema.label}
    </button>
  );
};

export default withJsonFormsControlProps(CustomButtonRenderer);