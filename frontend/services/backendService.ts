/**
 * Backend API Service
 * Connects the frontend to the FastAPI RAG backend
 */

const BACKEND_URL = 'http://localhost:8000';

interface SourceDocument {
  content: string;
  source: string;
  page?: number;
  chapter?: string;
  section?: string;
  chunk_index?: number;
  total_chunks?: number;
  relevance_score?: number;
}

interface ChatResponse {
  answer: string;
  sources: SourceDocument[];
  conversation_id: string;
  model_used: string;
}

interface HealthResponse {
  status: string;
  version: string;
  components: {
    api: string;
    vector_store: {
      status: string;
      documents_indexed: number;
    };
    llm_provider: string;
  };
  available_models: string[];
}

interface MessageHistory {
  role: 'user' | 'assistant';
  content: string;
}

/**
 * Check backend health status
 */
export const checkHealth = async (): Promise<HealthResponse> => {
  const response = await fetch(`${BACKEND_URL}/api/health`);
  if (!response.ok) {
    throw new Error('Backend not available');
  }
  return response.json();
};

/**
 * Send a message to the RAG backend
 */
export const sendMessageToBackend = async (
  query: string,
  modelId: string,
  history: MessageHistory[] = [],
  imageBase64?: string
): Promise<ChatResponse> => {
  try {
    const response = await fetch(`${BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        model: modelId,
        history: history.map(msg => ({
          role: msg.role === 'user' ? 'user' : 'assistant',
          content: msg.content
        })),
        image: imageBase64
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get response');
    }

    return response.json();
  } catch (error) {
    console.error('Backend API Error:', error);
    throw error;
  }
};

/**
 * Get available models from backend
 */
export const getAvailableModels = async (): Promise<{ id: string; name: string }[]> => {
  const response = await fetch(`${BACKEND_URL}/api/models`);
  if (!response.ok) {
    throw new Error('Failed to fetch models');
  }
  const data = await response.json();
  return data.models;
};

/**
 * Get indexed documents from backend
 */
export const getDocuments = async () => {
  const response = await fetch(`${BACKEND_URL}/api/documents`);
  if (!response.ok) {
    throw new Error('Failed to fetch documents');
  }
  return response.json();
};
