import React, { useState } from "react";
import "react18-json-view/src/style.css";
import { useAppSelector, useAppDispatch } from "../app/hooks";

const MainApplicatonPane: React.FC = () => {
  const [generatedResponse, setGeneratedResponse] = useState<any>();
  const appRunningOnServer = useAppSelector(
    (state) => state.stateData.startAppOnServer
  );
 const layout = useAppSelector((state) => state.model.currentLayout);

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
