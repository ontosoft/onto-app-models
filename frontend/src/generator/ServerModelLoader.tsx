import React, {useState, useEffect} from "react";
import { useAppSelector, useAppDispatch } from "../app/hooks";
import { loadInnerUIModel } from "../data/serverModelSlice";


const ServerModelLoaded: React.FC = () => {
    const dispatch = useAppDispatch();
    const innerModelLoaded = useAppSelector((state) => state.serverInnerModels.innerUIModelLoadingStatus);
    const selectedModel = useAppSelector((state) => state.serverInnerModels.selectedServerModel);
    const [loadedModelInfo, setLoadedModelInfo] = useState<{ filename: string, model: string, description: string }[]>([]);


    const runModelOnServer = async () => {
        try {
            const response = await fetch("http://localhost:8089/run_loaded_inner_server_models"); 
            const data = await response.json();
            console.log(data);
            setLoadedModelInfo(JSON.parse(data));
            console.log(data);
        } catch (error) {
            console.error("Failed to load inner server models", error);
        }
    };   

    useEffect(() => {
        if (innerModelLoaded === "idle") {
            dispatch(loadInnerUIModel(selectedModel || ""))
        }
    }, [innerModelLoaded]);


    return (
        <div>
            <div className='text-center' > 
                <h2>The following model is loaded.</h2>
            </div>

            <table className="table">
                <thead>
                    <tr>
                        <th></th><th></th>
                    </tr>
                </thead>
                <tbody>
                    {loadedModelInfo ? (
                        <>
                        <tr>
                            <td>File:</td> 
                            <td>loadedModelInfo.filename</td>
                        </tr>
                        <tr>
                            <td>Description:</td> 
                            <td>loadedModelInfo.description</td>
                        </tr>                       
                        <tr>
                            <td>Action:</td> 
                            <td><button className="btn btn-primary" onClick={() => runModelOnServer()}>Run the model</button></td>
                        </tr> 
                        </>
                    ) : (
                        <tr>
                            <td>No model is loaded.</td>
                            <td></td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>

    );
}; 

export default ServerModelLoaded;


