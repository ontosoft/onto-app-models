import React, { useEffect, useState } from "react";
import { useAppSelector, useAppDispatch } from "../app/hooks";
import {
  initiateSelectedInnerModelLoading,
  closePreviewModelList,
  resetLoadingModelListStatus,
  loadInnerUIModel,
} from "../data/serverModelSlice";
import { AppModelData } from "../app/communication";

/**
 * The ServerModelSelector component is responsible for showing the list of Application
 *  models present currently on the server. It uses Redux for state management
 * and provides functionality to load the selected model on the server by
 * clicking the button to load the model.
 * TODO: Should be refactored to remove the function listInnerServerModels and the hardcoded server address into a configuration file and
 * the function should be initiated from outside this component.
 */
const ServerModelSelector: React.FC = () => {
  const dispatch = useAppDispatch();
  
  const [localInnerModelList, setLocalInnerModelList] = useState<
    AppModelData[]
  >([]);
  const listOfServerModels : AppModelData[] = useAppSelector(state => 
    state.serverInnerModels.listOfServerModels);
  const listInnerServerModels = () => {
    setLocalInnerModelList(listOfServerModels);
  };
  
  const innerModelLoaded = useAppSelector(
    (state) => state.serverInnerModels.innerUIModelLoadingStatus
  );
  useEffect(() => {
      listInnerServerModels();
  }, []);

  const initiateModelLoadingOnServer = (filename: string) => {
    dispatch(initiateSelectedInnerModelLoading(filename));
    dispatch(closePreviewModelList());
    dispatch(resetLoadingModelListStatus());
    dispatch(loadInnerUIModel({ filename: filename || "", force_load: true }));
  };

  return (
    <div>
      <div className="text-center">
        <h2> List of application models on the server</h2>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th>Filename</th>
            <th>Model</th>
            <th>Description</th>
            <th> Action </th>
          </tr>
        </thead>
        <tbody>
          {localInnerModelList.map((model, index) => (
            <tr key={index}>
              <td>{model.filename}</td>
              <td>{model.model}</td>
              <td>{model.description}</td>
              <td>
                <button
                  className="btn btn-primary"
                  onClick={() => initiateModelLoadingOnServer(model.filename)}
                >
                  Load model
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ServerModelSelector;
