import { createSlice, PayloadAction } from "@reduxjs/toolkit";

type EditAction = PayloadAction<{id:number, datatype:{}, value:{}}>;

interface AppState {
    running: boolean;
    editing: boolean;
    selectedId: number;
    selectedType: {};
}
const initialState :AppState = {
    running : false,
    editing: false,
    selectedId: -1,
    selectedType: {}
}

export const appStateSlice = createSlice ({
    name:"appState",
    initialState,
    reducers:{
        startRunningTemplate:  (state) =>{
            state.running = true;
        },
        startEditingItem: (state, action: EditAction) =>{
            state.selectedType = action.payload.datatype;
            state.editing = true;
        },
        startCreatingItem: (state) =>{
            state.editing = true;
        },
        endEditingItem: (state) =>{
            state.editing = false;
        }
    }
});

export const {startRunningTemplate, startEditingItem, startCreatingItem, endEditingItem} = appStateSlice.actions;
export default appStateSlice.reducer;