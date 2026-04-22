"use client";

interface ConfidenceRingProps {
  score: number; // 0–1
  size?: number;
  strokeWidth?: number;
}

export default function ConfidenceRing({
  score,
  size = 64,
  strokeWidth = 3.5,
}: ConfidenceRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - score * circumference;
  const percent = Math.round(score * 100);

  // Color based on match quality
  const getColor = () => {
    if (score >= 0.75) return { stroke: "#34d399", text: "text-emerald-400" };
    if (score >= 0.6) return { stroke: "#fbbf24", text: "text-amber-400" };
    return { stroke: "#f87171", text: "text-red-400" };
  };

  const color = getColor();

  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="-rotate-90"
      >
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          className="confidence-ring-track"
          strokeWidth={strokeWidth}
        />
        {/* Fill */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color.stroke}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="confidence-ring-fill"
          style={{ "--ring-color": color.stroke } as React.CSSProperties}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-sm font-bold tabular-nums ${color.text}`}>
          {percent}%
        </span>
      </div>
    </div>
  );
}
