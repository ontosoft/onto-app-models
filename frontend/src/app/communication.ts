import {z} from "zod"


export const AppExchangeBackendGetSchema = z.object({
    message_type: z.string(),
    layout_type: z.string(),
    message_content: z.any(),
    output_knowledge_graph: z.string()
});

export type AppExchangeBackendGet = z.infer<typeof AppExchangeBackendGetSchema>

//TODO This validation can be considered

export interface AppModelData {
    filename: string; 
    model: string; 
    description: string; 
    filepath: string 
  }