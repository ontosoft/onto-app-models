import { configureStore, ThunkAction, Action, createListenerMiddleware  } from '@reduxjs/toolkit';
import modelReducer from '../data/modelSlice';
import appStateReducer from '../data/appStateSlice';
import serverModel from '../data/serverModelSlice';
import { effect } from 'zod';

export const listenerMiddleware = createListenerMiddleware();

export const store = configureStore({
  reducer: {
    model: modelReducer,
    stateData: appStateReducer,
    serverInnerModels: serverModel
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }).prepend(listenerMiddleware.middleware)
});



//TODO: Do we need applyMiddleware here in configStore?

export type AppDispatch = typeof store.dispatch;
export type RootState = ReturnType<typeof store.getState>;
export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  RootState,
  unknown,
  Action<string>
>;


