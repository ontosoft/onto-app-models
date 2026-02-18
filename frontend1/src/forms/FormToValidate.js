import React from "react";
import { useNavigate } from "react-router-dom";
import { ValidationError } from "./ValidationError";
import { GetMessages } from "./ValidationMessages";
import { useAppDispatch, useAppSelector } from "../app/hooks";
import { BUTTON_TYPE, FIELD_TYPE, LABEL_TYPE } from "../owlprocessor/InterfaceOntologyTypes";
import { generalAction } from "../data/modelSlice";

export function FormToValidate(submitText, cancelText) {
  const validationErrors = {};
  const formElements = {};
  const dispatch = useAppDispatch();
  const formModel = useAppSelector((state) => state.model.currentForm);
  const navigate = useNavigate();
  const defaultAttrs = { type: "text", required: true };

  const handleSubmit = (event) => {
    // this.setState(
    //   (state) => {
    //     const newState = {
    //       ...state,
    //       validationErrors: {},
    //     };
    //     Object.values(formElements).forEach((elem) => {
    //       if (!elem.checkValidity()) {
    //         newState.validationErrors[elem.name] = GetMessages(elem);
    //       }
    //     });
    //     return newState;
    //   },
    //   () => {
    //     if (Object.keys(validationErrors).length === 0) {
    //       const data = Object.entries(formElements).map((e) => ({
    //         id: e[1].id,
    //         value: e[1].value,
    //       }));
    //       const activatedAction = {
    //         insertedData: data,
    //         type: "connection",
    //         name: event.target.id,
    //       };
    //       dispatch(generalAction(activatedAction));
    //       navigate.push("/");
    //     }
    //   }
    // );
  };

  const registerRef = (element) => {
    if (element !== null) {
      formElements[element.name] = element;
    }
  };

  const renderElement = (formItem) => {
    if (formItem.type === FIELD_TYPE) {
      return (
        <div className="form-group" key={formItem.label}>

          if (formItem.label) <label>{formItem.label}</label>
          {/*<ValidationError errors={validationErrors[name]} />*/}
          <input
            className="form-control"
            name={formItem.id}
            ref={registerRef}
            id={formItem.id}
            {...defaultAttrs}
            {...formItem.attrs}
          />
        </div>
      );
    } else if (formItem.type === BUTTON_TYPE) {
      if (formItem.action === "cancel") {
        return (
          <button
            className="btn btn-secondary m-1"
            onClick={() => navigate(-1)}
            id={crypto.randomUUID()}
          >
            {cancelText || "Cancel"}
          </button>
        );
      } else
        return (
          <button
            className="btn btn-primary m-1"
            id={formItem.label}
            onClick={handleSubmit()}
          >
            {submitText || "Submit"}
          </button>
        );
    }
  };
  // The function is general functions that is defined
  const renderAction = (modelItem) => {
    return (
      <div className="text-center">
        {/*     <button className="btn btn-secondary m-1" 
           onClick={() => navigate(-1)} id = {crypto.randomUUID()}>
          {cancelText || "Cancel"}
    </button> 
        <button
          className="btn btn-primary m-1"
          id={modelItem.label}
          onClick={handleSubmit()}
        >
          {submitText || "Submit"}
        </button> */}
      </div>
    );
  };
  return (
    <React.Fragment>
      {formModel.elements.map((m) => renderElement(m))}
    </React.Fragment>
  );
}
