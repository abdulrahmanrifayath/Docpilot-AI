import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { ZoomIn, ZoomOut, RotateCcw, Copy, Check, Code } from 'lucide-react';

interface MermaidViewerProps {
  code: string;
  title?: string;
}

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
  themeVariables: {
    darkMode: true,
    background: '#0f172a',
    primaryColor: '#8b5cf6',
    primaryTextColor: '#f8fafc',
    primaryBorderColor: '#6d28d9',
    lineColor: '#94a3b8',
    secondaryColor: '#06b6d4',
    tertiaryColor: '#10b981',
    fontFamily: 'Inter, sans-serif',
  },
});

export const MermaidViewer: React.FC<MermaidViewerProps> = ({ code, title }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>('');
  const [zoom, setZoom] = useState<number>(1);
  const [showCode, setShowCode] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [renderError, setRenderError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const renderDiagram = async () => {
      if (!code) return;
      try {
        setRenderError(null);
        const id = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
        const { svg } = await mermaid.render(id, code);
        if (isMounted) {
          setSvgContent(svg);
        }
      } catch (err: any) {
        if (isMounted) {
          setRenderError(err?.message || 'Error rendering diagram');
        }
      }
    };

    renderDiagram();
    return () => {
      isMounted = false;
    };
  }, [code]);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="w-full bg-[#0f172a]/90 border border-slate-800 rounded-2xl overflow-hidden flex flex-col shadow-xl">
      {/* Header Controls */}
      <div className="px-4 py-3 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-200">{title || 'Mermaid Diagram'}</h4>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setZoom((z) => Math.min(z + 0.15, 2.5))}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(z - 0.15, 0.4))}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Reset Zoom"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          <div className="w-px h-4 bg-slate-800 mx-1" />

          <button
            onClick={() => setShowCode(!showCode)}
            className={`p-1.5 rounded-lg transition-colors ${
              showCode ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
            title="Toggle Source Code"
          >
            <Code className="w-4 h-4" />
          </button>

          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Copy Diagram Code"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Main Diagram Area */}
      {showCode ? (
        <div className="p-4 bg-black/40 font-mono text-xs text-slate-300 overflow-x-auto max-h-[500px]">
          <pre>{code}</pre>
        </div>
      ) : renderError ? (
        <div className="p-8 text-center text-rose-400 text-sm">
          <p>Failed to render diagram:</p>
          <p className="font-mono text-xs mt-1 text-slate-400">{renderError}</p>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="p-8 overflow-auto flex items-center justify-center min-h-[420px] max-h-[650px] bg-[#0b0f19]/40"
        >
          <div
            style={{ transform: `scale(${zoom})`, transformOrigin: 'center center', transition: 'transform 0.15s ease' }}
            dangerouslySetInnerHTML={{ __html: svgContent }}
            className="select-none [&_svg]:max-w-none"
          />
        </div>
      )}
    </div>
  );
};
