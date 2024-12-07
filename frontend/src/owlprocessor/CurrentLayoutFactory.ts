import CurrentLayout from "./CurrentLayout";
import { Form } from "./Form";

class CurrentLayoutFactory {
    static getCurrentLayout(layout_type: "form" | "table" | "list" | "tree" | "chart" | "text", form?: JSON): CurrentLayout {
        return new CurrentLayout(layout_type, form);
    }
    static getDefaultLayout(): CurrentLayout {
        return new CurrentLayout("text", new String("text"));
    }
}

export default CurrentLayoutFactory;