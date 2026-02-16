import React, { useState } from 'react';
import { FileText, ExternalLink, ShieldCheck, X, BookOpen, Hash, Layers } from 'lucide-react';
import { Reference } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ContextPanelProps {
  reference: Reference | null;
  isOpen: boolean;
  onClose: () => void;
}

const ContextPanel: React.FC<ContextPanelProps> = ({ reference, isOpen, onClose }) => {
  const [showFullContent, setShowFullContent] = useState(false);

  if (!isOpen) return null;

  // Build location string
  const buildLocationInfo = () => {
    const parts: string[] = [];
    if (reference?.page) parts.push(reference.page);
    if (reference?.chapter) parts.push(`Chapter: ${reference.chapter}`);
    if (reference?.section) parts.push(`Section: ${reference.section}`);
    if (reference?.chunkIndex && reference?.totalChunks) {
      parts.push(`Segment ${reference.chunkIndex}/${reference.totalChunks}`);
    }
    return parts;
  };

  const locationParts = reference ? buildLocationInfo() : [];

  return (
    <aside className="w-full md:w-[450px] bg-industrial-900 border-l border-industrial-800 flex flex-col h-full absolute right-0 top-0 bottom-0 z-50 md:z-30 shadow-2xl animate-in slide-in-from-right duration-300">

      {/* Header */}
      <div className="h-14 border-b border-industrial-800 flex items-center justify-between px-4 bg-industrial-800/20 backdrop-blur-sm">
        <div className="flex items-center gap-2 text-industrial-accent">
          <ShieldCheck className="w-4 h-4" />
          <span className="text-xs font-mono font-bold tracking-widest uppercase">Trust Layer</span>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-white p-2">
          <X className="w-5 h-5" />
        </button>
      </div>

      {reference ? (
        <div className="flex-1 overflow-y-auto p-0">
           {/* Document Preview Header */}
           <div className="p-5 bg-gradient-to-b from-gray-900 to-black">
              <div className="inline-block px-2 py-0.5 rounded border border-blue-500/30 bg-blue-500/10 text-blue-400 text-[10px] font-mono mb-3">
                VERIFIED SOURCE
              </div>
              <h3 className="text-base font-bold text-white mb-2 leading-snug">{reference.title}</h3>

              {/* Document Location Info */}
              <div className="space-y-1.5 mt-3">
                <div className="flex items-center gap-2 text-gray-400 text-xs">
                  <FileText className="w-3.5 h-3.5 text-industrial-accent shrink-0" />
                  <span className="truncate">{reference.source}</span>
                </div>

                {locationParts.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {locationParts.map((part, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded bg-gray-800/50 text-[10px] text-gray-400 font-mono"
                      >
                        {part.includes('Page') && <BookOpen className="w-3 h-3" />}
                        {part.includes('Chapter') && <Hash className="w-3 h-3" />}
                        {part.includes('Segment') && <Layers className="w-3 h-3" />}
                        {part}
                      </span>
                    ))}
                  </div>
                )}
              </div>
           </div>

           {/* Document Link */}
           <div className="border-y border-industrial-800 bg-gray-900/50 py-4 px-4 flex items-center gap-3">
              <FileText className="w-8 h-8 text-industrial-accent" />
              <div>
                <a
                  href={`${API_URL}/api/pdfs/${encodeURIComponent(reference?.source || '')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-industrial-accent font-medium hover:text-orange-400 hover:underline cursor-pointer transition-colors"
                >
                  {reference?.source || 'PDF Document'}
                </a>
                <p className="text-[10px] text-gray-600">Click to open source document</p>
              </div>
           </div>

           {/* Extracted Content Section */}
           <div className="p-5">
             <div className="flex items-center justify-between mb-3">
               <h4 className="text-xs font-mono text-gray-500 uppercase tracking-widest">Extracted Content</h4>
               {reference.fullContent && reference.fullContent.length > 300 && (
                 <button
                   onClick={() => setShowFullContent(!showFullContent)}
                   className="text-[10px] text-industrial-accent hover:text-orange-400 font-medium"
                 >
                   {showFullContent ? 'Show Less' : 'Show More'}
                 </button>
               )}
             </div>

             <div className="p-4 bg-gray-800/30 rounded-lg border-l-2 border-industrial-accent text-sm text-gray-300 leading-relaxed max-h-[400px] overflow-y-auto">
                <p className="whitespace-pre-wrap font-mono text-xs">
                  {showFullContent && reference.fullContent
                    ? reference.fullContent
                    : reference.description}
                </p>
             </div>

             {/* Confidence indicator */}
             <div className="mt-4 p-3 bg-green-900/20 border border-green-800/30 rounded-lg">
               <div className="flex items-center gap-2">
                 <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                 <span className="text-[10px] font-mono text-green-400 uppercase tracking-wider">
                   Source Verified
                 </span>
               </div>
               <p className="text-[10px] text-gray-500 mt-1">
                 Content extracted from indexed technical documentation
               </p>
             </div>

             <a
               href={`${API_URL}/api/pdfs/${encodeURIComponent(reference?.source || '')}`}
               target="_blank"
               rel="noopener noreferrer"
               className="w-full mt-4 py-2.5 border border-gray-700 hover:border-industrial-accent text-gray-400 hover:text-industrial-accent text-xs font-mono uppercase tracking-wider flex items-center justify-center gap-2 transition-all rounded"
             >
               <ExternalLink className="w-3 h-3" /> Open Source Document
             </a>
           </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center opacity-30">
          <FileText className="w-16 h-16 text-gray-500 mb-4" />
          <h3 className="text-lg font-bold text-gray-400">No Context Active</h3>
          <p className="text-sm text-gray-600 mt-2 max-w-[200px]">
            Select a citation in the chat stream to view technical evidence.
          </p>
        </div>
      )}
    </aside>
  );
};

export default ContextPanel;