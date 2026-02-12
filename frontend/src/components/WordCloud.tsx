import { useEffect, useRef } from "react";
import type { WordFrequency } from "../types";

interface Props {
  words: WordFrequency[];
}

export default function WordCloud({ words }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || words.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    const maxCount = Math.max(...words.map((w) => w.count));
    const minCount = Math.min(...words.map((w) => w.count));
    const range = maxCount - minCount || 1;

    const colors = [
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
    ];

    // Simple spiral placement
    const placed: Array<{
      x: number;
      y: number;
      w: number;
      h: number;
    }> = [];

    const sorted = [...words].sort((a, b) => b.count - a.count).slice(0, 60);

    for (let i = 0; i < sorted.length; i++) {
      const word = sorted[i];
      const fontSize = 14 + ((word.count - minCount) / range) * 36;
      ctx.font = `${Math.round(fontSize)}px sans-serif`;
      const metrics = ctx.measureText(word.word);
      const textW = metrics.width;
      const textH = fontSize;

      // Spiral placement
      let angle = 0;
      let radius = 0;
      let x = 0;
      let y = 0;
      let found = false;

      for (let step = 0; step < 500; step++) {
        angle = step * 0.5;
        radius = step * 1.5;
        x = width / 2 + radius * Math.cos(angle) - textW / 2;
        y = height / 2 + radius * Math.sin(angle) + textH / 2;

        if (x < 0 || y < 0 || x + textW > width || y > height) continue;

        const overlap = placed.some(
          (p) =>
            x < p.x + p.w && x + textW > p.x && y - textH < p.y && y > p.y - p.h
        );

        if (!overlap) {
          found = true;
          break;
        }
      }

      if (found) {
        ctx.fillStyle = colors[i % colors.length];
        ctx.font = `${Math.round(fontSize)}px sans-serif`;
        ctx.fillText(word.word, x, y);
        placed.push({ x, y, w: textW, h: textH });
      }
    }
  }, [words]);

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={400}
      style={{ width: "100%", height: "auto", maxHeight: 400 }}
    />
  );
}
