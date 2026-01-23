import { GoogleGenAI, GenerateContentResponse } from "@google/genai";
import { Message } from "../types";

const API_KEY = process.env.API_KEY || '';

// Initialize client
const ai = new GoogleGenAI({ apiKey: API_KEY });

/**
 * Sends a message to the Gemini API, supporting both text and image inputs.
 */
export const sendMessageToGemini = async (
  modelId: string,
  prompt: string,
  imageBase64?: string
): Promise<string> => {
  try {
    const parts: any[] = [];
    
    // Add image if present
    if (imageBase64) {
      // Remove data URL prefix if present for clean base64
      const base64Data = imageBase64.split(',')[1] || imageBase64;
      
      parts.push({
        inlineData: {
          mimeType: 'image/jpeg', // Assuming JPEG for simplicity in this demo
          data: base64Data
        }
      });
    }

    // Add text prompt
    parts.push({ text: prompt });

    // Use specific Gemini logic
    const response: GenerateContentResponse = await ai.models.generateContent({
      model: modelId,
      contents: {
        role: 'user',
        parts: parts
      },
      config: {
        // Simulating a technical persona via system instruction is done via config in 0.0.1+ SDKs
        // adhering to guidelines, though typically best passed as systemInstruction if supported
        systemInstruction: `You are an expert Industrial Maintenance AI Copilot. 
        Your tone is professional, technical, and concise. 
        Use technical jargon appropriate for mechanical and electrical engineering. 
        Format your response with Markdown. 
        If an image is provided, analyze the potential fault, identify components, and suggest a repair procedure.
        Structure answers with: "Diagnosis", "Probable Cause", and "Action Plan".`
      }
    });

    return response.text || "Analysis complete. No text output generated.";

  } catch (error) {
    console.error("Gemini API Error:", error);
    return "SYSTEM ERROR: Connection to AI Core failed. Please verify API key and network status.";
  }
};
