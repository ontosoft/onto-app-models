
export class Action {

    _graph_node : string ;
    _type : string | null = null;
    _initiators : string[]= [];
    _uuid : string | null = null;

    constructor(graph_node: string, initiators: string[] = [], type: string | null = null) {
        this._graph_node = graph_node;
        this._type = null;
        this._uuid = null;
    }

    get graph_node(){
        return this._graph_node;
    }

    set graph_node(newNode: string){
        this._graph_node = newNode;
    }

    get type() {
        return this._type;
    }
    set type(value: string | null) {
        this._type = value;
    }
    get initiators() {
        return this._initiators;
    }
    set initiators(value) {
        this._initiators = value;
     }
    get uuid() {
        return this._uuid;
    }
    set uuid(value) {
        this._uuid = value;
     }
    
    generateUUID() {
        this._uuid = crypto.randomUUID();
    }
    toString() {    
        return `Action: { graph_node: ${this._graph_node}, type: ${this._type}, initiators: ${this._initiators.join(", ")}, uuid: ${this._uuid} }`;
    }
 

}