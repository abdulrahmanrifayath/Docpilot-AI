import React, { useState } from 'react';
import { Copy, Check, Download } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
  title?: string;
  downloadFilename?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  title,
  downloadFilename = 'document.md',
}) => {
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = downloadFilename;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Basic lightweight Markdown parser to HTML
  const formatMarkdown = (md: string) => {
    let html = md
      // Escaping
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      // Headers
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      // Blockquotes
      .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
      // Bold & Italic
      .replace(/\*\*\*(.*?)\*\*\*/gim, '<b><i>$1</i></b>')
      .replace(/\*\*(.*?)\*\*/gim, '<b>$1</b>')
      .replace(/\*(.*?)\*/gim, '<i>$1</i>')
      // Code blocks
      .replace(/```([a-z0-9_-]*)\n([\s\S]*?)```/gim, '<pre><code class="language-$1">$2</code></pre>')
      // Inline code
      .replace(/`([^`]+)`/gim, '<code>$1</code>')
      // Unordered lists
      .replace(/^\- (.*$)/gim, '<ul><li>$1</li></ul>')
      // Horizontal rules
      .replace(/^---$/gim, '<hr class="my-6 border-slate-800" />')
      // Line breaks
      .replace(/\n\n/gim, '<p></p>');

    // Clean contiguous <ul> lists
    html = html.replace(/<\/ul>\s*<ul>/gim, '');

    return html;
  };

  return (
    <div className="w-full bg-[#0f172a]/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
      {/* Action Bar */}
      <div className="px-6 py-4 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between">
        <h3 className="text-base font-bold text-white tracking-tight">{title || 'Documentation'}</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white transition-colors flex items-center gap-1.5 border border-slate-700"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy Markdown'}</span>
          </button>
          <button
            onClick={handleDownload}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-brand-600 hover:bg-brand-500 transition-colors flex items-center gap-1.5 shadow-md shadow-brand-500/20"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download .md</span>
          </button>
        </div>
      </div>

      {/* Rendered Prose Content */}
      <div className="p-8 markdown-body overflow-x-auto text-left leading-relaxed">
        <div dangerouslySetInnerHTML={{ __html: formatMarkdown(content) }} />
      </div>
    </div>
  );
};
