import React, { useEffect, useState } from "react";
import JsonView from "react18-json-view";
import "react18-json-view/src/style.css";
import { unwrapResult } from "@reduxjs/toolkit";
import { FormToValidate } from "../forms/FormToValidate";
import { BrowserRouter as Router } from "react-router-dom";
import { useAppSelector, useAppDispatch } from "../app/hooks";
import { runInnerAppModelOnServer, initiateAppExchange } from "../data/appStateSlice";
import { Layout } from "../owlprocessor/LayoutRendering";

const MainApplicatonPane: React.FC = () => {
  const [generatedResponse, setGeneratedResponse] = useState<any>();
  const appRunningOnServer = useAppSelector(
    (state) => state.stateData.runningOnServer
  );
  const appExchangeStatus = useAppSelector(
    (state) => state.stateData.appExchangeGetStatus
  );
  const layout = useAppSelector((state) => state.model.currentLayout);

  const dispatch = useAppDispatch();

  const printGeneratedViewOnConsole = () => {
    console.log(layout);
  };
  // useEffect(() => {
  //   if (appRunningOnServer !== "succeeded") {
  //     console.log("The application is not running on the server"); 
  //   }else if (appExchangeStatus !== "succeeded"){
  //     console.log("The application has still not made any data exchange with the server");
  //   }
  //   else if (appRunningOnServer === "succeeded") {
  //    console.log("The application is running on the server"); 
  //   }
  //   printGeneratedViewOnConsole();
  // }, [appRunningOnServer]);

  return <div>{layout}</div>;
};
export default MainApplicatonPane;
