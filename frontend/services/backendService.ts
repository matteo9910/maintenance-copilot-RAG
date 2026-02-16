/**
 * Backend API Service
 * Connects the frontend to the FastAPI RAG backend
 *
 * Features:
 * - Standard chat endpoint
 * - Streaming chat endpoint (SSE) for reduced latency
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
  images?: string[];
}

interface ChatResponse {
  answer: string;
  sources: SourceDocument[];
  conversation_id: string;
  model_used: string;
}

interface RAGMetadata {
  mode: string;
  iterations: number;
  queries_executed: string[];
}

// Status update during processing
export interface StatusUpdate {
  step: 'analyzing' | 'expanding' | 'searching' | 'processing' | 'generating';
  message: string;
  query?: string;
  index?: number;
  total?: number;
}

// Callbacks for streaming
interface StreamCallbacks {
  onToken: (token: string) => void;
  onSources: (sources: SourceDocument[]) => void;
  onMetadata: (metadata: RAGMetadata) => void;
  onStatus?: (status: StatusUpdate) => void;
  onDone: () => void;
  onError: (error: Error) => void;
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
 * Send a message with streaming response (SSE)
 * This shows the response as it's being generated, reducing perceived latency
 */
export const sendMessageStreaming = async (
  query: string,
  modelId: string,
  history: MessageHistory[] = [],
  callbacks: StreamCallbacks
): Promise<void> => {
  try {
    const response = await fetch(`${BACKEND_URL}/api/chat/stream`, {
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
        }))
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to get streaming response');
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      let currentEvent = '';
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          const data = line.slice(6);

          try {
            if (currentEvent === 'status') {
              const status = JSON.parse(data);
              callbacks.onStatus?.(status);
            } else if (currentEvent === 'token') {
              const parsed = JSON.parse(data);
              callbacks.onToken(parsed.token);
            } else if (currentEvent === 'sources') {
              const sources = JSON.parse(data);
              callbacks.onSources(sources);
            } else if (currentEvent === 'metadata') {
              const metadata = JSON.parse(data);
              callbacks.onMetadata(metadata);
            } else if (currentEvent === 'done') {
              callbacks.onDone();
            }
          } catch (parseError) {
            console.warn('Failed to parse SSE data:', data);
          }
        }
      }
    }

  } catch (error) {
    console.error('Streaming API Error:', error);
    callbacks.onError(error instanceof Error ? error : new Error('Unknown error'));
    throw error;
  }
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
