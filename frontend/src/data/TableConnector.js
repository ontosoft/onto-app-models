import { connect } from "react-redux"
import { TEMPLATES, ITEMS } from "./dataTypes";
import { deleteItem, deleteTemplate } from "./modelActionCreators";
import { startEditingItem, startEditingTemplate } from "./StateActions";

export const TableConnector = (dataType, presentationComponent) => {

    const mapStateToProps = (storeData, ownProps) => {
        if (!ownProps.needItems) {
            return { items: storeData.modelData[ITEMS] };
        } else {
            return {
                suppliers: storeData.modelData[TEMPLATES].map(supp => ({
                    ...supp,
                    items: supp.products.map(id =>
                        storeData.modelData[ITEMS].find(p => p.id === Number(id)) || id)
                        .map(val => val.name || val)
                }))
            }
        }
    }

    const mapDispatchToProps = {
        editCallback: dataType === ITEMS
            ? startEditingItem : startEditingTemplate,
        deleteCallback: dataType === ITEMS
            ? deleteItem : deleteTemplate
    }
    return connect(mapStateToProps, mapDispatchToProps)(presentationComponent);

}