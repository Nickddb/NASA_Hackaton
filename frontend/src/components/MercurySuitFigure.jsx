const STATUS_VISUALS = {
  CRITICAL: {
    ring: "#EF4444",
    glow: "rgba(239, 68, 68, 0.55)",
    beacon: "bg-red-500 shadow-[0_0_16px_4px_rgba(239,68,68,0.95)] animate-ping",
    beaconSolid: "bg-red-400 shadow-[0_0_12px_3px_rgba(239,68,68,0.9)]",
    dropShadow: "drop-shadow(0 0 12px rgba(239, 68, 68, 0.85)) drop-shadow(0 8px 18px rgba(0, 0, 0, 0.72))",
    blinkClass: "suit-blink-critical",
  },
  WARNING: {
    ring: "#F59E0B",
    glow: "rgba(245, 158, 11, 0.45)",
    beacon: "bg-amber-400 shadow-[0_0_14px_4px_rgba(245,158,11,0.9)] animate-ping",
    beaconSolid: "bg-amber-300 shadow-[0_0_10px_3px_rgba(245,158,11,0.85)]",
    dropShadow: "drop-shadow(0 0 10px rgba(245, 158, 11, 0.78)) drop-shadow(0 8px 18px rgba(0, 0, 0, 0.72))",
    blinkClass: "suit-blink-warning",
  },
  NOMINAL: {
    ring: "#22C55E",
    glow: "rgba(56, 189, 248, 0.24)",
    beacon: "",
    beaconSolid: "bg-emerald-400 shadow-[0_0_8px_2px_rgba(34,197,94,0.8)]",
    dropShadow: "drop-shadow(0 0 8px rgba(56, 189, 248, 0.25)) drop-shadow(0 10px 18px rgba(0, 0, 0, 0.7))",
    blinkClass: "",
  },
};

export default function MercurySuitFigure({
  status = "NOMINAL",
  accentColor = "#38BDF8",
  callsign = "EVA-1",
  zooming = false,
}) {
  const visual = STATUS_VISUALS[status] || STATUS_VISUALS.NOMINAL;
  const isAlert = status === "CRITICAL" || status === "WARNING";

  return (
    <div
      className={`relative mx-auto flex h-[238px] w-[190px] items-center justify-center select-none transition-transform duration-500 ease-out ${
        zooming ? "scale-[1.42] z-20" : "group-hover:scale-[1.03]"
      }`}
    >
      {/* Ambient status halo behind suit */}
      <div
        className={`pointer-events-none absolute inset-x-3 top-2 bottom-6 rounded-full blur-2xl transition-all duration-300 ${
          visual.blinkClass
        }`}
        style={{
          background: `radial-gradient(circle, ${visual.glow} 0%, transparent 72%)`,
        }}
      />

      {/* Grounded holographic deck pedestal under boots */}
      <div
        className="pointer-events-none absolute bottom-5 left-1/2 h-6 w-32 -translate-x-1/2 rounded-full border opacity-90"
        style={{
          borderColor: visual.ring,
          background: `radial-gradient(ellipse at center, ${
            isAlert ? visual.glow : `${accentColor}26`
          } 0%, rgba(10, 12, 16, 0.88) 75%)`,
          boxShadow: `0 0 18px ${isAlert ? visual.glow : "rgba(56, 189, 248, 0.2)"}`,
        }}
      />

      {/* Photorealistic Project Mercury Spacesuit rendered directly from Mercury Spacesuit.glb */}
      <div className={`relative z-10 flex h-[214px] w-[158px] items-center justify-center -mt-3 ${visual.blinkClass}`}>
        <img
          src="/assets/mercury-suit.png"
          alt={`${callsign} Mercury spacesuit`}
          draggable={false}
          className="h-full w-full object-contain pointer-events-none transition-[filter] duration-300"
          style={{ filter: visual.dropShadow }}
        />

        {/* Helmet top comms / alert beacon */}
        {isAlert && (
          <span className="pointer-events-none absolute top-[3%] left-[49%] -translate-x-1/2">
            <span className={`absolute -inset-1 rounded-full ${visual.beacon}`} />
            <span className={`relative block h-2.5 w-2.5 rounded-full border border-white/80 ${visual.beaconSolid}`} />
          </span>
        )}

        {/* Suit chest biotelemetry status LED */}
        <span className="pointer-events-none absolute top-[35%] left-[55%] -translate-x-1/2 -translate-y-1/2">
          {isAlert && <span className={`absolute -inset-1.5 rounded-full ${visual.beacon}`} />}
          <span className={`relative block h-2.5 w-2.5 rounded-full border border-white/80 ${visual.beaconSolid}`} />
        </span>
      </div>

      {/* Callsign badge on deck */}
      <div className="pointer-events-none absolute bottom-1 left-1/2 z-20 -translate-x-1/2">
        <span
          className="inline-flex items-center gap-1.5 rounded-full border bg-[#090C11]/95 px-2.5 py-0.5 font-mono text-[10px] font-bold tracking-widest text-white shadow-lg"
          style={{ borderColor: isAlert ? visual.ring : accentColor }}
        >
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: isAlert ? visual.ring : accentColor }}
          />
          {callsign}
        </span>
      </div>
    </div>
  );
}
