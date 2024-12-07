
# Frontend documentation 




### Behaviour of React useEffect 

One of imprtant features this application is to be synchronized with the current state of the application in the backend. To this end, the React rendering leveraged "Effect" functionality. The frontend application screen presents to the user current application layout, and that current layout depends on the current state of the running application on the server. It is simmilar to a chatbot application which is updated (synchronized) according to what data is gathered from the server. For this synchronization is used the React's Effects functionality, which enables the application to synchronize with the external system (current layout sent from our server API).  
On the other hand, for individual clicks that trigger events are used plain functions. 

## MainApplicationPane
MainApplicationPane is a React component that includes all rendering pertaining to the running application. Additionally, it encompasses other user interface elements like a list for the model selection and subsequently running the selected model.    

### ApplicationState
The frontend application has also a state that  processor.

