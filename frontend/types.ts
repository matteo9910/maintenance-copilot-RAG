export interface Reference {
  id: string;
  title: string;
  source: string;
  page?: string;
  chapter?: string;
  section?: string;
  chunkIndex?: number;
  totalChunks?: number;
  imageUrl?: string;
  description?: string;
  fullContent?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'model';
  content: string;
  timestamp: Date;
  attachments?: {
    type: 'image';
    url: string;
    base64?: string;
  }[];
  isThinking?: boolean;
  references?: Reference[];
}

export interface ModelOption {
  id: string;
  name: string;
  provider: string;
  description: string;
  available: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  date: string;
  status: 'active' | 'resolved' | 'archived';
}
