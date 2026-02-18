import {
    BUTTON_TYPE, FIELD_TYPE, LABEL_TYPE, RDF_TYPE, RDF_LABEL,
    CONNECTION_TYPE, HAS_CONNECTION_TYPE, HAS_SOURCE_TYPE, HAS_DESTINATION_TYPE, 
    HAS_LABEL_TYPE, MODEL_BELONGS_TO_TYPE, IS_RELATED_TO_TARGET_INSTANCE_TYPE, 
    HAS_POSITION_NUMBER
} from "./InterfaceOntologyTypes";

export const isRdfType = (term) => {
    if (term.termType === "NamedNode" && term.value === RDF_TYPE) {
        return true;
    }
    else return false;
}

export const isRdfLabel = (term) => {
    if (term.termType === "NamedNode" && term.value === RDF_LABEL) {
        return true;
    }
    else return false;
}

export const isHasLabel = (term) => {
    if (term.termType === "NamedNode" && term.value === HAS_LABEL_TYPE) {
        return true;
    }
    else return false;
}

export const isHasPositionNumber = (term) => {
    if (term.termType === "NamedNode" && term.value === HAS_POSITION_NUMBER) {
        return true;
    }
    else return false;
}




export const isHasConnection = (term) => {
    if (term.termType === "NamedNode" && term.value === HAS_CONNECTION_TYPE)
        return true;
    else return false;
}

export const isHasSource = (term) => {
    if (term.termType === "NamedNode" && term.value === HAS_SOURCE_TYPE)
        return true;
    else return false;
}

export const isHasDestination = (term) => {
    if (term.termType === "NamedNode" && term.value === HAS_DESTINATION_TYPE)
        return true;
    else return false;
}

export const isButtonType = (term) => {
    if (term.termType === "NamedNode" && term.value === BUTTON_TYPE)
        return true;
    else return false;
}

export const isLabelType = (term) => {
    if (term.termType === "NamedNode" && term.value === LABEL_TYPE)
        return true;
    else return false;
}

export const isFieldType = (term) => {
    if (term.termType === "NamedNode" && term.value === FIELD_TYPE)
        return true;
    else return false;
}

export const isElementOfFieldType = (element) => {
    if (element.type === FIELD_TYPE) {
        return true;
    }
    else return false;
}

export const isElementOfButtonType = (element) => {
    if (element.type === BUTTON_TYPE) {
        return true;
    }
    else return false;
}


export const isConnection = (term) => {
    if (term.termType === "NamedNode" && term.value === CONNECTION_TYPE)
        return true;
    else return false;
}

export const isModelBelongsTo = (term) => {
    if (term.termType === "NamedNode" && term.value === MODEL_BELONGS_TO_TYPE)
        return true;
    else return false;
}

export const isRelatedToDataOntologyInstance = (term) => {
    if (term.termType === "NamedNode" && term.value === IS_RELATED_TO_TARGET_INSTANCE_TYPE)
        return true;
    else return false;
}
/** 
 * Keeping only predicates that belong to the domain ontology and 
 * which do not belong to the model ontology (logicinterface)  
 * 
 **/
export const isValidDomainOntologyPredicate = (term) => {
    if (!isModelBelongsTo(term) && !isRelatedToDataOntologyInstance(term) &&
        !isHasSource(term) && !isHasDestination(term)
    ) return true;
    else return false;
}

export const generateHashCode = () => {
    return Math.random().toString(36).substring(7);
}