import { configureStore, ThunkAction, Action } from '@reduxjs/toolkit';
import modelReducer from '../data/modelSlice';
import appStateReducer from '../data/appStateSlice';
import serverModel from '../data/serverModelSlice';


export const store = configureStore({
  reducer: {
    model: modelReducer,
    stateData: appStateReducer,
    serverInnerModels: serverModel
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    })
});

// Do we need applyMiddleware here in configStore?

export type AppDispatch = typeof store.dispatch;
export type RootState = ReturnType<typeof store.getState>;
export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  RootState,
  unknown,
  Action<string>
>;
