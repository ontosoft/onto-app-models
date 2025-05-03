export class Element {
        _graph_node = null;
        _label = null;
        // type of the HTML element
        _type = null;
        // type of the value that has to be entered using this 
        // HTML element 
        _valueType = null;
        _position = null;
        _value = null;
        _action = null;
        // this data property should be added to the this model instnce 
        // modelInstance is in rdfstore NamedNode and represents URI
        _modelInstance = null;

    constructor(newNode){
        this._graph_node = newNode;
        this._label = null;
        // type of the HTML element
        this._type = null;
        // type of the value that has to be entered using this 
        // HTML element 
        this._valueType = null;
        this._position = null;
        this._value = null;
        this._action = null;
        this._modelInstance=null;
    }

    get graph_node(){
        return this._graph_node;
    }

    set graph_node(newNode){
        this._graph_node = newNode;
    }

    get label(){
        return this._label;
    }

    set label(value){
        this._label = value;
    }

    get type(){
        return this._type;
    }

    set type(value){
        this._type = value;
    }

    get valueType() {
        return this._valueType;
    }
    set valueType(value) {
        this._valueType = value;
    }

    get value(){
        return this._value;
    }

    set value(newValue){
        this._value = newValue;
    }

    get position(){
        return this._position;
    }

    set position(newPosition){
        this._position = newPosition;
    }

    get action() {
        return this._action;
    }

    set action(value) {
        this._action = value;
    }

     get modelInstance() {
        return this._modelInstance;
    }

    set modelInstance(value) {
        this._modelInstance = value;
    }

}