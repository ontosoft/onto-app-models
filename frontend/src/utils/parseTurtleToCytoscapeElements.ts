import * as $rdf from "rdflib";

// Helper to convert rdflib graph to Cytoscape elements
export function parseTurtleToCytoscapeElements(turtleString: string) {
    const store = $rdf.graph();
    const mimeType = "text/turtle";
    const baseUrl = "http://example.org/base#";

    // Parse the Turtle string into the store (rdflib graph)
    $rdf.parse(turtleString, store, baseUrl, mimeType);

    // Collect nodes and edges
    const nodesSet = new Set<string>();
    const edges: any[] = [];

    store.statements.forEach(st => {
        nodesSet.add(st.subject.value);
        nodesSet.add(st.object.value);
        edges.push({
            data: {
                id: st.subject.value + "-" + st.predicate.value + "-" + st.object.value,
                source: st.subject.value,
                target: st.object.value,
                label: st.predicate.value
            }
        });
    });


    const nodes = Array.from(nodesSet).map(id => ({
        data: { id, label: id }
    }));

    return [...nodes, ...edges];
}