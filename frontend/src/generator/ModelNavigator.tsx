import React, { useState, ChangeEvent } from "react";
import { useAppDispatch, useAppSelector } from "../app/hooks";
import { initiatePreviewModelList, readingListOfServerModels } from "../data/serverModelSlice";
import { previewAppTerminationPane } from "../data/appStateSlice";
import { serialize, Formula } from "rdflib";
import { OUTPUT_KG } from "../owlprocessor/InterfaceOntologyTypes";

// Choose a model to load
export const ModelNavigator: React.FC = () => {

  const dispatch = useAppDispatch();
  //TODO inputModelGraph here from the earlier version
  const inputModelGraph = useAppSelector((store) => store.model.rdfGraph);
  const appRunningOnServer = useAppSelector(
    (state) => state.stateData.runningOnServer
  );
  const outputKnowledgeGraph: String = useAppSelector(
    (store) => store.model.outputGraph
  );
  const isShownTerminationPane = useAppSelector(
    (store) => store.stateData.showAppTerminationPane
  );
  const currentForm = useAppSelector((store) => store.model.currentForm);


  const initiatedLoad = useAppSelector(
    (state) => state.serverInnerModels.previewModelList
  );

  const loadListOfMOdels = () => {
    console.log("Initiating inner models list loading");
    if (appRunningOnServer ) {
      console.log(
        "The current running application has to be terminated in order to proceed."
      );
      if (!isShownTerminationPane)
        dispatch(previewAppTerminationPane());
    } else {
      dispatch(readingListOfServerModels()).then(
        () => dispatch(initiatePreviewModelList())
      );
    }
  };

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

  //TODO is this really necessary?
  const runServerModel = () => {
    console.log("Running server model");
    // dispatch(runInnerAppModelOnServer());
  }



  const previewGraph = (graph: String) => {

    return graph ? graph : "Empty";
  };

  const printState = () => {
    // const link = document.createElement('a');
    // link.href = `output.owl`;
    // document.body.appendChild(link);
    // link.click();
    // document.body.removeChild(link);
    console.log("Serialized output graph:");
    console.log(outputKnowledgeGraph)
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
