import { PayloadAction, createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { ActionProcessor } from "../owlprocessor/ActionProcessor";
import { TemplateFactory } from "../owlprocessor/TemplateFactory";
import { RunningInstance } from "../owlprocessor/RunningInstance";
import { Formula } from "rdflib";
import { CurrentForm } from "../owlprocessor/CurrentForm";
import { getLayout } from "../owlprocessor/LayoutRendering";
import AppExchangeResponse from "../owlprocessor/AppExchangeResponse";
import { RootState } from "../app/store";
import { Action } from "../owlprocessor/Action";
import { initiateAppExchange, appExchangeGet } from "./appStateSlice";
import React from "react";
// @ts-ignore: internal import for WritableDraft type
import type { WritableDraft } from "immer/dist/internal";
import { AppDispatch } from "../app/store";
import { avatarClasses } from "@mui/material";
import { Console } from "console";

type GeneralAction = PayloadAction<{}>;
type ResponseAction = PayloadAction<AppExchangeResponse>;
// type ConnectionAction = PayloadAction<{modelAcction, dataType}>;
const owlTemplate = new TemplateFactory();
const owlProcessor = new ActionProcessor();


export interface ModelState {
  /* This model class is deprecated. It is for keeping track of
     the application state when the application is completely
     running on the front end side.
  */

  idCounter: number;
  rdfGraph: any;
  currentForm: CurrentForm,
  currentJSONFormData: any,
  UIRunningInstance: RunningInstance,
  outputGraph: string,
  //status of the RDF reading
  asyncStatus: "loading" | "complete",
  currentLayout: React.ReactNode,
  layoutRefreshNecessary: boolean
}

const initialState: ModelState = {
  idCounter: 1,
  rdfGraph: {} as Formula,
  currentForm: new CurrentForm(),
  currentJSONFormData: {},
  UIRunningInstance: {} as RunningInstance,
  outputGraph: "",
  asyncStatus: 'complete',
  currentLayout: {} as React.ReactNode,
  layoutRefreshNecessary: false
};

const processResponse = (state: WritableDraft<ModelState>, serverExchangeResponse: AppExchangeResponse): React.ReactNode => {
  state.outputGraph = serverExchangeResponse.output_knowledge_graph;
  let layout: React.ReactNode = null;
  if (serverExchangeResponse.message_type === "layout") {
    return getLayout({
      layout_type: serverExchangeResponse.layout_type,
      message_content: serverExchangeResponse.message_content
    });
  } else if (serverExchangeResponse.message_type === "notification") {
    layout = React.createElement("div", null, serverExchangeResponse.message_content);
  } else {
    layout = React.createElement("div", null, "Error: Unknown message type from the server");
  }
  return layout;
}

/*
  * This function executes tha action on the server

  */
export const triggerAction = createAsyncThunk('model/triggerAction',
  async (params: { action: Action, form_graph_node: string}, thunkApi) => {
    let state: RootState = thunkApi.getState() as RootState;
    let messageType: string = "";
    let messageContent: any = {};
    console.log("The app state (read form inside the Thunk) is", state.stateData.runningOnServer);
    if (!state.stateData.runningOnServer) {
      return {
        status: "failed",
        message: "The app is still not running on the server."
      };
    }
    else {
      if (params.action.type === "submit") {
        messageType = "action";
        messageContent = {
          "action_type": "submit",          
          "action_graph_node": params.action.graph_node,
          "form_graph_node": params.form_graph_node,
          "form_data": state.model.currentJSONFormData
        };
      } else if (params.action.type === "reset") {
        messageType = "action";
        messageContent = {
          "action": "reset",
          "form_data": {}
        };
      } else if (params.action.type === "shacl_validation"){
        /* Validaation action is unique because it does not submit the form data but initiate validation of all 
        enter data in the application*/
        messageType = "action";
        messageContent = {
          "action_type": "shacl_validation",          
          "action_graph_node": params.action.graph_node
        };
      } else if (params.action.type === "other"){
        messageType = "action";
        messageContent = {
          "action_type": "other",          
          "action_graph_node": params.action.graph_node,
          "form_graph_node": params.form_graph_node
        };
 
      }
      try {
        console.log("The message type:", messageType );
        console.log("The message content:", messageContent );
        thunkApi.dispatch(initiateAppExchange({ messageType, messageContent })).then(() => {
          /**
           * After the data are sent to the server with the function intiateAppExchange,
           *  the function appExchangeGet is called to get the data from the server 
           *  */
          thunkApi.dispatch(appExchangeGet());
        });

      } catch (error) {
        console.error("Failed to submit the form", error);
      }
    }
  }
);

const modelSlice = createSlice({
  name: "model",
  initialState,
  reducers: {

    updateCurrentJSONFormData(state, action) {
      state.currentJSONFormData = action.payload;
    },
    
    generalAction: (state, action: GeneralAction) => {
      //const currentAction = state.templateTriples.actions.find(a => a.uuid === action.payload)
      owlTemplate.handleConnection(action, action.payload);
    },

    processReceivedMessage: function (state, action: ResponseAction) {
      const layout = processResponse(state, action.payload);
      state.currentLayout = layout !== null ? layout : React.createElement("div", null, "Error");
      state.layoutRefreshNecessary = true;
    }

  }
});


export const { generalAction, processReceivedMessage, updateCurrentJSONFormData } = modelSlice.actions;

export default modelSlice.reducer;