import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import ContextPanel from './components/ContextPanel';
import { Message, Reference, ChatSession } from './types';
import { AI_MODELS } from './constants';
import { sendMessageToBackend, checkHealth } from './services/backendService';

// Helper to extract title from first query (max 40 chars)
const extractTitle = (query: string): string => {
  const cleaned = query.trim().replace(/\s+/g, ' ');
  if (cleaned.length <= 40) return cleaned;
  return cleaned.substring(0, 37) + '...';
};

const App: React.FC = () => {
  const [selectedModel, setSelectedModel] = useState(AI_MODELS[0].id);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [activeReference, setActiveReference] = useState<Reference | null>(null);
  const [isContextPanelOpen, setIsContextPanelOpen] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'online' | 'offline' | 'checking'>('checking');

  // Sidebar state: open by default on desktop
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Theme state
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');

  // Chat sessions state
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sessionsMessages, setSessionsMessages] = useState<Record<string, Message[]>>({});

  // Check backend health on mount
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await checkHealth();
        setBackendStatus('online');
      } catch {
        setBackendStatus('offline');
      }
    };
    checkBackend();
    // Re-check every 30 seconds
    const interval = setInterval(checkBackend, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Apply theme class to html element
    const html = document.documentElement;
    if (theme === 'dark') {
      html.classList.add('dark');
    } else {
      html.classList.remove('dark');
    }
  }, [theme]);

  // Helper to convert file to base64 for API
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = error => reject(error);
    });
  };

  // Convert messages to history format for API
  const getMessageHistory = () => {
    return messages.map(msg => ({
      role: msg.role === 'user' ? 'user' as const : 'assistant' as const,
      content: msg.content
    }));
  };

  const handleSendMessage = async (text: string, image?: File) => {
    // Check if this is the first message (create new session)
    const isFirstMessage = messages.length === 0;
    let sessionId = currentSessionId;

    if (isFirstMessage) {
      // Create new session
      sessionId = Date.now().toString();
      const newSession: ChatSession = {
        id: sessionId,
        title: extractTitle(text),
        date: new Date().toISOString().split('T')[0],
        status: 'active'
      };
      setChatSessions(prev => [newSession, ...prev]);
      setCurrentSessionId(sessionId);
    }

    // 1. Create User Message
    const newUserMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date(),
      attachments: image ? [{
        type: 'image',
        url: URL.createObjectURL(image)
      }] : undefined
    };

    setMessages(prev => [...prev, newUserMessage]);

    // Update sessions messages
    if (sessionId) {
      setSessionsMessages(prev => ({
        ...prev,
        [sessionId]: [...(prev[sessionId] || []), newUserMessage]
      }));
    }

    setIsThinking(true);

    try {
      // 2. Prepare Payload
      let imageBase64: string | undefined = undefined;
      if (image) {
        const fullBase64 = await fileToBase64(image);
        imageBase64 = fullBase64.split(',')[1]; // Remove data URL prefix
      }

      // 3. Call Backend RAG API
      const response = await sendMessageToBackend(
        text,
        selectedModel,
        getMessageHistory(),
        imageBase64
      );

      // 4. Convert backend sources to References with extended metadata
      const references: Reference[] = response.sources.map((source: any, index: number) => ({
        id: `ref-${Date.now()}-${index}`,
        title: source.source,
        source: source.source,
        page: source.page ? `Page ${source.page}` : undefined,
        chapter: source.chapter,
        section: source.section,
        chunkIndex: source.chunk_index,
        totalChunks: source.total_chunks,
        description: source.content.substring(0, 300) + '...',
        fullContent: source.content
      }));

      // 5. Create AI Response
      const newAiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'model',
        content: response.answer,
        timestamp: new Date(),
        references: references.length > 0 ? references : undefined
      };

      setMessages(prev => [...prev, newAiMessage]);

      // Update sessions messages with AI response
      if (sessionId) {
        setSessionsMessages(prev => ({
          ...prev,
          [sessionId]: [...(prev[sessionId] || []), newAiMessage]
        }));
      }

      // 6. Show context panel if we have references
      if (references.length > 0) {
        setActiveReference(references[0]);
        setIsContextPanelOpen(true);
      }

    } catch (error) {
      console.error(error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'model',
        content: backendStatus === 'offline'
          ? "SYSTEM ERROR: Backend RAG service is offline. Please ensure the FastAPI server is running on port 8000."
          : "CRITICAL FAILURE: Unable to process diagnostic request. Please check the connection.",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsThinking(false);
    }
  };

  const handleReferenceClick = (ref: Reference) => {
    setActiveReference(ref);
    setIsContextPanelOpen(true);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden font-sans selection:bg-industrial-accent selection:text-white">
      {/* 1. Left Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        onNewChat={() => {
          setMessages([]);
          setCurrentSessionId(null);
          setActiveReference(null);
          setIsContextPanelOpen(false);
        }}
        chatSessions={chatSessions}
        currentSessionId={currentSessionId}
        onSelectSession={(sessionId) => {
          setCurrentSessionId(sessionId);
          setMessages(sessionsMessages[sessionId] || []);
          setActiveReference(null);
          setIsContextPanelOpen(false);
        }}
      />

      {/* 2. Main Content Area */}
      <div className="flex-1 flex relative flex-col min-w-0">
        <ChatArea
          messages={messages}
          isThinking={isThinking}
          selectedModel={selectedModel}
          onSelectModel={setSelectedModel}
          onSendMessage={handleSendMessage}
          onReferenceClick={handleReferenceClick}
          onSidebarTrigger={() => setIsSidebarOpen(true)}
          isSidebarOpen={isSidebarOpen}
          theme={theme}
          onToggleTheme={() => setTheme(prev => prev === 'dark' ? 'light' : 'dark')}
          onOpenTrustLayer={(ref) => {
            setActiveReference(ref);
            setIsContextPanelOpen(true);
          }}
        />

        {/* 3. Context Panel (Right) */}
        {isContextPanelOpen && (
          <ContextPanel
            reference={activeReference}
            isOpen={isContextPanelOpen}
            onClose={() => setIsContextPanelOpen(false)}
          />
        )}
      </div>
    </div>
  );
};

export default App;
