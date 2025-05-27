import { useAppDispatch, useAppSelector } from "../app/hooks";
import { KnowledgeGraphViewer } from "./KnowledgGraphViewer";
//import outputfile from "./output.owl";

export function ModelPresenter() {
  const dispatch = useAppDispatch();
  const inputModelGraph = useAppSelector((store) => store.model.rdfGraph);
  const outputKnowledgeGraph = useAppSelector(
    (store) => store.model.outputGraph
  );
  const currentForm = useAppSelector((store) => store.model.currentForm);

  const previewGraph = (graph: any) => {
    if (!graph) return "Empty";
    if (typeof graph === "string") return graph;
    // If it's an object, stringify it for display
    return JSON.stringify(graph, null, 2);
  };

  const printState = () => {
    console.log("Serialized output graph:");
    console.log(outputKnowledgeGraph);
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
      <div>
        <KnowledgeGraphViewer turtleString={outputKnowledgeGraph} />
      </div>
    </div>
  );
}
