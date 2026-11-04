import { evolvePath } from "@remotion/paths";

/** SVG filter for a soft glow around outlines; put once inside the overlay <svg>. */
export const GlowDefs: React.FC = () => (
  <defs>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="4" result="b" />
      <feMerge>
        <feMergeNode in="b" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>
);

/** One of SAM's outlines, drawn on with an animated stroke (progress 0 to 1), then filled faintly. */
export const Outline: React.FC<{
  d: string;
  color: string;
  progress: number;
  width: number;
  fill?: number;
}> = ({ d, color, progress, width, fill = 0 }) => {
  if (progress <= 0) return null;
  const evo = evolvePath(Math.min(1, progress), d);
  return (
    <g>
      {fill > 0 && <path d={d} fill={color} fillOpacity={fill} stroke="none" />}
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={width}
        strokeLinejoin="round"
        strokeLinecap="round"
        strokeDasharray={evo.strokeDasharray}
        strokeDashoffset={evo.strokeDashoffset}
        filter="url(#glow)"
      />
    </g>
  );
};
