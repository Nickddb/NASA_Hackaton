/**
 * Static, high-contrast minimalist deep-space frame backdrop.
 * Keeps the central telemetry region pure black while placing subtle
 * constellations and pinpoint stars along the outer margins.
 */

const EDGE_CONSTELLATIONS = [
  {
    id: "left-upper",
    viewBox: "0 0 180 260",
    className: "left-2 top-16 h-60 w-44 opacity-85 sm:left-4",
    links: [
      [26, 36, 74, 62],
      [74, 62, 58, 118],
      [58, 118, 112, 148],
      [112, 148, 86, 206],
      [74, 62, 128, 44],
    ],
    stars: [
      { x: 26, y: 36, r: 1.4, bright: false },
      { x: 74, y: 62, r: 2.1, bright: true },
      { x: 128, y: 44, r: 1.2, bright: false },
      { x: 58, y: 118, r: 1.5, bright: false },
      { x: 112, y: 148, r: 1.9, bright: true },
      { x: 86, y: 206, r: 1.3, bright: false },
    ],
  },
  {
    id: "left-lower",
    viewBox: "0 0 160 220",
    className: "left-2 bottom-16 h-52 w-36 opacity-75 sm:left-6",
    links: [
      [30, 178, 66, 134],
      [66, 134, 48, 82],
      [48, 82, 102, 54],
      [66, 134, 118, 152],
    ],
    stars: [
      { x: 30, y: 178, r: 1.3, bright: false },
      { x: 66, y: 134, r: 1.8, bright: true },
      { x: 48, y: 82, r: 1.3, bright: false },
      { x: 102, y: 54, r: 1.6, bright: false },
      { x: 118, y: 152, r: 1.2, bright: false },
    ],
  },
  {
    id: "right-mid",
    viewBox: "0 0 180 250",
    className: "right-2 top-[44%] h-60 w-44 opacity-80 sm:right-5",
    links: [
      [142, 34, 96, 72],
      [96, 72, 124, 126],
      [124, 126, 74, 168],
      [124, 126, 154, 186],
      [74, 168, 104, 218],
    ],
    stars: [
      { x: 142, y: 34, r: 1.4, bright: false },
      { x: 96, y: 72, r: 2.0, bright: true },
      { x: 124, y: 126, r: 1.5, bright: false },
      { x: 74, y: 168, r: 1.3, bright: false },
      { x: 154, y: 186, r: 1.7, bright: true },
      { x: 104, y: 218, r: 1.2, bright: false },
    ],
  },
  {
    id: "right-lower",
    viewBox: "0 0 150 180",
    className: "right-3 bottom-12 hidden h-44 w-36 opacity-75 md:block sm:right-7",
    links: [
      [112, 32, 74, 68],
      [74, 68, 102, 122],
      [102, 122, 46, 142],
    ],
    stars: [
      { x: 112, y: 32, r: 1.3, bright: false },
      { x: 74, y: 68, r: 1.8, bright: true },
      { x: 102, y: 122, r: 1.4, bright: false },
      { x: 46, y: 142, r: 1.2, bright: false },
    ],
  },
];

const PERIPHERY_PIN_STARS = [
  { top: "8%", left: "3%", size: 2, opacity: 0.7 },
  { top: "14%", left: "11%", size: 1.5, opacity: 0.45 },
  { top: "33%", left: "2.5%", size: 2, opacity: 0.6 },
  { top: "52%", left: "4.5%", size: 1.5, opacity: 0.5 },
  { top: "68%", left: "2%", size: 2, opacity: 0.65 },
  { top: "89%", left: "8%", size: 1.5, opacity: 0.45 },
  { top: "7%", right: "22%", size: 1.5, opacity: 0.5 },
  { top: "19%", right: "17%", size: 2, opacity: 0.55 },
  { top: "36%", right: "3%", size: 1.5, opacity: 0.6 },
  { top: "64%", right: "2.5%", size: 2, opacity: 0.7 },
  { top: "84%", right: "12%", size: 1.5, opacity: 0.45 },
  { top: "92%", right: "4%", size: 2, opacity: 0.55 },
];

export default function SpaceBackdrop() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden select-none"
    >
      {/* Crisp isolated periphery pin-stars (edges only, leaving center clean pure black) */}
      {PERIPHERY_PIN_STARS.map((star, idx) => (
        <span
          key={idx}
          className="absolute rounded-full bg-white"
          style={{
            top: star.top,
            left: star.left,
            right: star.right,
            width: `${star.size}px`,
            height: `${star.size}px`,
            opacity: star.opacity,
            boxShadow: star.size >= 2 ? "0 0 6px rgba(255,255,255,0.65)" : undefined,
          }}
        />
      ))}

      {/* Subtle hairline constellations framing the left & right peripheries */}
      {EDGE_CONSTELLATIONS.map((group) => (
        <svg
          key={group.id}
          viewBox={group.viewBox}
          fill="none"
          className={`absolute ${group.className}`}
        >
          {group.links.map(([x1, y1, x2, y2], idx) => (
            <line
              key={idx}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="#E2E8F0"
              strokeWidth="0.7"
              strokeOpacity="0.16"
            />
          ))}
          {group.stars.map((s, idx) => (
            <g key={idx}>
              {s.bright && (
                <>
                  <circle cx={s.x} cy={s.y} r={s.r * 3.4} fill="#FFFFFF" fillOpacity="0.08" />
                  <path
                    d={`M${s.x - 5.5} ${s.y} H${s.x + 5.5} M${s.x} ${s.y - 5.5} V${s.y + 5.5}`}
                    stroke="#FFFFFF"
                    strokeWidth="0.65"
                    strokeOpacity="0.45"
                  />
                </>
              )}
              <circle
                cx={s.x}
                cy={s.y}
                r={s.r}
                fill="#F8FAFC"
                fillOpacity={s.bright ? "0.95" : "0.65"}
              />
            </g>
          ))}
        </svg>
      ))}
    </div>
  );
}
