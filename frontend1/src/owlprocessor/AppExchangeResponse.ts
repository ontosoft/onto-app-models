
export default interface AppExchangeResponse {
    message_type: string;
    layout_type: string;
    message_content: any; // Adjust the type based on the actual structure of your data
    output_knowledge_graph: string; // Optional, adjust as needed
}
