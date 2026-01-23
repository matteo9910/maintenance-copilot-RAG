import React from 'react';
import { Search, Plus, PanelLeftClose, User, MessageSquare } from 'lucide-react';
import { ChatSession } from '../types';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onNewChat: () => void;
  chatSessions?: ChatSession[];
  currentSessionId?: string | null;
  onSelectSession?: (sessionId: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  onNewChat,
  chatSessions = [],
  currentSessionId,
  onSelectSession
}) => {
  return (
    <aside 
      className={`
        bg-white dark:bg-industrial-900 border-r border-gray-200 dark:border-industrial-800 
        flex flex-col h-full z-40 shadow-xl md:shadow-none
        fixed inset-y-0 left-0 w-72 transition-transform duration-300 ease-in-out
        md:static md:translate-x-0
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        ${!isOpen && 'md:hidden'} 
      `}
    >
      {/* Header */}
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
           <div className="w-8 h-8 rounded-lg bg-industrial-accent text-white flex items-center justify-center font-bold">
             MC
           </div>
           <span className="font-bold text-gray-800 dark:text-gray-100 tracking-tight">Maintenance Copilot</span>
        </div>
        <button 
          onClick={onClose}
          className="p-1.5 rounded-md text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          title="Close Sidebar"
        >
          <PanelLeftClose className="w-5 h-5" />
        </button>
      </div>

      <div className="px-4 mb-2">
         {/* New Chat Button */}
         <button 
           onClick={onNewChat}
           className="w-full py-2.5 px-4 bg-industrial-subtle dark:bg-industrial-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-industrial-accent font-medium rounded-lg flex items-center justify-center gap-2 transition-all mb-4 border border-transparent hover:border-industrial-accent/20"
         >
            <Plus className="w-4 h-4" />
            New Chat
         </button>

         {/* Search Bar */}
         <div className="relative group">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400 group-focus-within:text-industrial-accent" />
            <input 
              type="text" 
              placeholder="Search by error, tag..." 
              className="w-full pl-9 pr-3 py-2 bg-gray-50 dark:bg-black/20 border border-gray-200 dark:border-gray-800 rounded-lg text-sm text-gray-700 dark:text-gray-300 focus:outline-none focus:ring-1 focus:ring-industrial-accent placeholder-gray-400"
            />
         </div>
      </div>

      {/* History List */}
      <div className="flex-1 overflow-y-auto px-4 py-2">
        {chatSessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <MessageSquare className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
            <p className="text-sm text-gray-400 dark:text-gray-500">No chat history yet</p>
            <p className="text-xs text-gray-300 dark:text-gray-600 mt-1">Start a new conversation</p>
          </div>
        ) : (
          <div className="space-y-1">
            <h3 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2 px-2">
              Recent Chats
            </h3>
            {chatSessions.map(session => (
              <button
                key={session.id}
                onClick={() => onSelectSession?.(session.id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all truncate flex items-center gap-2 ${
                  currentSessionId === session.id
                    ? 'bg-industrial-accent/10 text-industrial-accent border border-industrial-accent/20'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-200'
                }`}
              >
                <MessageSquare className="w-4 h-4 shrink-0" />
                <span className="truncate">{session.title}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* User Footer */}
      <div className="p-4 border-t border-gray-200 dark:border-industrial-800">
        <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-industrial-800 cursor-pointer transition-colors">
          <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 flex items-center justify-center text-white shadow-md">
             <User className="w-5 h-5" />
          </div>
          <div className="flex flex-col overflow-hidden">
             <span className="text-sm font-semibold text-gray-800 dark:text-white truncate">Senior Tech</span>
             <span className="text-[10px] text-gray-500 dark:text-gray-400 truncate">tech.lead@factory.com</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;