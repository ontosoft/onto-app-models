import { createSlice, createAsyncThunk, PayloadAction, } from "@reduxjs/toolkit";
import { fetchListOfServerModels } from "./serverModelLoadingAPI";
import { AppModelData } from "../app/communication";

/*
   selectServerModelSlice has a function to choose among those 
   inner models (stored on the server) which has to be executed
   by the app generator, to load those models and other activities 
   with models 
*/



export interface ServerModelState {
    previewModelList: boolean;
    loadingModelListStatus: 'idle' | 'loading' | 'succeeded' | 'failed';
    listOfServerModels: AppModelData[],
    initiedSelectedInnerModelLoading: boolean;
    innerUIModelLoadingStatus: 'idle' | 'loading' | 'succeeded' | 'failed';
    selectedServerModel: string | null;
    innerUIModelLoadingError: string | null;
}

const initialState: ServerModelState = {
    previewModelList: false,
    loadingModelListStatus: "idle",
    listOfServerModels: [],
    initiedSelectedInnerModelLoading: false,
    innerUIModelLoadingStatus: 'idle',
    selectedServerModel: null,
    innerUIModelLoadingError: null
}

export const readingListOfServerModels = createAsyncThunk('model/readListOfModels',
    async () => {
        const response = await fetchListOfServerModels();
        return response;
    }
);

export const loadInnerUIModel = createAsyncThunk('model/loadModel', async ({filename, force_load}: {filename:string | undefined | null, force_load: boolean | undefined | null}) => {
    /** Load the chosen UI model on the server and retrun the 
     * messige that the model is loaded
     */
    try {
        const url = new URL("http://localhost:8089/load_inner_uimodel_from_server?");
        url.searchParams.append('filename', filename as string);
        if (force_load!== undefined && force_load!== null) {
            url.searchParams.append('force_load', String(force_load));
        }
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
        initiatePreviewModelList: (state) => {
            console.log("Initiating loading a list of models on the server");
            state.previewModelList = true;
        },
        closePreviewModelList: (state) => {
            state.previewModelList = false;
        },
        resetLoadingModelListStatus: (state) => {
            state.loadingModelListStatus = "idle"
        },
        initiateSelectedInnerModelLoading: (state, action: { payload: string | undefined | null }) => {
            state.initiedSelectedInnerModelLoading = true;
            state.selectedServerModel = action.payload ?? null;
        }   
    },
    extraReducers(builder) {
        builder.addCase(readingListOfServerModels.pending, (state) => {
            state.loadingModelListStatus = 'loading';
        });
        builder.addCase(readingListOfServerModels.fulfilled, (state, action: PayloadAction<AppModelData[]> ) => {
            state.loadingModelListStatus = 'succeeded';
            state.listOfServerModels = action.payload;
        });
        builder.addCase(readingListOfServerModels.rejected, (state, action) => {
            state.loadingModelListStatus = 'failed';
        });

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

// This listener could have been used instead of useEffects in 
// in the 
// listenerMiddleware.startListening.withTypes<RootState, AppDispatch>()({
//   predicate: (_action, currentState, previousState) => {
//     return currentState.pokemon.search !== previousState.pokomen.search;
//   },
//   effect: async (_action, listenerApi)
// })


export const { selectModel, initiatePreviewModelList,
    initiateSelectedInnerModelLoading,
    closePreviewModelList, resetLoadingModelListStatus
} = selectedServerModelSlice.actions;

export default selectedServerModelSlice.reducer;