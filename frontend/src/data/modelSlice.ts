import { PayloadAction, createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { ActionProcessor } from "../owlprocessor/ActionProcessor";
import { TemplateFactory } from "../owlprocessor/TemplateFactory";
import { RunningInstance } from "../owlprocessor/RunningInstance";
import { Formula } from "rdflib";
import { CurrentForm } from "../owlprocessor/CurrentForm";
import { getLayout } from "../owlprocessor/LayoutRendering";
import AppExchangeResponse from "../owlprocessor/AppExchangeResponse";
import { RootState } from "../app/store";
import { initiateAppExchange, appExchangeGet } from "./appStateSlice";
import React from "react";
import { AppDispatch } from "../app/store";
import { avatarClasses } from "@mui/material";

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
  outputGraph: Formula,
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
  outputGraph: {} as Formula,
  asyncStatus: 'complete',
  currentLayout: {} as React.ReactNode,
  layoutRefreshNecessary: false
};

const processResponse = (serverExchangeResponse: AppExchangeResponse): React.ReactNode => {
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


export const triggerAction = (actionType: string) => async (dispatch: AppDispatch, getState: () => RootState) => {
  try {
    const state: RootState = getState();
    const currentForm: CurrentForm = state.model.currentForm;
    let messageType: string = "";
    let messageContent: any = {}; 
    if (actionType === "submit") {
      messageType = "submit";
      messageContent = {
            "form_node": "form1",
            "form_data": state.model.currentJSONFormData
        }
    }

    await dispatch(initiateAppExchange({ messageType, messageContent }));
    await dispatch(appExchangeGet());
  } catch (error) {
    console.error("Failed to submit the form", error);
  }
}

const modelSlice = createSlice({
  name: "model",
  initialState,
  reducers: {

    updateFormData(state, action) {

    },
    submitForm(state, action) {
      // TODO: Implement form submission logic
      // if we have more forms in the same page, we need to find the correct form
      // const currentForm = state.templateTriples.forms.find(f => f.uuid === action.payload)
      //owlTemplate.handleFormSubmission(action, action.payload);
    },
    generalAction: (state, action: GeneralAction) => {
      //const currentAction = state.templateTriples.actions.find(a => a.uuid === action.payload)
      owlTemplate.handleConnection(action, action.payload);
    },

    processReceivedMessage: function (state, action: ResponseAction) {
      const layout = processResponse(action.payload);
      state.currentLayout = layout !== null ? layout : React.createElement("div", null, "Error");
      state.layoutRefreshNecessary = true;
    }

  }
});


export const { generalAction, processReceivedMessage } = modelSlice.actions;

export default modelSlice.reducer;