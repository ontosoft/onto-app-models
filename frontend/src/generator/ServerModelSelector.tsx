import React, { useEffect, useState } from 'react';
import { useAppSelector, useAppDispatch } from '../app/hooks';
import { initiateSelectedInnerModelLoading, innerModelListLoadingDone } from '../data/serverModelSlice';

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

  useEffect(() => {
    if (isLoadListOfInnerModelsPressed) {
      listInnerServerModels();
    }
  }, [isLoadListOfInnerModelsPressed]);

  const initiateModelLoadingOnServer = (filename: string) => {
    dispatch(initiateSelectedInnerModelLoading(filename));
    dispatch(innerModelListLoadingDone());
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