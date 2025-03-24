import React from "react";
import { useAppDispatch } from "../app/hooks";
import {
  terminateAppOnServer,
  closeAppTerminationPane,
} from "../data/appStateSlice";
import {
  initiatePreviewModelList,
  readingListOfServerModels,
} from "../data/serverModelSlice";

export const ShutDownAppModal: React.FC = () => {
  const dispatch = useAppDispatch();

  const terminateTheApplicatonOnServer = () => {
    dispatch(terminateAppOnServer());
    dispatch(readingListOfServerModels()).then(() => {
      dispatch(initiatePreviewModelList());
      dispatch(closeAppTerminationPane());
    });
  };
  const cancelTerminationApplicatonOnServer = () =>
    dispatch(closeAppTerminationPane());

  return (
    <div className="fixed insert-0 flex justify-center">
      <div className="mt-10 flex-row gap-5">
        <h1> Do you want to terminated the active application?</h1>
        <button
          className="btn btn-primary m-2"
          onClick={() => terminateTheApplicatonOnServer()}
        >
          Yes
        </button>
        <button
          className="btn btn-primary m-2"
          onClick={() => cancelTerminationApplicatonOnServer()}
        >
          Cancel
        </button>
      </div>
    </div>
  );
};
