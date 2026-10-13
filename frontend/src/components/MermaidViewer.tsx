import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Copy,
  Check,
  Code,
  Download,
  Maximize2,
  Minimize2,
  RefreshCw,
  FileCode,
  AlertTriangle,
} from 'lucide-react';

interface MermaidViewerProps {
  code: string;
  title?: string;
  description?: string;
  version?: number;
  onRegenerate?: () => void;
  isRegenerating?: boolean;
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

export const MermaidViewer: React.FC<MermaidViewerProps> = ({
  code,
  title,
  description,
  version,
  onRegenerate,
  isRegenerating = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>('');
  const [zoom, setZoom] = useState<number>(1);
  const [showCode, setShowCode] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    const renderDiagram = async () => {
      if (!code) {
        setSvgContent('');
        return;
      }
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

  // Handle escape to close fullscreen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFullscreen]);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadSvg = () => {
    if (!svgContent) return;
    const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(title || 'diagram').toLowerCase().replace(/[^a-z0-9]+/g, '-')}.svg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleDownloadMmd = () => {
    if (!code) return;
    const blob = new Blob([code], { type: 'text/vnd.mermaid;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${(title || 'diagram').toLowerCase().replace(/[^a-z0-9]+/g, '-')}.mmd`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const viewerContent = (
    <div className="w-full bg-[#0f172a]/95 border border-slate-800 rounded-2xl overflow-hidden flex flex-col shadow-2xl h-full">
      {/* Header Controls */}
      <div className="px-5 py-3.5 bg-slate-900/90 border-b border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-2.5 h-2.5 rounded-full bg-brand-500 animate-pulse" />
          <h4 className="text-sm font-bold text-white truncate">{title || 'Architecture Diagram'}</h4>
          {version && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400">
              v{version}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Zoom Controls */}
          <button
            onClick={() => setZoom((z) => Math.min(z + 0.15, 3.0))}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(z - 0.15, 0.3))}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom(1)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Reset Zoom (100%)"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          <div className="w-px h-4 bg-slate-800 mx-1" />

          {/* Code Toggle */}
          <button
            onClick={() => setShowCode(!showCode)}
            className={`p-1.5 rounded-lg transition-colors ${
              showCode ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
            title="Toggle Mermaid Source Syntax"
          >
            <Code className="w-4 h-4" />
          </button>

          {/* Copy Code */}
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Copy Mermaid Code"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          </button>

          {/* Download SVG */}
          <button
            onClick={handleDownloadSvg}
            disabled={!svgContent}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-40"
            title="Download SVG"
          >
            <Download className="w-4 h-4" />
          </button>

          {/* Download MMD */}
          <button
            onClick={handleDownloadMmd}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Download .mmd file"
          >
            <FileCode className="w-4 h-4" />
          </button>

          {/* Regenerate Diagram */}
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              disabled={isRegenerating}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-40"
              title="Regenerate this diagram"
            >
              <RefreshCw className={`w-4 h-4 ${isRegenerating ? 'animate-spin text-brand-400' : ''}`} />
            </button>
          )}

          <div className="w-px h-4 bg-slate-800 mx-1" />

          {/* Fullscreen Toggle */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title={isFullscreen ? 'Exit Fullscreen (ESC)' : 'Fullscreen View'}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {description && (
        <div className="px-5 py-2 bg-slate-900/40 border-b border-slate-800/40 text-xs text-slate-400">
          {description}
        </div>
      )}

      {/* Main Diagram Canvas Area */}
      {showCode ? (
        <div className="p-5 bg-black/50 font-mono text-xs text-slate-200 overflow-x-auto flex-1 min-h-[420px]">
          <pre className="selection:bg-brand-500/30">{code}</pre>
        </div>
      ) : renderError ? (
        <div className="p-12 text-center text-rose-400 flex flex-col items-center justify-center flex-1 min-h-[420px]">
          <AlertTriangle className="w-8 h-8 text-rose-400 mb-2" />
          <p className="font-semibold text-sm">Failed to render Mermaid diagram:</p>
          <p className="font-mono text-xs mt-2 max-w-lg p-3 bg-rose-950/40 border border-rose-900/60 rounded-xl text-rose-300">
            {renderError}
          </p>
          <button
            onClick={() => setShowCode(true)}
            className="mt-4 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-white transition-colors"
          >
            View Raw Mermaid Code
          </button>
        </div>
      ) : (
        <div
          ref={containerRef}
          className="p-8 overflow-auto flex items-center justify-center flex-1 min-h-[480px] bg-[#0b0f19]/40 relative select-none"
        >
          <div
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: 'center center',
              transition: 'transform 0.15s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
            dangerouslySetInnerHTML={{ __html: svgContent }}
            className="select-none [&_svg]:max-w-none transition-transform"
          />
        </div>
      )}
    </div>
  );

  if (isFullscreen) {
    return (
      <div className="fixed inset-0 z-50 bg-slate-950/95 backdrop-blur-md p-6 flex flex-col animate-in fade-in duration-200">
        <div className="flex-1 w-full max-w-7xl mx-auto flex flex-col">
          {viewerContent}
        </div>
      </div>
    );
  }

  return viewerContent;
};
