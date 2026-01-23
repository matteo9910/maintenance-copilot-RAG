import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Loader2, Cpu, FileText, PanelLeftOpen, ChevronDown, Moon, Sun, ShieldCheck } from 'lucide-react';
import { Message, Reference } from '../types';
import { AI_MODELS } from '../constants';

interface ChatAreaProps {
  messages: Message[];
  isThinking: boolean;
  selectedModel: string;
  onSelectModel: (id: string) => void;
  onSendMessage: (text: string, image?: File) => void;
  onReferenceClick: (ref: Reference) => void;
  onSidebarTrigger: () => void;
  isSidebarOpen: boolean;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onOpenTrustLayer?: (ref: Reference) => void;
}

// Helper function to strip markdown formatting from text
const stripMarkdown = (text: string): string => {
  return text
    // Remove headers (## Header)
    .replace(/^#{1,6}\s+/gm, '')
    // Remove bold (**text** or __text__)
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    // Remove italic (*text* or _text_)
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    // Remove inline code (`code`)
    .replace(/`([^`]+)`/g, '$1')
    // Remove links [text](url) -> text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Remove horizontal rules
    .replace(/^[-*_]{3,}\s*$/gm, '')
    // Clean up extra whitespace
    .replace(/\n{3,}/g, '\n\n')
    .trim();
};

const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isThinking,
  selectedModel,
  onSelectModel,
  onSendMessage,
  onReferenceClick,
  onSidebarTrigger,
  isSidebarOpen,
  theme,
  onToggleTheme,
  onOpenTrustLayer
}) => {
  const [inputValue, setInputValue] = useState('');
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
    }
  }, [inputValue]);

  const activeModelName = AI_MODELS.find(m => m.id === selectedModel)?.name || 'Select Model';

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isThinking]);

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedImage(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleSend = () => {
    if (!inputValue.trim() && !selectedImage) return;
    onSendMessage(inputValue, selectedImage || undefined);
    setInputValue('');
    setSelectedImage(null);
    setPreviewUrl(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <main className="flex-1 flex flex-col relative bg-gray-50 dark:bg-black h-full overflow-hidden transition-colors duration-300">
      
      {/* Top Navigation Bar */}
      <header className="h-14 flex items-center justify-between px-4 py-2 shrink-0 z-20">
        
        {/* Left: Sidebar Trigger & Model Selector */}
        <div className="flex items-center gap-3">
          {!isSidebarOpen && (
            <button 
              onClick={onSidebarTrigger} 
              className="p-2 text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-800 rounded-md transition-colors"
            >
              <PanelLeftOpen className="w-5 h-5" />
            </button>
          )}

          <div className="relative">
            <button 
              onClick={() => setIsModelMenuOpen(!isModelMenuOpen)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white dark:bg-industrial-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all text-sm font-medium text-gray-700 dark:text-gray-200 shadow-sm"
            >
              <span className="w-2 h-2 rounded-full bg-industrial-accent"></span>
              {activeModelName}
              <ChevronDown className="w-3 h-3 text-gray-400" />
            </button>

            {isModelMenuOpen && (
              <div className="absolute top-full left-0 mt-1 w-56 bg-white dark:bg-industrial-900 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl overflow-hidden z-50">
                {AI_MODELS.map(model => (
                  <button
                    key={model.id}
                    disabled={!model.available}
                    onClick={() => {
                      if(model.available) {
                         onSelectModel(model.id);
                         setIsModelMenuOpen(false);
                      }
                    }}
                    className={`w-full text-left px-4 py-2.5 text-sm flex items-center justify-between ${
                      selectedModel === model.id ? 'bg-industrial-subtle dark:bg-industrial-800 text-industrial-accent' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-industrial-800'
                    } ${!model.available && 'opacity-50 cursor-not-allowed'}`}
                  >
                    {model.name}
                    {selectedModel === model.id && <div className="w-1.5 h-1.5 rounded-full bg-industrial-accent"></div>}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Theme Toggle */}
        <button 
          onClick={onToggleTheme}
          className="p-2 rounded-full text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-800 transition-colors"
        >
          {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>
      </header>

      {/* Chat Content */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 sm:px-[10%] lg:px-[15%] py-6 space-y-6 scroll-smooth"
      >
        {messages.length === 0 ? (
          /* Empty State / Welcome Screen */
          <div className="h-full flex flex-col items-center justify-center animate-in fade-in duration-500">
             <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-industrial-accent to-orange-400 flex items-center justify-center mb-6 shadow-glow">
                <Cpu className="w-8 h-8 text-white" />
             </div>
             <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2 text-center">
               How can I help you maintain today?
             </h2>
             <p className="text-gray-500 dark:text-gray-400 text-center max-w-md">
               I'm trained on your technical manuals. I can help you diagnose faults, find parts, and verify safety protocols.
             </p>
          </div>
        ) : (
          /* Chat Messages */
          <>
            {messages.map((msg) => (
              <div 
                key={msg.id} 
                className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'model' && (
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-industrial-accent to-orange-400 flex-shrink-0 flex items-center justify-center mt-1 shadow-md">
                     <Cpu className="w-4 h-4 text-white" />
                  </div>
                )}

                <div className={`max-w-[85%] sm:max-w-[75%]`}>
                  {/* Message Bubble */}
                  <div 
                    className={`px-5 py-3.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap shadow-sm ${
                      msg.role === 'user' 
                        ? 'bg-white dark:bg-industrial-800 border border-gray-100 dark:border-gray-700 text-gray-800 dark:text-gray-100 rounded-tr-sm' 
                        : 'bg-white dark:bg-transparent text-gray-800 dark:text-gray-200'
                    }`}
                  >
                    {/* Attachments */}
                    {msg.attachments?.map((att, idx) => (
                      <div key={idx} className="mb-3 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 inline-block max-w-[200px]">
                        <img src={att.url} alt="User upload" className="w-full h-auto" />
                      </div>
                    ))}

                    <div className="font-sans">{msg.role === 'model' ? stripMarkdown(msg.content) : msg.content}</div>

                    {/* Citations */}
                    {msg.references && msg.references.length > 0 && (
                      <div className="mt-4 flex flex-wrap gap-2">
                        {msg.references.map(ref => (
                          <button
                            key={ref.id}
                            onClick={() => onReferenceClick(ref)}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-industrial-subtle dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 hover:border-industrial-accent rounded-full transition-all group"
                          >
                             <FileText className="w-3 h-3 text-industrial-accent" />
                             <span className="text-xs font-medium text-gray-600 dark:text-gray-300 group-hover:text-industrial-accent">{ref.source}</span>
                          </button>
                        ))}
                      </div>
                    )}

                    {/* Trust Layer Button - shows for AI messages with references */}
                    {msg.role === 'model' && msg.references && msg.references.length > 0 && (
                      <button
                        onClick={() => onOpenTrustLayer?.(msg.references![0])}
                        className="mt-3 flex items-center gap-1.5 text-xs text-industrial-accent hover:text-orange-400 transition-colors"
                      >
                        <ShieldCheck className="w-3.5 h-3.5" />
                        <span className="font-medium">View Trust Layer</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {isThinking && (
              <div className="flex gap-4 justify-start items-center">
                 <div className="w-8 h-8 rounded-full bg-gradient-to-br from-industrial-accent to-orange-400 flex items-center justify-center shadow-md">
                     <Loader2 className="w-4 h-4 text-white animate-spin" />
                 </div>
                 <span className="text-xs text-gray-400 font-medium animate-pulse">Consulting technical data...</span>
              </div>
            )}
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 pb-6 bg-transparent z-10">
        <div className="max-w-3xl mx-auto">
          {previewUrl && (
            <div className="mb-2 inline-flex relative group animate-in slide-in-from-bottom-2 fade-in">
              <img src={previewUrl} alt="Preview" className="h-16 w-auto rounded-lg border border-gray-200 dark:border-gray-700 shadow-md" />
              <button 
                onClick={() => { setSelectedImage(null); setPreviewUrl(null); }}
                className="absolute -top-2 -right-2 bg-gray-800 text-white rounded-full p-0.5 hover:bg-red-500 transition-colors"
              >
                <div className="w-4 h-4 flex items-center justify-center">×</div>
              </button>
            </div>
          )}

          <div className="relative bg-white dark:bg-industrial-800 border border-gray-200 dark:border-gray-700 rounded-2xl shadow-lg dark:shadow-none focus-within:ring-2 focus-within:ring-industrial-accent/50 focus-within:border-industrial-accent transition-all flex items-end p-1.5">

            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-2.5 text-gray-400 hover:text-industrial-accent hover:bg-gray-100 dark:hover:bg-gray-700 rounded-full transition-colors mb-0.5"
              title="Attach File"
            >
              <Paperclip className="w-5 h-5" />
            </button>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleImageSelect}
              className="hidden"
              accept="image/*"
            />

            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about maintenance, diagnostics, or technical issues..."
              className="flex-1 bg-transparent text-gray-800 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 px-2 py-2 text-sm focus:outline-none resize-none overflow-y-auto"
              autoComplete="off"
              rows={1}
              style={{ maxHeight: '150px' }}
            />

            <button
              onClick={handleSend}
              disabled={!inputValue && !selectedImage || isThinking}
              className={`p-2 rounded-full transition-all mb-0.5 ${
                (!inputValue && !selectedImage) || isThinking
                  ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
                  : 'bg-industrial-accent text-white shadow-md hover:bg-orange-600 hover:scale-105 transform'
              }`}
            >
              {isThinking ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5 ml-0.5" />}
            </button>
          </div>
          <div className="mt-2 text-center text-[10px] text-gray-400 dark:text-gray-600">
            AI Copilot uses AI. Check for mistakes.
          </div>
        </div>
      </div>
    </main>
  );
};

export default ChatArea;