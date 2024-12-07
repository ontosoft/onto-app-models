import React, { useEffect, useState } from "react";
import JsonView from "react18-json-view";
import "react18-json-view/src/style.css";
import { unwrapResult } from "@reduxjs/toolkit";
import { FormToValidate } from "../forms/FormToValidate";
import { BrowserRouter as Router } from "react-router-dom";
import { useAppSelector, useAppDispatch } from "../app/hooks";
import { runInnerAppModelOnServer, initiateAppExchange } from "../data/appStateSlice";

const MainApplicatonPane: React.FC = () => {
  const [generatedResponse, setGeneratedResponse] = useState<any>();
  const appRunningOnServer = useAppSelector(
    (state) => state.stateData.runningOnServer
  );
  const appExchangeStatus = useAppSelector(
    (state) => state.stateData.appExchangeGetStatus
  );

  const dispatch = useAppDispatch();

  const printConsole = () => {
    console.log(generatedResponse);
  };
  useEffect(() => {
    if (appRunningOnServer !== "succeeded") {
      console.log("The application is not running on the server"); 
    }else if (appExchangeStatus !== "succeeded"){
      console.log("The application has still not made any data exchange with the server");
    }
    else if (appRunningOnServer === "succeeded") {
     console.log("The application is running on the server"); 
    }
  }, [appRunningOnServer]);

  return (
    <Router>
      <div className="container-fluid">
        <div className="row">
          <div className="col bg-dark text-white">
            <div className="navbar-brand">Restaurant</div>
          </div>
        </div>
        <div className="row">
          <div className="col m-2">
            <FormToValidate submitText="Submit" cancelText="Cancel" />
          </div>
          <div>
            <pre>
              {generatedResponse && printConsole()}
              <JsonView src={generatedResponse} />
            </pre>
          </div>
        </div>
      </div>
    </Router>
  );
};
export default MainApplicatonPane;
