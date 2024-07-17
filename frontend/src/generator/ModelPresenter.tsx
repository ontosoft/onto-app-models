import {
  transformGraphToInnerTemplate,
  prepareFormData,
} from "../data/modelSlice";
import { startRunningTemplate } from "../data/appStateSlice";
import { serialize, Formula } from "rdflib";
import { OUTPUT_KG } from "../owlprocessor/InterfaceOntologyTypes";
import { useAppDispatch, useAppSelector } from "../app/hooks";
//import outputfile from "./output.owl";

export function ModelPresenter() {
  const dispatch = useAppDispatch();
  const inputModelGraph = useAppSelector((store) => store.model.rdfGraph);
  const outputKnowledgeGraph = useAppSelector(
    (store) => store.model.outputGraph
  );
  const currentForm = useAppSelector((store) => store.model.currentForm);

  const previewGraph = (graph: Formula) => {
    let base = OUTPUT_KG;
    let serializedGraph = undefined;
    serialize(null, graph, base, "application/rdf+xml", function (err, str) {
      console.log("Serialized output graph:");
      serializedGraph = str;
    });
    return serializedGraph ? serializedGraph : "Empty";
  };

  const printState = () => {
    // const link = document.createElement('a');
    // link.href = `output.owl`;
    // document.body.appendChild(link);
    // link.click();
    // document.body.removeChild(link);
    let base = OUTPUT_KG;
    serialize(
      null,
      outputKnowledgeGraph,
      base,
      "application/rdf+xml",
      function (err, str) {
        console.log("Serialized output graph:");
        console.log(str);
        //       localStorage.setItem("pageData", str);
      }
    );
    //window.open(newPageUrl, "_blank") //to open new page
  };

  return (
    <div className="container-fluid">
      <div className="row bg-info text-white">
        <div className="navbar-brand">Model instance:</div>
      </div>
      <div className="row bg-info">
        <pre className="text-white">
          {previewGraph(inputModelGraph)}
          {/*   {JSON.stringify(this.state).replace(/\n/g, "<br/>")} */}
        </pre>
      </div>
      <div className="row bg-info text-white">
        <div className="navbar-brand">Output graph instance:</div>
      </div>
      <div className="row bg-info">
        <pre className="text-white">
          {previewGraph(outputKnowledgeGraph)}
          {/*   {JSON.stringify(this.state).replace(/\n/g, "<br/>")} */}
        </pre>
      </div>
    </div>
  );
}
