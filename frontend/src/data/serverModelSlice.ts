import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { stat } from "fs";
/*
   selectServerModelSlice has a function to chose among those 
   inner models (stored on the server) which has to be executed by the app generator
*/

export interface ServerModelState {
    initiedModelListLoading: boolean;
    initiedSelectedInnerModelLoading: boolean;
    innerUIModelLoadingStatus: 'idle' | 'loading' | 'succeeded' | 'failed';
    selectedServerModel: string | null;
    innerUIModelLoadingError: string | null;
} 

const initialState :ServerModelState = {
    initiedModelListLoading : false,
    initiedSelectedInnerModelLoading: false,
    innerUIModelLoadingStatus: 'idle',
    selectedServerModel: null,
    innerUIModelLoadingError: null
}

export const loadInnerUIModel = createAsyncThunk('model/loadModel',  async (filename: string | undefined | null) => { 
   /** Load the chosen UI model on the server and retrun the 
    * messige that the model is loaded
    */
   try{
       const url = new URL("http://localhost:8089/load_inner_uimodel_from_server?");
       url.searchParams.append('filename', filename as string);
       const response = await fetch(url.toString(), {
           method: "GET",
           headers: {
               "Content-Type": "application/json",
           }
       });
       return response.json();
    }
    catch (error) {
        console.error("Failed to load inner server UI model", error);
    }
});

export const selectedServerModelSlice = createSlice({
    name: "selectedSeverModel",
    initialState,
    reducers: {
        selectModel: (state, action) => {
            state.selectedServerModel = action.payload;
        },
        initiateInnerModelsListLoading: (state) => {
            console.log("Initiating inner models list loading");
            state.initiedModelListLoading = true;
        },
        initiateSelectedInnerModelLoading: (state, action: { payload: string | undefined | null }) => {
            state.initiedSelectedInnerModelLoading = true;
            state.selectedServerModel = action.payload ?? null;
        },
        innerModelListLoadingDone: (state) => {
            state.initiedModelListLoading = false;
        }
    },
    extraReducers(builder) {
        builder.addCase(loadInnerUIModel.pending, (state) => {
            state.innerUIModelLoadingStatus = 'loading';
        });
        builder.addCase(loadInnerUIModel.fulfilled, (state, action) => {
            state.innerUIModelLoadingStatus = 'succeeded';
            state.selectedServerModel = action.payload;
        });
        builder.addCase(loadInnerUIModel.rejected, (state, action) => {
            state.innerUIModelLoadingStatus = 'failed';
            state.innerUIModelLoadingError = action.payload as string;
        });
    }
});

export const { selectModel, initiateInnerModelsListLoading,
    initiateSelectedInnerModelLoading,  
    innerModelListLoadingDone
 } = selectedServerModelSlice.actions;

export default selectedServerModelSlice.reducer;