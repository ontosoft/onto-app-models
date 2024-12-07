import  AppExchangeResponse  from "./AppExchangeResponse";
import CurrentLayoutFactory from "./CurrentLayoutFactory";
import CurrentLayout from "./CurrentLayout";

const layoutCreating = (serverExchangeResponse: AppExchangeResponse): CurrentLayout  => { 
    let layout : CurrentLayout = CurrentLayoutFactory.getDefaultLayout();
    if (serverExchangeResponse.message_type === 'layout') {
        layout = CurrentLayoutFactory.getCurrentLayout( 
            serverExchangeResponse.layout_type as "form" | "table" | "list" | "tree" | "chart",
            serverExchangeResponse.data);
    }
    return layout;
}

const layoutRendering = (layout : CurrentLayout) => {
    if (layout) {
        layout.displayAttributes();
    }
}
 
export { layoutCreating, layoutRendering };