import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { Copy, Check, ZoomIn, ZoomOut, RotateCcw, Code, Eye } from 'lucide-react';
import { Button } from '../common/Button';

interface MermaidViewerProps {
  chart: string;
  className?: string;
}

export const MermaidViewer: React.FC<MermaidViewerProps> = ({ chart, className = '' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [showCode, setShowCode] = useState(false);

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      securityLevel: 'loose',
      fontFamily: 'JetBrains Mono, Menlo, Monaco, monospace',
      er: {
        diagramPadding: 20,
        layoutDirection: 'TB',
        minEntityWidth: 100,
        minEntityHeight: 75,
        entityPadding: 15,
        useMaxWidth: true,
      },
      themeVariables: {
        darkMode: true,
        background: '#090d16',
        primaryColor: '#4f46e5',
        primaryTextColor: '#f8fafc',
        primaryBorderColor: '#6366f1',
        lineColor: '#06b6d4',
        secondaryColor: '#1e293b',
        tertiaryColor: '#0f172a',
        attributeBackgroundColorOdd: '#111827',
        attributeBackgroundColorEven: '#0f172a',
      },
    });
  }, []);

  useEffect(() => {
    let isMounted = true;

    const renderChart = async () => {
      if (!chart || !chart.trim()) {
        setSvgContent('');
        return;
      }

      try {
        setError(null);
        const id = `mermaid-svg-${Math.random().toString(36).substring(2, 9)}`;
        const { svg } = await mermaid.render(id, chart);
        if (isMounted) {
          setSvgContent(svg);
        }
      } catch (err: any) {
        console.error('Mermaid render error:', err);
        if (isMounted) {
          setError(err.message || 'Failed to render Mermaid ER Diagram');
        }
      }
    };

    renderChart();

    return () => {
      isMounted = false;
    };
  }, [chart]);

  const handleCopy = () => {
    navigator.clipboard.writeText(chart);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.15, 2.5));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.15, 0.4));
  const handleResetZoom = () => setZoom(1);

  return (
    <div className={`rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden flex flex-col ${className}`}>
      {/* Viewer Controls Toolbar */}
      <div className="px-4 py-2.5 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-slate-300 font-bold tracking-wider uppercase">Mermaid ER Renderer</span>
          <span className="text-[10px] px-2 py-0.5 rounded-md bg-indigo-950/60 border border-indigo-800 text-indigo-300">
            Entity-Relationship
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Zoom Controls */}
          <button
            onClick={handleZoomOut}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-[11px] text-slate-400 px-1">{Math.round(zoom * 100)}%</span>
          <button
            onClick={handleZoomIn}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleResetZoom}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
            title="Reset Zoom"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <div className="w-[1px] h-4 bg-slate-800 mx-1" />

          {/* Toggle Syntax / Diagram */}
          <button
            onClick={() => setShowCode(!showCode)}
            className={`px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-colors ${
              showCode ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300 hover:text-white'
            }`}
          >
            {showCode ? <Eye className="w-3.5 h-3.5" /> : <Code className="w-3.5 h-3.5" />}
            <span>{showCode ? 'View Diagram' : 'View Code'}</span>
          </button>

          {/* Copy Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            leftIcon={copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          >
            {copied ? 'Copied' : 'Copy ER Syntax'}
          </Button>
        </div>
      </div>

      {/* Render Area */}
      <div className="relative min-h-[420px] max-h-[700px] overflow-auto p-6 flex items-center justify-center bg-[#070b14]">
        {showCode ? (
          <div className="w-full h-full p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono text-cyan-300 overflow-auto whitespace-pre">
            {chart}
          </div>
        ) : error ? (
          <div className="p-6 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-mono max-w-lg">
            <p className="font-bold mb-2">Failed to render Mermaid ER Diagram</p>
            <p className="text-slate-400 mb-3">{error}</p>
            <pre className="p-3 bg-slate-950 rounded-lg text-slate-300 text-[11px] overflow-x-auto">{chart}</pre>
          </div>
        ) : (
          <div
            ref={containerRef}
            style={{ transform: `scale(${zoom})`, transformOrigin: 'center center', transition: 'transform 0.15s ease-out' }}
            className="w-full flex justify-center items-center select-none"
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
        )}
      </div>
    </div>
  );
};
