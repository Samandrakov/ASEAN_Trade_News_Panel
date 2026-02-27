import { useEffect, useRef, useState } from "react";
import cloud from "d3-cloud";
import type { WordFrequency } from "../types";

interface Props {
  words: WordFrequency[];
  width?: number;
  height?: number;
}

interface LayoutWord {
  text: string;
  size: number;
  x: number;
  y: number;
  rotate: number;
  color: string;
}

const COLORS = [
  "#1677ff",
  "#52c41a",
  "#faad14",
  "#ff4d4f",
  "#722ed1",
  "#13c2c2",
  "#eb2f96",
  "#fa8c16",
  "#2f54eb",
  "#a0d911",
  "#597ef7",
  "#36cfc9",
];

export default function WordCloud({ words, width = 900, height = 420 }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [layoutWords, setLayoutWords] = useState<LayoutWord[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(width);

  // Responsive width
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w && w > 100) setContainerWidth(Math.floor(w));
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  useEffect(() => {
    if (words.length === 0) {
      setLayoutWords([]);
      return;
    }

    const sorted = [...words].sort((a, b) => b.count - a.count).slice(0, 80);
    const maxCount = sorted[0]?.count || 1;
    const minCount = sorted[sorted.length - 1]?.count || 1;
    const range = maxCount - minCount || 1;

    const cloudWords = sorted.map((w, i) => ({
      text: w.word,
      size: 14 + ((w.count - minCount) / range) * 48,
      color: COLORS[i % COLORS.length],
    }));

    const layout = cloud<{ text: string; size: number; color: string }>()
      .size([containerWidth, height])
      .words(cloudWords)
      .padding(4)
      .rotate(() => (Math.random() > 0.65 ? 90 : 0))
      .fontSize((d) => d.size!)
      .spiral("archimedean")
      .random(() => 0.5)
      .on("end", (output) => {
        setLayoutWords(
          output.map((w) => ({
            text: w.text!,
            size: w.size!,
            x: (w as unknown as LayoutWord).x,
            y: (w as unknown as LayoutWord).y,
            rotate: (w as unknown as LayoutWord).rotate,
            color: (w as unknown as { color: string }).color,
          }))
        );
      });

    layout.start();
  }, [words, containerWidth, height]);

  return (
    <div ref={containerRef} style={{ width: "100%" }}>
      <svg
        ref={svgRef}
        width={containerWidth}
        height={height}
        viewBox={`0 0 ${containerWidth} ${height}`}
        style={{ width: "100%", height: "auto", maxHeight: height }}
      >
        <g transform={`translate(${containerWidth / 2},${height / 2})`}>
          {layoutWords.map((w, i) => (
            <text
              key={`${w.text}-${i}`}
              textAnchor="middle"
              transform={`translate(${w.x},${w.y}) rotate(${w.rotate})`}
              style={{
                fontSize: w.size,
                fontFamily: "'Segoe UI', Arial, sans-serif",
                fontWeight: w.size > 30 ? 700 : 500,
                fill: w.color,
                cursor: "default",
                transition: "opacity 0.2s",
              }}
            >
              {w.text}
            </text>
          ))}
        </g>
      </svg>
    </div>
  );
}
