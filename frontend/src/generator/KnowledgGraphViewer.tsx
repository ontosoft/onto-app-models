import CytoscapeComponent from "react-cytoscapejs";
import { parseTurtleToCytoscapeElements } from "../utils/parseTurtleToCytoscapeElements";

export function KnowledgeGraphViewer({
  turtleString,
}: {
  turtleString: string;
}) {
  const elements = parseTurtleToCytoscapeElements(turtleString);
  console.log("Parsed elements for cytoscape:", elements);

  return (
    //   <CytoscapeComponent
    //   elements={elements}
    // elements={[
    //   { data: { id: 'a', label: 'A' } },
    //   { data: { id: 'b', label: 'B' } },
    //   { data: { id: 'c', label: 'C' } },
    //   { data: { id: 'ab', source: 'a', target: 'b', label: 'rel' } },
    //   { data: { id: 'bc', source: 'b', target: 'c', label: 'rel' } },
    // ]}
    //   style={{ width: "100%", height: "600px" }}
    //   layout={{ name: "cose" }}
    // />
    <CytoscapeComponent
      elements={elements}
      style={{ width: "100%", height: "600px" }}
      // layout={{
      //   name: "cose",
      //   fit: true,
      //   padding: 50,
      //   nodeRepulsion: 100000, // Increase this value
      //   idealEdgeLength: 300, // Increase this value
      //   edgeElasticity: 0.1,
      //   nestingFactor: 1.2,
      //   gravity: 80,
      //   numIter: 1000,
      //   animate: false,
      // }}
      stylesheet={[
        {
          selector: "node",
          style: {
            label: "data(label)",
            "background-color": "#0074D9",
            color: "#fff",
            "text-valign": "center",
            "text-halign": "center",
            "font-size": 10,
            width: 30,
            height: 30,
            "text-wrap": "wrap",
            "text-max-width": 120,
          },
        },
        {
          selector: "edge",
          style: {
            label: (ele: any) => {
              const label = ele.data("label");
              return label.split("/").pop();
            },
            //    label: "data(label)",
            width: 2,
            "line-color": "#ccc",
            "target-arrow-color": "#ccc",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "font-size": 8,
          },
        },
      ]}
    />
  );
}
