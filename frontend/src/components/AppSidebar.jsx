import {
  BookOpen,
  Brain,
  ClipboardCheck,
  HeartPulse,
  MessageSquare,
  Orbit,
  Sun,
  Users,
} from "lucide-react";

// Navigation replaces the old header. Mission-wide pages first, then the pages about the selected astronaut,
// then demo tooling, kept apart so it never competes with clinical content.
export const MISSION_PAGES = [
  { id: "crew", label: "Crew", icon: Users },
  { id: "environment", label: "Environment", icon: Sun },
];
export const ASTRONAUT_PAGES = [
  { id: "vitals", label: "Vitals", icon: HeartPulse },
  { id: "diagnosis", label: "Diagnosis", icon: ClipboardCheck },
  { id: "mind", label: "Mind", icon: Brain },
  { id: "assistant", label: "Assistant", icon: MessageSquare },
];

const STATUS_DOT = {
  CRITICAL: "bg-red-500",
  WARNING: "bg-amber-400",
  NOMINAL: "bg-emerald-400",
};

function NavItem({ item, active, badge, onClick }) {
  const Icon = item.icon;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      className={`flex min-h-[40px] w-full items-center gap-3 rounded-lg px-3 text-sm transition cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-400 ${
        active ? "bg-white/[0.08] font-semibold text-white" : "text-slate-400 hover:bg-white/[0.04] hover:text-white"
      }`}
    >
      <Icon className={`h-[18px] w-[18px] shrink-0 ${active ? "text-emerald-300" : ""}`} strokeWidth={1.8} />
      <span className="flex-1 text-left">{item.label}</span>
      {badge > 0 && (
        <span className="min-w-[20px] rounded-full bg-red-500/90 px-1.5 text-center font-mono text-[11px] font-bold text-white">
          {badge}
        </span>
      )}
    </button>
  );
}

function GroupLabel({ children }) {
  return <p className="mb-1 mt-5 px-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">{children}</p>;
}

export default function AppSidebar({
  page,
  onNavigate,
  crew = [],
  activeCrewId,
  onSelectCrew,
  connection,
  alertCount = 0,
  onOpenStandards,
}) {
  const live = connection === "live";
  return (
    <aside
      aria-label="Main navigation"
      className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-white/[0.08] bg-[#05070B]/92 backdrop-blur-xl lg:flex"
    >
      <div className="flex items-center gap-2.5 px-5 pb-2 pt-5">
        <Orbit className="h-6 w-6 text-emerald-300" strokeWidth={1.8} aria-hidden="true" />
        <span className="text-base font-semibold tracking-tight text-white">AstraCare</span>
        <span
          className="ml-auto flex items-center gap-1.5 text-[11px] text-slate-400"
          title={live ? "Connected to the onboard backend" : "Backend unreachable: values are simulated in the browser"}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${live ? "bg-emerald-400" : "bg-amber-400"}`} />
          {live ? "Live" : connection === "unknown" ? "…" : "Simulated"}
        </span>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        <GroupLabel>Mission</GroupLabel>
        {MISSION_PAGES.map((item) => (
          <NavItem
            key={item.id}
            item={item}
            active={page === item.id}
            badge={item.id === "crew" ? alertCount : 0}
            onClick={() => onNavigate(item.id)}
          />
        ))}

        <GroupLabel>Astronaut</GroupLabel>
        <ul className="mb-2 space-y-0.5" aria-label="Select astronaut">
          {crew.map((m) => {
            const active = m.crew_id === activeCrewId;
            return (
              <li key={m.crew_id}>
                <button
                  type="button"
                  onClick={() => onSelectCrew(m.crew_id)}
                  aria-pressed={active}
                  className={`flex min-h-[34px] w-full items-center gap-2.5 rounded-lg px-3 text-left text-[13px] transition cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-400 ${
                    active ? "bg-emerald-400/10 text-white" : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
                  }`}
                >
                  <span className={`h-2 w-2 shrink-0 rounded-full ${STATUS_DOT[m.status] || STATUS_DOT.NOMINAL}`} aria-hidden="true" />
                  <span className="truncate">{m.name.replace(/\s*\(.*\)$/, "")}</span>
                  <span className="sr-only">{m.status}</span>
                </button>
              </li>
            );
          })}
        </ul>
        {ASTRONAUT_PAGES.map((item) => (
          <NavItem key={item.id} item={item} active={page === item.id} onClick={() => onNavigate(item.id)} />
        ))}

        <div className="my-4 h-px bg-white/[0.06]" />
        <NavItem item={{ id: "standards", label: "NASA standards", icon: BookOpen }} active={false} onClick={onOpenStandards} />
      </nav>

      <p className="border-t border-white/[0.06] px-5 py-3 text-[11px] leading-snug text-slate-500">
        Built with NASA data · NASA-STD-3001 &amp; OCHMO clinical standards
      </p>
    </aside>
  );
}

// Below lg the sidebar becomes a bottom tab bar (no top header on any size).
export function MobileTabBar({ page, onNavigate, alertCount = 0 }) {
  const items = [...MISSION_PAGES.slice(0, 1), ...ASTRONAUT_PAGES, MISSION_PAGES[1]];
  return (
    <nav
      aria-label="Main navigation"
      className="fixed inset-x-0 bottom-0 z-30 flex overflow-x-auto border-t border-white/10 bg-[#05070B]/95 px-1 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl lg:hidden"
    >
      {items.map((item) => {
        const Icon = item.icon;
        const active = page === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            aria-current={active ? "page" : undefined}
            className={`relative flex min-h-[56px] min-w-[64px] flex-1 flex-col items-center justify-center gap-0.5 text-[10px] cursor-pointer ${
              active ? "text-white" : "text-slate-500"
            }`}
          >
            <Icon className={`h-5 w-5 ${active ? "text-emerald-300" : ""}`} strokeWidth={1.8} />
            {item.label}
            {item.id === "crew" && alertCount > 0 && (
              <span className="absolute right-3 top-2 h-2 w-2 rounded-full bg-red-500" aria-label={`${alertCount} alerts`} />
            )}
          </button>
        );
      })}
    </nav>
  );
}
