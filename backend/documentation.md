
# Backend information

The routes/onto_app_router.py file contains the access points to the backend, and here can be found API functions connecting points. 
The ontology/obop.owl file contain our modeling ontology and the folder app_models is used to store application models.  

## Owlprocessor modul 
The modul owlprocessor (knowledge graph processor) contains the core of the application functionality. It includes classes that store application models and describe functionalities of corresponding model actions.  
The first class that is instantiated when the applications starts is the App class which is located in the owlprocessor/app.py file.

File backend/owlprocessor/app_model.py holds inner repressentation of the model, e.i. class AppInternalModel. 

### AppInternalModel 
The AppInternalModel class stores inner representation of application information. It includes the list of application forms and other static components (e.g. UI components) and the list of actions which are executed for corresponding application events.

Every application contains a first layout (form) when the application starts an execution. The specification of this "first form" is stored in the data attribute called "startingFormBlock". 
The objects of the class AppInternalModel are used as a reference point when the application is run. 

### UIModelFactory
This is a class that inclues functions that read knowledge graphs and make instances of the AppInternalModel class (internal app models). 

File (owlprocessor/app_interaction_model.py) contains actual functionality for the application interaction. It includes the AppInteractionModel class that generates new form screen.

## AppInteractionModel
This class contains functionalities which are relevant for the actual application execution. The generateLayout method is a function responsible for sending data (json documentss) to the frontend. That json documents are necessary information to show a new screen to the user. 
If one application is running then it has an instance of the  localAppInteractionModelInstance. This can be seen in the 
run_application() method of the onto_app_router.py file that checks whether this object exists. 

The AppInteractionModel class relies on ApplicationState objects that keep track of the application state.

### ApplicationState
To keep track of the application state represensts one of the most challenging tasks to the application processor.

