import {Namespace } from "rdflib";

export const RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#");
export const RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#");
export const XSD =  Namespace("http://www.w3.org/2001/XMLSchema#");
export const OBOP = Namespace("http://purl.org/net/obop/");
export const OWL = Namespace("http://www.w3.org/2002/07/owl#");

const RDFPREFIX = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
const RDFSPREFIX = "http://www.w3.org/2000/01/rdf-schema#";
const OBOPPREFIX = "http://purl.org/net/obop/"; 
const OWLPREFIX = "http://www.w3.org/2002/07/owl#"; 

export const RDF_TYPE = RDFPREFIX+"type";
export const RDF_TYPE_NODE = RDF("type");
export const RDF_LABEL = RDFSPREFIX+"label";
export const RDF_LABEL_NODE = RDFS("label");
export const OWL_IMPORT_NODE = OWL("imports");
export const OWL_ONTOLOGY_NODE = OWL("Ontology");



export const BLOCK_TYPE = OBOPPREFIX+"Block";
export const BLOCK_NODE = OBOP("Block");
export const BUTTON_TYPE =  OBOPPREFIX+"Button";
export const BUTTON_NODE = OBOP("Button");
export const LABEL_TYPE =  OBOPPREFIX+"Label";
export const LABEL_NODE = OBOP("Label");
export const FIELD_TYPE =  OBOPPREFIX+"Field";
export const FIELD_NODE = OBOP("Field");
export const NAMED_INDIVIDUAL_TYPE =  OWLPREFIX+"NamedIndividual";
export const NAMED_INDIVIDUAL_NODE =  OWL("NamedIndividual");
export const ACTION_TYPE = OBOPPREFIX + "Action";
export const ACTION_NODE = OBOP("Action");
export const CONTAINS_DATATYPE_TYPE =  OBOPPREFIX + "containsDatatype";
export const CONTAINS_DATATYPE_NODE = OBOP("containsDatatype");
export const BELONGS_TO = OBOP("belongsTo");
export const HAS_CONNECTION_NODE = OBOP("hasConnection");
export const HAS_CONNECTION_TYPE = OBOPPREFIX+"hasConnection";
export const HAS_LABEL_NODE = OBOP("hasLabel");
export const HAS_LABEL_TYPE = OBOPPREFIX+"hasLabel";
export const HAS_POSITION_NUMBER = OBOPPREFIX+"hasPositionNumber";
export const HAS_SOURCE_NODE = OBOP("hasSource");
export const HAS_SOURCE_TYPE = OBOPPREFIX+"hasSource";
export const HAS_DESTINATION_NODE = OBOP("hasDestination");
export const HAS_DESTINATION_TYPE = OBOPPREFIX+"hasDestination";

//MODEL_BELONGS_TO indicates block (form) to which this part of the 
//model ontology belongs
export const MODEL_BELONGS_TO_NODE = OBOP("modelBelongsTo");
export const MODEL_BELONGS_TO_TYPE = OBOPPREFIX + "modelBelongsTo";
export const IS_RELATED_TO_TARGET_INSTANCE_NODE = OBOP("isRelatedToTargetOntologyInstance");
export const IS_RELATED_TO_TARGET_INSTANCE_TYPE = OBOPPREFIX+"isRelatedToTargetOntologyInstance";
export const ACTIVATES_ACTION_NODE = OBOP("activatesAction");
export const ACTIVATES_ACTION__TYPE = OBOPPREFIX+"activatesAction";
export const GENERATED_ACCORDING_TO_MODEL_NODE = OBOP("generatedAccordingToModel");
export const GENERATED_ACCORDING_TO_MODEL_TYPE = OBOPPREFIX+"generatedAccordingToModel";

export const CONNECTION_TYPE = OBOPPREFIX+"Connection";
//Name of output file 
export const OUTPUT_KG = "http://example.org/logicinterface/restaurant";