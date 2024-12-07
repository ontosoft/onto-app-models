import { FormElement } from "./FormElement";

export class Form {
    _node : string;
    _position : number = -1;
    _elements : FormElement[] = [];
    _model : string | undefined;


    constructor (newNode: string){
        this._node = newNode;
    }

    addNewElement = (e: FormElement)  => {
        this._elements.push(e);
    }
    get node() {
        return this._node;
    }
    set node(value) {
        this._node = value;
    }
    get position() {
        return this._position;
    }
    set position(value) {
        this._position = value;
    }
 
    get elements() {
        return this._elements;
    }
    set elements(value) {
        this._elements = value;
    }
    get model() {
        return this._model;
    }
    set model(value) {
        this._model = value;
    }

}