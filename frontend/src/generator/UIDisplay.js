import GeneralForm from "./GeneralForm";
import ServerModelSelector from "./ServerModelSelector";
import ServerModelLoaded from "./ServerModelLoader";
import { useAppSelector } from "../app/hooks";

export const UIDisplay = () => {
  const running = useAppSelector((state) => state.stateData.running);
  const previewListOfInnerModels = useAppSelector(
    (state) => state.serverInnerModels.initiedModelListLoading
  );
  const initiedSelectedInnerModelLoading = useAppSelector( 
    (state) => state.serverInnerModels.initiedSelectedInnerModelLoading
  )
  const formFields = useAppSelector((state) => state.model.currentForm);

  return (
    <div className="col-10" id="display">
      {(() => {
        if (running) {
          return <GeneralForm formModel={formFields} />;
        } else if (previewListOfInnerModels) {
          return <ServerModelSelector />;
        } else if (initiedSelectedInnerModelLoading) {
          return <ServerModelLoaded />;
        } else {
          return (
              <div className="text-center">
                <h2>UI model is not yet loaded</h2>
              </div>
          );
        }
      })()}
    </div>
  );
};
