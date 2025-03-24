import { PayloadAction, createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { ActionProcessor } from "../owlprocessor/ActionProcessor";
import { TemplateFactory } from "../owlprocessor/TemplateFactory";
import { RunningInstance } from "../owlprocessor/RunningInstance";
import { TemplateDataSourceActions } from "../owlprocessor/TemplateDataSource";
import { Template } from "../owlprocessor/Template";
import { Formula } from "rdflib";
import { CurrentForm } from "../owlprocessor/CurrentForm";
import {Layout}  from "../owlprocessor/LayoutRendering";
import AppExchangeResponse from "../owlprocessor/AppExchangeResponse";
import React from "react";

type GeneralAction = PayloadAction<{}>;
type ResponseAction = PayloadAction<AppExchangeResponse>;
type DeleteAction = PayloadAction<{}>;
type FormAction = PayloadAction<string>;
// type ConnectionAction = PayloadAction<{modelAcction, dataType}>;
const owlTemplate = new TemplateFactory();
const owlProcessor = new ActionProcessor ();


export interface ModelState {
  /* This model class is deprecated. It is for keeping track of
     the application state when the application is completely
     running on the front end side.
  */ 
  
  idCounter: number;
  rdfGraph: any;
  templateTriples: Template,
  currentForm: CurrentForm,
  UIRunningInstance: RunningInstance,
  outputGraph: Formula,
  //status of the RDF reading
  asyncStatus: "loading" | "complete",
  currentLayout: React.ReactNode,
  layoutRefreshNecessary: boolean 
 }

const initialState: ModelState = {
  idCounter:1,
  rdfGraph: {} as Formula,
  templateTriples: new Template(),
  currentForm: new CurrentForm(),
  UIRunningInstance: {} as RunningInstance,
  outputGraph: {} as Formula,
  asyncStatus: 'complete',
  currentLayout: {} as JSX.Element,
  layoutRefreshNecessary: false
};

const dataSourceActions = new TemplateDataSourceActions();

const modelSlice = createSlice({
    name: "model",
    initialState,
    reducers: {

        // storeGraph: (state, action: StoreAction) => {
        //             [action.dataType] =[action.dataType].concat([action.payload])
        // },
        // deleteDataFromGraph: (state, action: DeleteAction) => {
        //             [action.dataType]
        //                 .filter(item => item.id !== action.payload)
        // },

        // Transform the RDF graph into the inner template
        transformGraphToInnerTemplate : (state) => {
            state.templateTriples = owlTemplate.graph2Template(state.rdfGraph)
        },
        // the current form is set up  
        prepareFormData : (state, action: FormAction) => {
                state.UIRunningInstance = new RunningInstance(state.templateTriples);
                state.currentForm = state.UIRunningInstance 
                    .generateCurrentForm(action.payload)

        },
        generalAction: (state, action: GeneralAction) =>{
          //const currentAction = state.templateTriples.actions.find(a => a.uuid === action.payload)
          owlTemplate.handleConnection(action, action.payload);
        },

        processReceivedMessage : function (state, action: ResponseAction) {
          state.currentLayout = Layout(action.payload) ;
          state.layoutRefreshNecessary = true;
        }
    
    }
});


export const { transformGraphToInnerTemplate, prepareFormData, generalAction, processReceivedMessage } = modelSlice.actions;

export default modelSlice.reducer;