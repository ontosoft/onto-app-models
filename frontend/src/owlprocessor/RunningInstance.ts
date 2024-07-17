import { CurrentForm } from "./CurrentForm";
import { Element } from "./Element";
import { FormElement } from "./FormElement";
import { BUTTON_TYPE, FIELD_TYPE, LABEL_TYPE } from "./InterfaceOntologyTypes";
import { Template } from "./Template";
import { isElementOfButtonType, isElementOfFieldType } from "./TemplateUtilities";

export class RunningInstance {

    _UIModelInstance: Template;
    _currentForm: CurrentForm;
    _currentAction: any;

    constructor(template: Template) {
        this._UIModelInstance = template;
        this._currentForm = new CurrentForm();
        this._currentAction = null;

    }

    get currentForm() {
        return this._currentForm;
    }

    set currentForm(form) {
        this._currentForm = form;
    }

    get currentAction() {
        return this._currentAction;
    }
    set currentAction(value) {
        this._currentAction = value;
    }

    /** 
     * This function makes final preparation of the current form for the UI processor
  
     * 
     * */
    generateCurrentForm = (formURI: string):CurrentForm => {
        let templateForm = null;
        if (formURI === "-1") {
            // the value "-1" denotes the starting form presented by the application
            templateForm = this._UIModelInstance.firstForm;
        } else {
            templateForm = this._UIModelInstance.forms.find(
                (f) => f.node.value === formURI
            );
        }
            templateForm.elements.forEach((element: Element) => {
                if (element.type === LABEL_TYPE) {
                    this._currentForm?.addNewElement(new FormElement(LABEL_TYPE));
                } else if (isElementOfButtonType(element)) {
                    this._currentForm?.addNewElement(new FormElement(BUTTON_TYPE));
                } else if ( isElementOfFieldType( element)) {
                    let formElement = new FormElement(FIELD_TYPE);
                    if (element.label) formElement.label = element.label!;
                    this.currentForm?.addNewElement(new FormElement(FIELD_TYPE));
                }
            });
        return this.currentForm;
    };


}