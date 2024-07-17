import { graph, parse, sym } from "rdflib";

export class TemplateDataSourceActions {

    readFile = async(fileName) => {
        let fileContent = await fetch(fileName).then(response => response.text())
            .then(data => data)
            .catch((error) => {
                console.error('Error: Load file problems', error);
            });
        return fileContent;

    }

    getData = async( fileName) => {
        const rdffile = await this.readFile(fileName);
        let rdfgraph = graph();
        let doc = sym("http://example.org/logicinterface/restaurant");
        let contenttype1 = "text/turtle";
        //let contenttype1 = "application/rdf+xml";
        parse(rdffile, rdfgraph, doc.uri, contenttype1);
        return rdfgraph;
    }

}