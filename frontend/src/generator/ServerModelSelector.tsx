import React, { useEffect, useState } from 'react';
import { useAppSelector, useAppDispatch } from '../app/hooks';
import { initiateSelectedInnerModelLoading, innerModelListLoadingDone } from '../data/serverModelSlice';
import { loadInnerUIModel } from "../data/serverModelSlice";


/**
 * The ServerModelSelector component is responsible for showing the list of Application
 *  models present currently on the server. It uses Redux for state management 
 * and provides functionality to load the selected model on the server by 
 * clicking the button to load the model. 
 * TODO: Should be refactored to remove the function listInnerServerModels and the hardcoded server address into a configuration file and
 * the function should be initiated from outside this component.
 */
const ServerModelSelector: React.FC  =() =>{
  const isLoadListOfInnerModelsPressed = useAppSelector((state) => state.serverInnerModels.initiedModelListLoading);
  const dispatch = useAppDispatch();
  const [localInnerModelList, setLocalInnerModelList] = useState<{ filename: string, model: string, description: string, filepath: string }[]>([]);
  const listInnerServerModels = async () => {
    try {
      const response = await fetch("http://localhost:8089/read_inner_server_models"); 
      const data = await response.json();
      setLocalInnerModelList(JSON.parse(data));
      console.log(data);
    } catch (error) {
        console.error("Failed to load inner server models", error);
        }
  };   
  const selectedModel = useAppSelector((state) => state.serverInnerModels.selectedServerModel);
  const innerModelLoaded = useAppSelector((state) => state.serverInnerModels.innerUIModelLoadingStatus);
  useEffect(() => {
    if (isLoadListOfInnerModelsPressed) {
      listInnerServerModels();
    }
  }, [isLoadListOfInnerModelsPressed]);

  const initiateModelLoadingOnServer = (filename: string) => {
    dispatch(initiateSelectedInnerModelLoading(filename));
    dispatch(innerModelListLoadingDone());
    if (innerModelLoaded === "idle") {
      dispatch(loadInnerUIModel(filename || ""))
    }
  }

  return (
    <div>
    <div className='text-center' > 
        <h2> List of UI models on the server</h2>
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
                <button className = "btn btn-primary" onClick={() => initiateModelLoadingOnServer(model.filename)}>Load model</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
    </div>
  );
};

export default ServerModelSelector;