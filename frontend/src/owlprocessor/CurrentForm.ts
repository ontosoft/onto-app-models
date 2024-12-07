import { FormElement } from "./FormElement";
/**
 * This class is used to store the current form that is being processed. This could be a class which inherits from Form class and has additional methods to process the form.
 * TODO : Consider removing this class and using Form class directly.
 */
export class CurrentForm {
    addNewElement(arg0: FormElement) {
        throw new Error("Method not implemented.");
    }
    elements: FormElement[] = [] ;

    constructor() {
        this.elements =[];
    }


}
