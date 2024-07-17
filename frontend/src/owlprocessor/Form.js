export class Form {
    _node = null;
    _position = null;
    _elements = [];
    _model = null;

    constructor (newNode){
        this._node = newNode;
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