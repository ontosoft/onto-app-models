import React, { useState, useEffect } from "react";
import { useAppSelector, useAppDispatch } from "../app/hooks";
import {
  runInnerAppModelOnServer,
  initiateAppExchange,
  appExchangeGet,
} from "../data/appStateSlice";
import { getJSDocTemplateTag } from "typescript";

/**
 * ServerModelRunner Component
 *
 * This component is responsible for showing what application model
 * is loaded on the server and it provides a button to run
 * the model on the server (function runModelOnServer)
 *
 */

const ServerModelRunner: React.FC = () => {
  const dispatch = useAppDispatch();
  const innerModelLoaded = useAppSelector(
    (state) => state.serverInnerModels.innerUIModelLoadingStatus
  );
  const appExchangeStatus = useAppSelector(
    (state) => state.stateData.appExchangeGetStatus
  );
  const [loadedModelInfo, setLoadedModelInfo] = useState<
    { filename: string; model: string; description: string }[]
  >([]);
  const appRunningOnServer = useAppSelector(
    (state) => state.stateData.runningOnServer
  );
  const [counter, setCounter] = useState(0);

  /**
   * This function runs the application on the server and
   * additionally makes the first exchange with the server.
   * It means that the server should return the first
   * application layour or the first form (depending on
   * the application model)
   */
  const runModelOnServer = async () => {
    if (innerModelLoaded === "idle") {
      console.log("The inner model is not loaded yet");
    } else if (
      innerModelLoaded === "succeeded" &&
      appRunningOnServer === "idle"
    ) {
      // If the inner model is loaded and the application should be run
      dispatch(runInnerAppModelOnServer()).then(() => {
        /**
         * After the model is run on the server, initiate the first
         * exchange with the server
         **/
        dispatch(initiateAppExchange()).then(() => {
          /**
           * After the data to exchange are sent run the function to get data in the exchange
           *  */
          dispatch(appExchangeGet());
        });
      });
    }
  };

  useEffect(() => {
    // TODO: this userEffect should be deleted
    setCounter((counter) => counter + 1);
    console.log("Loader counter is", counter);
  }, [innerModelLoaded]);

  return (
    <div>
      <div className="text-center">
        <h2>The following model is loaded.</h2>
      </div>

      <table className="table">
        <thead>
          <tr>
            <th></th>
            <th></th>
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
                <td>
                  <button
                    className="btn btn-primary"
                    onClick={() => runModelOnServer()}
                  >
                    Run the model
                  </button>
                </td>
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

export default ServerModelRunner;
