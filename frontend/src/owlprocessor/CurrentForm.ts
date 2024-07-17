import { FormElement } from "./FormElement";

export class CurrentForm {
    elements: FormElement[] = [] ;

    constructor() {
        this.elements =[];
    }
    addNewElement = (e: FormElement)  => {
        this.elements.push(e);
    }

}
