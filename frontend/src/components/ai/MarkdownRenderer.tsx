"use client";

import React from "react";

function parseMarkdown(text: string): React.ReactNode[] {
  if (!text) return [""];
  const nodes: React.ReactNode[] = [];
  const lines = text.split("\n");
  let i = 0;
  let listItems: React.ReactNode[] = [];
  let orderedListItems: React.ReactNode[] = [];

  const flushList = () => {
    if (listItems.length > 0) {
      nodes.push(<ul key={`ul-${nodes.length}`} className="list-disc pl-5 space-y-1 my-2">{listItems}</ul>);
      listItems = [];
    }
    if (orderedListItems.length > 0) {
      nodes.push(<ol key={`ol-${nodes.length}`} className="list-decimal pl-5 space-y-1 my-2">{orderedListItems}</ol>);
      orderedListItems = [];
    }
  };

  while (i < lines.length) {
    const line = lines[i];

    // Code blocks (```)
    if (line.startsWith("```")) {
      flushList();
      let language = line.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      nodes.push(
        <pre key={`pre-${nodes.length}`} className="bg-slate-800 text-zinc-200 rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono leading-relaxed">
          {language && <div className="text-[10px] text-zinc-500 uppercase tracking-wider mb-1.5">{language}</div>}
          <code>{codeLines.join("\n")}</code>
        </pre>
      );
      continue;
    }

    // Unordered list items
    if (/^[\s]*[-*+]\s+/.test(line)) {
      flushList();
      const trimmed = line.replace(/^[\s]*[-*+]\s+/, "");
      listItems.push(<li key={`li-${nodes.length}-${listItems.length}`} className="text-xs text-zinc-200">{renderInline(trimmed)}</li>);
      i++;
      continue;
    }

    // Ordered list items
    if (/^[\s]*\d+\.\s+/.test(line)) {
      flushList();
      const trimmed = line.replace(/^[\s]*\d+\.\s+/, "");
      orderedListItems.push(<li key={`oli-${nodes.length}-${orderedListItems.length}`} className="text-xs text-zinc-200">{renderInline(trimmed)}</li>);
      i++;
      continue;
    }

    // Empty line flushes lists
    if (line.trim() === "") {
      flushList();
      nodes.push(<br key={`br-${nodes.length}`} />);
      i++;
      continue;
    }

    // Headings
    if (line.startsWith("### ")) {
      flushList();
      nodes.push(<h4 key={`h-${nodes.length}`} className="text-sm font-bold text-zinc-100 mt-3 mb-1">{renderInline(line.slice(4))}</h4>);
      i++;
      continue;
    }
    if (line.startsWith("## ")) {
      flushList();
      nodes.push(<h3 key={`h-${nodes.length}`} className="text-base font-bold text-zinc-100 mt-3 mb-1">{renderInline(line.slice(3))}</h3>);
      i++;
      continue;
    }
    if (line.startsWith("# ")) {
      flushList();
      nodes.push(<h2 key={`h-${nodes.length}`} className="text-lg font-bold text-zinc-100 mt-3 mb-1">{renderInline(line.slice(2))}</h2>);
      i++;
      continue;
    }

    // Paragraphs
    flushList();
    nodes.push(<p key={`p-${nodes.length}`} className="text-xs leading-relaxed my-1">{renderInline(line)}</p>);
    i++;
  }
  flushList();

  return nodes.length === 0 ? [text] : nodes;
}

function renderInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  // Match **bold**, *italic*, `inline code`, and [links](url)
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    if (match[2] !== undefined) {
      parts.push(<strong key={`b-${parts.length}`} className="font-bold">{match[2]}</strong>);
    } else if (match[3] !== undefined) {
      parts.push(<em key={`i-${parts.length}`} className="italic">{match[3]}</em>);
    } else if (match[4] !== undefined) {
      parts.push(<code key={`c-${parts.length}`} className="bg-slate-800 text-violet-300 px-1.5 py-0.5 rounded text-[11px] font-mono">{match[4]}</code>);
    } else if (match[5] !== undefined && match[6] !== undefined) {
      parts.push(<a key={`a-${parts.length}`} href={match[6]} target="_blank" rel="noopener noreferrer" className="text-violet-400 underline hover:text-violet-300">{match[5]}</a>);
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts.length === 0 ? [text] : parts;
}

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  if (!content) return null;
  return <div className={`markdown-body ${className}`}>{parseMarkdown(content)}</div>;
}
