import AppExchangeResponse  from "../owlprocessor/AppExchangeResponse";

/**
 * Run tha applicaiton model on the server.
 * @returns A Promise that resolves to the response data.
 */
const API_BASE_URL = process.env.REACT_APP_API_URL || "";

export async function fetchRunModelOnServer(): Promise<any> {
    const fetchRunning = fetch(`${API_BASE_URL}/run_application`, {
       method: "GET",
       headers: {
           "Content-Type": "application/json",
       }
    });
    return fetchRunning.then((response) => {
        if (!response.ok) {
            throw new Error("Failed to fetch running model on the server");
        }
        return response.json();
    });
} 

/**
 * Run tha applicaiton model on the server.
 * @returns A Promise that resolves to the response data.
 */
export async function fetchTerminateAppOnServer(): Promise<any> {
    const fetchTerminating = fetch(`${API_BASE_URL}/stop_application`, {
       method: "GET",
       headers: {
           "Content-Type": "application/json",
       }
    });
    return fetchTerminating.then((response) => {
        if (!response.ok) {
            throw new Error("Failed to fetch running model on the server");
        }
        return response.json();
    });
} 

/**
 * This function initiates the exchange of the application model on the server side.  
 * @returns 
 */
export async function initiateAppExchangeAPI(sentData : any) : Promise<any> {
    const fetchResult = fetch(`${API_BASE_URL}/app_exchange_post`, {
       method: "POST",
       headers: {
           "Content-Type": "application/json",
       },
       body: JSON.stringify(sentData)
    });
    const response = await fetchResult;
    if (!response.ok) {
        throw new Error("Failed to execute the operation with" +
            " the running model on the server");
    }
    // The response is the data that the server sends back is true or false 
    const data:boolean = await response.json();
    return data; 
}

/**
 * This function receives the server data in the exchange with the server side.  
 * @returns 
 */
export async function appExchangeGetAPI() : Promise<any> {
    const fetchResult = fetch(`${API_BASE_URL}/app_exchange_get`, {
       method: "GET",
       headers: {
           "Content-Type": "application/json",
       }
    });
    const response = await fetchResult;
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    const jsonResponse = await response.json();
    const data: AppExchangeResponse =  jsonResponse as AppExchangeResponse;
    return data; 
}