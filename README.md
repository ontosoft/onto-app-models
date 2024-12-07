# Onto Application Models - Documentation
This project is an implementation of the approach that combines data and the functionality to collect that data in knowledge graphs. The approach includes an implementation of the application generator that creates web-applications which collect data, i.e., generate knowledge graphs according to specified SHACL models. 

## Architecture

The project consists of two parts. The first one is the backend that processes the majority of functions and the second is the frontend that previews the GUI of the application. Models are written in the form of rdf knowledge graphs. The backend has a mechanism to keep state of the application and to execute functions according to the program specification in model files. The division of the project in frontend and backend is also caused by the fact that the libraries for working with rdf graphs implemented in JavaScript are not as well-developed as those using Python programming language. 

### Backend
The backend is implemented using the Python programming language with the FastAPI framework and the uvicorn server. It includes three routes:

 1. /run_application - a REST api address for the first communication with the system.  

 2. /upload_rdf_file - a route to upload a model RDF file

 3. /get_current_ui_page - this is the URI for exchanging data with the backend when the model is read and the app is running.  


 ### Frontend

 The frontend part is the place where the user interface is presented to users according to the specification in the model.

 ## Model 

 An application model which is stored as a knowledge graph in the rdf file is read in the internal representation. In the backend 

 ## One simple use case

 After you run the application generator (OntoUI environment), you can click on "List server models" button to retrieve all application models which are currently stored internally.  

 One of the listed application models (RDF graphs) should be loaded and in the next step the application is run. After that the right pannel of the OntoUI screen is reserved for the generated application interface.  