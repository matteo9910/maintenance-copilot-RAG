import React, { useState } from 'react';
import { Table, ChevronDown, ChevronUp, FileText, Sparkles } from 'lucide-react';
import { TableData } from '../types';

interface TableDisplayProps {
  tables: TableData[];
  compact?: boolean;
}

/**
 * Parse markdown table into structured data
 */
const parseMarkdownTable = (markdown: string): { headers: string[]; rows: string[][] } => {
  const lines = markdown.trim().split('\n').filter(line => line.trim());

  if (lines.length < 2) {
    return { headers: [], rows: [] };
  }

  // Parse header row
  const headerLine = lines[0];
  const headers = headerLine
    .split('|')
    .map(cell => cell.trim())
    .filter(cell => cell);

  // Skip separator line (index 1)
  // Parse data rows
  const rows: string[][] = [];
  for (let i = 2; i < lines.length; i++) {
    const cells = lines[i]
      .split('|')
      .map(cell => cell.trim())
      .filter(cell => cell);

    if (cells.length > 0) {
      rows.push(cells);
    }
  }

  return { headers, rows };
};

/**
 * Render a single table
 */
const TableRenderer: React.FC<{ table: TableData; isExpanded: boolean; onToggle: () => void }> = ({
  table,
  isExpanded,
  onToggle
}) => {
  const { headers, rows } = parseMarkdownTable(table.markdown);

  // Determine table type badge
  const getTypeBadge = () => {
    switch (table.type) {
      case 'summary':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-industrial-accent/10 text-industrial-accent text-xs font-medium">
            <Sparkles className="w-3 h-3" />
            Summary
          </span>
        );
      case 'source':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-500 text-xs font-medium">
            <FileText className="w-3 h-3" />
            Source
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-industrial-800/50">
      {/* Table Header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-industrial-900/50 hover:bg-gray-100 dark:hover:bg-industrial-800 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Table className="w-4 h-4 text-industrial-accent" />
          <span className="font-medium text-sm text-gray-800 dark:text-gray-200">
            {table.title}
          </span>
          {getTypeBadge()}
        </div>
        <div className="flex items-center gap-2">
          {table.source && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {table.source}{table.page ? `, p.${table.page}` : ''}
            </span>
          )}
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* Table Content */}
      {isExpanded && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-100 dark:bg-industrial-900">
                {headers.map((header, idx) => (
                  <th
                    key={idx}
                    className="px-4 py-2 text-left font-semibold text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700 whitespace-nowrap"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rowIdx) => (
                <tr
                  key={rowIdx}
                  className={`${
                    rowIdx % 2 === 0
                      ? 'bg-white dark:bg-transparent'
                      : 'bg-gray-50 dark:bg-industrial-900/30'
                  } hover:bg-industrial-subtle dark:hover:bg-industrial-800/50 transition-colors`}
                >
                  {row.map((cell, cellIdx) => (
                    <td
                      key={cellIdx}
                      className="px-4 py-2 text-gray-600 dark:text-gray-300 border-b border-gray-100 dark:border-gray-800 whitespace-nowrap"
                    >
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && (
            <div className="px-4 py-6 text-center text-gray-500 dark:text-gray-400 text-sm">
              No data available
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * TableDisplay Component
 *
 * Renders a list of tables extracted from the RAG response.
 * Tables can be expanded/collapsed and show their source.
 */
const TableDisplay: React.FC<TableDisplayProps> = ({ tables, compact = false }) => {
  const [expandedTables, setExpandedTables] = useState<Set<string>>(
    // Auto-expand summary tables and first table
    new Set(tables.filter(t => t.type === 'summary').map(t => t.id).concat(tables[0]?.id || []))
  );

  const toggleTable = (tableId: string) => {
    setExpandedTables(prev => {
      const next = new Set(prev);
      if (next.has(tableId)) {
        next.delete(tableId);
      } else {
        next.add(tableId);
      }
      return next;
    });
  };

  if (!tables || tables.length === 0) {
    return null;
  }

  return (
    <div className={`${compact ? 'space-y-2' : 'space-y-3 mt-4'}`}>
      {!compact && tables.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <Table className="w-3.5 h-3.5" />
          <span>{tables.length} table{tables.length > 1 ? 's' : ''} found</span>
        </div>
      )}
      {tables.map(table => (
        <TableRenderer
          key={table.id}
          table={table}
          isExpanded={expandedTables.has(table.id)}
          onToggle={() => toggleTable(table.id)}
        />
      ))}
    </div>
  );
};

export default TableDisplay;
