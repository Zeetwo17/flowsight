import type { FrameRow } from "../types";

interface Props {
  frames: FrameRow[];
  frameIdx: number;
  setFrameIdx: (i: number) => void;
  playing: boolean;
  onTogglePlay: () => void;
}

export default function Timeline({ frames, frameIdx, setFrameIdx, playing, onTogglePlay }: Props) {
  if (!frames.length) return null;
  const frame = frames[frameIdx];
  const lastT = frames[frames.length - 1]?.t ?? 0;

  // Compute disruption hot-spots: timesteps with peak-of-peaks risk
  const peaks = frames.map((f) => Math.max(...f.risk));
  const peakMax = Math.max(...peaks, 1e-6);

  return (
    <div className="border-t border-slate-700 bg-ink/60 px-3 py-2 flex items-center gap-3">
      <button
        onClick={onTogglePlay}
        className="bg-accent hover:bg-blue-600 text-white rounded w-9 h-9 flex items-center justify-center text-sm font-medium shrink-0"
        aria-label={playing ? "Pause" : "Play"}
      >
        {playing ? "❚❚" : "▶"}
      </button>
      <div className="flex-1 min-w-0">
        <div className="relative h-8">
          {/* heatbar background */}
          <div className="absolute inset-0 flex items-center">
            <div className="w-full h-2 rounded-full overflow-hidden flex bg-slate-700/40">
              {peaks.map((p, i) => (
                <div
                  key={i}
                  className="h-full"
                  style={{
                    flex: 1,
                    background: `rgba(220, 60, 60, ${(p / peakMax) * 0.85})`
                  }}
                />
              ))}
            </div>
          </div>
          <input
            type="range"
            min={0}
            max={frames.length - 1}
            value={frameIdx}
            onChange={(e) => setFrameIdx(parseInt(e.target.value))}
            className="absolute inset-0 w-full opacity-80 cursor-pointer accent-accent"
            aria-label="Cascade time"
          />
        </div>
      </div>
      <div className="text-xs text-slate-300 shrink-0 tabular-nums w-20 text-right">
        t = {frame.t.toFixed(0)} / {lastT.toFixed(0)} min
      </div>
    </div>
  );
}
