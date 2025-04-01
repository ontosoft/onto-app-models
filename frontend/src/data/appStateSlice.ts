import { createSlice, PayloadAction, createAsyncThunk } from "@reduxjs/toolkit";
import { fetchRunModelOnServer, initiateAppExchangeAPI,
     appExchangeGetAPI, fetchTerminateAppOnServer } from "./appStateAPI";
import  AppExchangeResponse from "../owlprocessor/AppExchangeResponse";
import { processReceivedMessage } from "./modelSlice";
import { RootState } from "../app/store";
import { stat } from "fs";


type EditAction = PayloadAction<{ id: number, datatype: {}, value: {} }>;

/**
 * The AppState interface is used to define the state of the application 
 * on the frontend side.   
 */
interface AppState {
    runningOnServer: boolean;
     /*
     * running on the server. If it has value true, then the front end can exchange 
     * messages with the running app on the server
    */ 

    startAppOnServer: 'idle' | 'loading' | 'succeeded' | 'failed';
    /**
     * appExchangePost and appExchangeGet are indicatorso of the exchange with
     * the app on the server has been successfully completed. 
     * This exchange always sends (posts) data to the server and gets a response back. 
     * The processing of the gathered data takes place in the serverModelSlice
    */

    appExchangePostStatus: 'idle' | 'loading' | 'succeeded' | 'failed';
    appExchangeGetStatus: 'idle' | 'loading' | 'succeeded' | 'failed';
    appTerminationOnServer: 'idle' | 'loading' | 'succeeded' | 'failed';


    /**
     * Data returned from the server during the app exchange has to be
     * localy processed and displayed in the UI. This flag
     * dataLocalyPocessed indicates 
     * this local processing. Every time the appExchange is started 
     * this flag is set to false, and when the appExchange is finished
     * successfully, this flag is set to true.
     */
    dataLocalyProcessed: boolean;
    editing: boolean;
    selectedId: number;
    waitingForServerData: boolean;
    selectedType: {};
    /**
     * The MainApplicationPane presents the app UI and
     *  this showMainApplicationPane flag is used to indicate
     * whether the main application pane is shown or not.
     */
    showMainApplicationPane: boolean;
    /* The user wants to initiate terminating the current application on the server*/
    showAppTerminationPane:boolean

}
const initialState: AppState = {
    runningOnServer: false,
    startAppOnServer: 'idle',
    appExchangePostStatus: 'idle',
    appExchangeGetStatus: 'idle',
    appTerminationOnServer: 'idle',

    dataLocalyProcessed: true,
    editing: false,
    waitingForServerData: false,
    selectedId: -1,
    selectedType: {},
    showMainApplicationPane: false,
    showAppTerminationPane:false
}

/** It runs an already loaded UI model on the server and returns the 
 * application status 
*/
export const runInnerAppModelOnServer = createAsyncThunk('appstate/runModelOnServer',
    async () => {
        const response = await fetchRunModelOnServer();
        return response;
    }
);
/** This function invokes an API to terminate a running application 
* on the server and returns the application status 
*/
export const terminateAppOnServer = createAsyncThunk('appstate/terminateAppOnServer',
    async () => {
        const response = await fetchTerminateAppOnServer();
        return response;
    }
);


/**
 * This function initiates the exchange with the server
 */
export const initiateAppExchange = createAsyncThunk('appstate/initiateAppExchange',
    async (params:{messageType:string, messageContent:any}, thunkApi) => {
        let state:RootState = thunkApi.getState() as RootState;
        console.log("The app state (read form inside the Thunk) is", state.stateData.runningOnServer);
        if (!state.stateData.runningOnServer) {
            return { status: "failed",
                message: "The app is still not running on the server."
             };
        }
        else {
            const response:AppExchangeResponse = await initiateAppExchangeAPI(
                {
                   message_type: params.messageType,
                   message_content: params.messageContent
                }
            );
            return response;
        }
    }
);

export const appExchangeGet = createAsyncThunk('appstate/appExchangeGetData',
    async (_, thunkApi) => {
        let state:RootState = thunkApi.getState() as RootState;
        if (!state.stateData.waitingForServerData) {
            return { status: "failed",
                message: "The model is still not running on the server."
             };
        }
        else {
            /**
             * The application exchange logic
             * After the application exchange data are received, the data 
             * are processed in the modelSlice and if the layout refresh is 
             * necessary, the main application pane is activated.
             * 
             * The main application pane is activated in the appStateSlice by the action activateMainApplicationPana
             */
            const response:AppExchangeResponse = await appExchangeGetAPI();
            thunkApi.dispatch(processReceivedMessage(response));
            let state1:RootState = thunkApi.getState() as RootState;
            console.log("Do we need to refresh the layout?", state1.model.layoutRefreshNecessary);
 
            if (state1.model.layoutRefreshNecessary) {
                thunkApi.dispatch(activateMainApplicationPane());
            }
        }
    }
);



export const appStateSlice = createSlice({
    name: "appState",
    initialState,
    reducers: {
/*        initiateRunningOnServer: (state) => {
            state.initiedRunning = true;
        },*/
        previewAppTerminationPane: (state) => {
            state.showAppTerminationPane= true;
        },
        closeAppTerminationPane: (state) => {
            state.showAppTerminationPane=false;
            state.appTerminationOnServer = 'idle'
        },
        startEditingItem: (state, action: EditAction) => {
            state.selectedType = action.payload.datatype;
            state.editing = true;
        },
        startCreatingItem: (state) => {
            state.editing = true;
        },
        endEditingItem: (state) => {
            state.editing = false;
        },

        startLocalProcessingServerData: (state) => {
        },
        activateMainApplicationPane: (state) => {
            state.showMainApplicationPane = true;
        },
        
    },
    extraReducers: (builder) => {
        builder
            .addCase(runInnerAppModelOnServer.pending, (state) => {
                state.startAppOnServer = 'loading';
                state.dataLocalyProcessed = false;
            })
            .addCase(runInnerAppModelOnServer.fulfilled, (state, action) => {
                state.startAppOnServer = 'succeeded';
                state.runningOnServer = true;
            })
            .addCase(runInnerAppModelOnServer.rejected, (state) => {
                state.startAppOnServer = 'failed';
            })
            .addCase(terminateAppOnServer.pending, (state) => {
                state.appTerminationOnServer = 'loading';
            })
            .addCase(terminateAppOnServer.fulfilled, (state, action) => {
                state.appTerminationOnServer = 'succeeded';
                //reset all status flags and data
                state.runningOnServer = false;
                state.startAppOnServer = 'idle';
                state.appExchangePostStatus = 'idle';
                state.appExchangeGetStatus = 'idle';
                state.appTerminationOnServer = 'idle';
            })
            .addCase(terminateAppOnServer.rejected, (state) => {
                state.appTerminationOnServer = 'failed';
            })

            .addCase(initiateAppExchange.pending, (state) => {
                state.appExchangeGetStatus = 'loading';
            })
            .addCase(initiateAppExchange.fulfilled, (state) => {
                state.appExchangeGetStatus = 'succeeded';
                state.dataLocalyProcessed = false;
                state.waitingForServerData = true;
            })
            
            .addCase(appExchangeGet.rejected, (state) => {
                state.appExchangeGetStatus = 'failed';
            })
            .addCase(appExchangeGet.pending, (state) => {
                state.appExchangeGetStatus = 'loading';
            })
            .addCase(appExchangeGet.fulfilled, (state) => {
                state.appExchangeGetStatus = 'succeeded';
                state.dataLocalyProcessed = false;
                state.waitingForServerData = false;
            });
    },
});

export const { startEditingItem, startCreatingItem, endEditingItem,
    activateMainApplicationPane, previewAppTerminationPane ,
    closeAppTerminationPane}
     = appStateSlice.actions;
export default appStateSlice.reducer;