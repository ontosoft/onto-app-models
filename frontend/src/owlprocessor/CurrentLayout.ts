import { Form } from "./Form";

class CurrentLayout {
    layout_type: "form" | "table" | "list" | "tree" | "chart" | "text" = "text";
    data?: Form ;

    constructor( layout_type: "form" | "table" | "list" | "tree" | "chart"| "text", form?: any) {
        this.layout_type = layout_type;
        if (layout_type === "form") {   
            this.data = form? new Form(form) : undefined;
        }
    }

    displayAttributes(): void {
        console.log('layout_type: ${this.layout_type}');
    }
}

export default CurrentLayout;