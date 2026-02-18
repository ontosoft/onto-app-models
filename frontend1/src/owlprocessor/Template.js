export class Template {

    _startingFormBlock = null;
    _formBlocks = [];
    _actions = [];

    constructor(){
        this._startingFormBlock= null;
        this._formBlocks = [];

    }

    get firstForm() {
        return this._startingFormBlock;
    }
    set firstForm(forms){
        this._startingFormBlock = forms;
    }

    get forms() {
        return this._formBlocks;
    }

    set forms (forms){
        this._formBlocks = forms;
    }

    get actions() {
        return this._actions;
    }
    set actions(value) {
        this._actions = value;
    }
}