"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
  if (!content) return null;

  return (
    <div className={`markdown-body prose prose-sm max-w-none dark:prose-invert ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className: codeClass, children, ...props }) {
            const match = /language-(\w+)/.exec(codeClass || "");
            const isInline = !match && !String(children).includes("\n");
            if (isInline) {
              return (
                <code className="bg-muted text-primary px-1.5 py-0.5 rounded text-[11px] font-mono" {...props}>
                  {children}
                </code>
              );
            }
            return (
              <pre className="bg-muted text-foreground rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono leading-relaxed">
                {match && (
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5">
                    {match[1]}
                  </div>
                )}
                <code className={codeClass} {...props}>
                  {children}
                </code>
              </pre>
            );
          },
          a({ children, href, ...props }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline hover:opacity-80"
                {...props}
              >
                {children}
              </a>
            );
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-2">
                <table className="min-w-full border border-border rounded-lg text-xs">{children}</table>
              </div>
            );
          },
          th({ children }) {
            return (
              <th className="bg-muted px-3 py-2 text-left font-semibold border-b border-border">
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td className="px-3 py-2 border-b border-border/50">
                {children}
              </td>
            );
          },
          blockquote({ children }) {
            return (
              <blockquote className="border-l-4 border-primary/30 pl-4 my-2 italic text-muted-foreground">
                {children}
              </blockquote>
            );
          },
          img({ src, alt }) {
            return (
              <img
                src={src}
                alt={alt || ""}
                className="rounded-lg max-w-full my-2"
                loading="lazy"
              />
            );
          },
          hr() {
            return <hr className="border-border my-3" />;
          },
          ul({ children }) {
            return <ul className="list-disc pl-5 space-y-1 my-2 text-sm">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="list-decimal pl-5 space-y-1 my-2 text-sm">{children}</ol>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
