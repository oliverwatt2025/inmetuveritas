import React from "react";

/**
 * DEFCON levels
 * 5 = calm
 * 1 = maximum danger
 */
export type DefconLevel = 1 | 2 | 3 | 4 | 5;

type Props = {
  level: DefconLevel;
  note?: string;
  corner?: "top-right" | "top-left" | "bottom-right" | "bottom-left";
};

function palette(level: DefconLevel) {
  switch (level) {
    case 1:
      return { color: "#ffffff", glow: "rgba(255,255,255,0.35)" }; // white
    case 2:
      return { color: "#ff4d4d", glow: "rgba(255,77,77,0.35)" };
    case 3:
      return { color: "#ffb347", glow: "rgba(255,179,71,0.30)" };
    case 4:
      return { color: "#f6e58d", glow: "rgba(246,229,141,0.25)" };
    default:
      return { color: "#2ecc71", glow: "rgba(46,204,113,0.25)" };
  }
}

function cornerStyle(corner: NonNullable<Props["corner"]>) {
  const pad = 16;
  const base: React.CSSProperties = { position: "absolute", zIndex: 50 };
  if (corner === "top-left") return { ...base, top: pad, left: pad };
  if (corner === "bottom-left") return { ...base, bottom: pad, left: pad };
  if (corner === "bottom-right") return { ...base, bottom: pad, right: pad };
  return { ...base, top: pad, right: pad };
}

export function DefconMeter({
  level,
  note,
  corner = "top-right",
}: Props) {
  const { color, glow } = palette(level);
  const labels: Record<DefconLevel, string> = {
    5: "Routine Operations",
    4: "Increase Awareness",
    3: "Prepare For Alert",
    2: "Action Needed",
    1: "Global Thermo Nuclear War",
  };

  return (
    <div style={cornerStyle(corner)}>
      <div
        style={{
          width: 220,
          padding: 14,
          borderRadius: 14,
          background: "rgba(0,0,0,0.22)",
border: "1px solid rgba(255,255,255,0.08)",
boxShadow: `0 0 16px ${glow}`,
          backdropFilter: "blur(10px)",
          WebkitBackdropFilter: "blur(10px)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontSize: 11, letterSpacing: 2, opacity: 0.7 }}>
              DEFCON
            </div>
            <div style={{ fontSize: 12, opacity: 0.6 }}>
              {labels[level]}
            </div>
          </div>

          <div
            style={{
              fontSize: 30,
              fontWeight: 700,
              color,
              textShadow: `0 0 10px ${glow}`,
            }}
          >
            {level}
          </div>
        </div>

        <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
          {[5, 4, 3, 2, 1].map((n) => (
            <div
              key={n}
              style={{
                height: 10,
                flex: 1,
                borderRadius: 4,
                background:
                  n === level ? color : "rgba(255,255,255,0.2)",
                boxShadow:
                  n === level ? `0 0 10px ${glow}` : "none",
                opacity: n >= level ? 1 : 0.35,
              }}
            />
          ))}
        </div>

        {note && (
          <div
            style={{
              marginTop: 8,
              fontSize: 11,
              lineHeight: 1.3,
              opacity: 0.65,
            }}
          >
            {note}
          </div>
        )}
      </div>
    </div>
  );
}
