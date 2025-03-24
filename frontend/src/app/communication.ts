import {z} from "zod"


export const AppExchangeBackendGetSchema = z.object({
    message_type: z.string(),
    layout_type: z.string(),
    message_content: z.any()
});

export type AppExchangeBackendGet = z.infer<typeof AppExchangeBackendGetSchema>

//TODO This validation can be considered

export interface AppModelData {
    filename: string; 
    model: string; 
    description: string; 
    filepath: string 
  }