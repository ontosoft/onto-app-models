import React, { useState, ChangeEvent } from "react";
import { useAppDispatch, useAppSelector } from "../app/hooks";
import { transformGraphToInnerTemplate, prepareFormData,
} from "../data/modelSlice";
import { initiateInnerModelsListLoading } from "../data/serverModelSlice";
import { serialize, Formula } from "rdflib";
import { OUTPUT_KG } from "../owlprocessor/InterfaceOntologyTypes";
//This file is loaded from the public directory
const fileName = "../models/restaurant-model-ttl.ttl";

// Choose a model to load
export const ModelNavigator: React.FC = () => {
  const dispatch = useAppDispatch();
  const inputModelGraph = useAppSelector((store) => store.model.rdfGraph);
  const outputKnowledgeGraph = useAppSelector(
    (store) => store.model.outputGraph
  );
  const currentForm = useAppSelector((store) => store.model.currentForm);

  const processQuery = () => {
    //Initiation of RDF graph transformation to inner representation
    dispatch(transformGraphToInnerTemplate());
    //Preparing the first form in application
    dispatch(prepareFormData("-1"));
//    dispatch(initiateRunningOnServer());
    console.log("Current form:");
    console.log(currentForm);
  };

  const initiatedLoad = useAppSelector(
    (state) => state.serverInnerModels.initiedModelListLoading
  );

  const loadListOfMOdels = () => {
    console.log("Initiating inner models list loading")
    dispatch(initiateInnerModelsListLoading())
    console.log(initiatedLoad)
  }  

  // Selecting an RDF file to upload
  const [selectedRDFFile, setSelectedFile] = useState<File | null>(null);
  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setSelectedFile(event.target.files ? event.target.files[0] : null);
  };

  // Uploading the selected RDF file to the server
  const handleUpload = async () => {
    if (!selectedRDFFile) {
      console.error("No RDF file selected");
      return;
    }
    const formData = new FormData();
    formData.append("file", selectedRDFFile);

    const response = await fetch("http://localhost:8089/upload_rdf_file", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      console.error("Upload failed");
      return;
    }

    console.log("Upload successful");
  };

  const readCurrentModelPage = async () => {
    fetch("http://localhost:8089/read_current_model_page").then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    });
  };


  const runServerModel = () => {
    //Initiation of RDF graph transformation to inner representation
    dispatch(transformGraphToInnerTemplate());
    //Preparing the first form in application
    dispatch(prepareFormData("-1"));
 //   dispatch(initiateRunningOnServer());
    console.log("Current form:");
    console.log(currentForm);
  };

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
    <div className="col-2" id="dashboard">
      <div className="row">
        <button className="btn btn-primary m-2" onClick={loadListOfMOdels}>
          List server models
        </button>
      </div>
      <div className="row">
        <input type="file" onChange={handleFileChange} />
        <button className="btn btn-primary m-2" onClick={handleUpload}>
          Upload model to server
        </button>
      </div>
      <div className="row">
        <button className="btn btn-primary m-2" onClick={processQuery}>
          Run model
        </button>
      </div>

      <div className="row">
        <button className="btn btn-primary m-2" onClick={runServerModel}>
          Run server model
        </button>
      </div>
      <div className="row">
        <button className="btn btn-secondary m-2" onClick={printState}>
          Export output file
        </button>
      </div>
    </div>
  );
};
