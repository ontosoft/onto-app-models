import { FormToValidate } from "../forms/FormToValidate";
import { BrowserRouter as Router } from "react-router-dom";

function GeneralForm() {

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
              <FormToValidate 
              submitText='Submit'
              cancelText='Cancel'/>
            </div>
          </div>
        </div>
    </Router>
  );
}
export default GeneralForm;
