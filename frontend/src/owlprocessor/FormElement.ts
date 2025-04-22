export class FormElement {
    type: string | undefined;
    private _id: string;
    name!: string;
    private _label: string | undefined;

    constructor(type: string) {
        this.type = type;
        this._id = crypto.randomUUID();
    }
    public get label(): string | undefined {
        return this._label;
    }
    public set label(value: string | undefined) {
        this._label = value;
    }
    public get id(): string {
        return this._id;
    }
    public set id(value: string) {
        this._id = value;
    }
}