import MainApplicatonPane from "./MainApplicationPane";
import ServerModelSelector from "./ServerModelSelector";
import ServerModelRunner from "./ServerModelRunner";
import { useAppSelector } from "../app/hooks";
import { ShutDownAppModal } from "./ShutDownAppModal";

/**
 * GeneratorViewport component renders different UI components 
 * in the process of searching for an applicaton model, loading 
 * the model and then it displays GeneratorViewport component 
 * which is the main working area of the chosen executing application.
 *
 *
 * @description
 * The component uses several selectors to determine which part of 
 * the UI to display:
 * - If `previewListOfInnerModels` is true, This component displays 
 * the `ServerModelSelector` component to chose among the models on the 
 * server.
 * - After the user loads the model on the server 
 * ( the value of `initiedSelectedInnerModelLoading` is true), it displays
 *  the `ServerModelRunner` component.
 * - When finally the application is started `initiatedRunning` is true, it displays the `MainApplicatonPane` component as the place of the application interaction.
 *
 */
export const GeneratorViewport : React.FC = () => {
  const appRunningOnServer = useAppSelector((state) => state.stateData.runningOnServer);
  const previewAppTerminationPane  = useAppSelector((state) => state.stateData.showAppTerminationPane)
  const appExchangeGetStatus = useAppSelector((state) => state.stateData.appExchangeGetStatus);
  const previewListOfServerModels = useAppSelector(
    (state) => state.serverInnerModels.previewModelList
  );
  const initiedSelectedInnerModelLoading = useAppSelector( 
    (state) => state.serverInnerModels.initiedSelectedInnerModelLoading
  )
 const showMainApplicationPane = useAppSelector((state) => state.stateData.showMainApplicationPane);


  return (
    <div className="col-10" id="display">
      {(() => {
        if (previewAppTerminationPane) {
          return <ShutDownAppModal/>;
        }
        else if (appExchangeGetStatus === "succeeded" &&
           showMainApplicationPane && appRunningOnServer ) {
          /**  Displays main application panel if the form model running and 
           *   the frontend has activated the main application panel  
           * 
           */ 
          console.log("Main application panel is displayed");
          return <MainApplicatonPane  />;
        } else if (previewListOfServerModels) {
          return <ServerModelSelector />;
        } else if (initiedSelectedInnerModelLoading) {
          /**
           * Inner model is selected from the list and it is initiated the loading process
           * on the server 
           */
            return <ServerModelRunner />;
        } else {
          return (
              <div className="text-center">
                <h2>UI model is not loaded</h2>
              </div>
          );
        }
      })()}
    </div>
  );
};
