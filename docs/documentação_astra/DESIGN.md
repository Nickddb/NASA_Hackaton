# AstraCare AI — Design System (`DESIGN.md`)

> **Mission cockpit, dark.** The crew reads this console in a dim cabin, often in the middle of a sleep shift or an emergency, so the interface is a deep near-black surface over a quiet star field, with colour reserved for clinical meaning. Adapted from `VoltAgent/awesome-design-md` (`spacex` + `sentry`, MIT).
>
> The light "eco-tech" palette that `frontend/src/index.css` still declares in `@theme` (`#F7FBF9`, `#113D2E`, mint and lime) is **legacy**: no screen uses it any more. Components use the dark tokens below.

---

## 1. Surfaces

| Role | Value | Where |
| --- | --- | --- |
| Page | `#030406` + `SpaceBackdrop` star field | `body`, behind every screen |
| Navigation | `#05070B` at 92–95 %, `backdrop-blur-xl`, `border-white/[0.08]` | Sidebar (≥ lg), bottom tab bar (< lg) |
| Panel | `bg-[#0B0E14]/80`, `border border-white/10`, `rounded-2xl` | Every section card (Vitals, Diagnosis, Mind, Assistant, Environment) |
| Inner surface | `bg-[#151922]` (controls, chips, nested rows), `bg-[#0E1218]` (inputs, selects) | Tabs track, quick prompts, form fields, agent replies |
| Dividers | `border-white/10`, `divide-white/10` | Lists, tables |

One elevation per element: a border **or** a shadow, never both. Card radius 16 px (`rounded-2xl`); pills only for small controls and status badges.

## 2. Text

| Role | Class |
| --- | --- |
| Primary | `text-white` |
| Body | `text-slate-200` / `text-slate-300` |
| Secondary, labels | `text-slate-400` |
| Placeholder, disabled | `text-slate-500` |

All text on panels stays ≥ 4.5 : 1 contrast. Coloured surfaces tint their text from the same hue (for example `bg-red-500/10` + `text-red-300`), never grey.

## 3. Clinical colour (traffic light)

Colour is reserved for status and action; it is never decoration.

| Status | Surface | Border | Text | Dot / solid |
| --- | --- | --- | --- | --- |
| **NOMINAL** | `bg-emerald-500/10–20` | `border-emerald-400/30–50` | `text-emerald-300` / `-100` | `emerald-400` |
| **ATTENTION / WARNING** | `bg-amber-500/10–20` | `border-amber-400/30–55` | `text-amber-200` | `amber-400` |
| **CRITICAL** | `bg-red-500/10` | `border-red-400/30` | `text-red-300` | `red-400` / `red-500` |
| **Information / link** | `bg-sky-500/10` | `border-sky-400/30` | `text-sky-200` / `-300` | `sky-400` |

## 4. Controls

- **Primary action:** `bg-sky-600 text-white hover:bg-sky-500`, `rounded-xl` or `rounded-full`, min height 40–44 px.
- **Secondary action:** `border border-white/15 bg-[#151922] text-slate-200 hover:border-white/35 hover:text-white`.
- **Positive confirmation:** `border-emerald-400/50 bg-emerald-500/20 text-emerald-100 hover:bg-emerald-500/30`.
- **Focus:** visible ring or outline in `sky-400` (`emerald-400` on emerald controls); inputs `focus:border-sky-400 focus:ring-sky-400/25`.
- **Tabs:** track `bg-[#151922]`, active tab `bg-white/10 text-white`, idle `text-slate-300 hover:text-white`.
- Touch targets are at least 40 px high; the pain map and chat input are usable with one thumb.

## 5. Typography

- **Display / headings:** Space Grotesk (fallback Inter), semibold to bold.
- **UI and body:** Inter, 13–15 px in panels; dense labels at 11 px (`text-[11px]`).
- **Measurements:** JetBrains Mono (`font-mono-telemetry`) only for numbers that are readings: heart rate, pressures, delays, doses, hashes.

## 6. Signature elements

- **3D anatomical body** (`AnatomyBody3D.jsx`): neutral clay `#C4C8CE` under three directional lights. Hover lightens, selection turns emerald, and reported pain tints the part amber → orange → red by intensity.
- **Crew cards:** Mercury suit figure with the traffic-light badge and four vitals; alerts cannot be dismissed until a new reading is back in the personal range.
- **Agent trace:** each assistant answer lists the tools it executed, with their status badge, so the reasoning is auditable.

## 7. Screens

Crew · Environment · (per astronaut) Vitals · Diagnosis · Mind · Assistant · NASA standards (modal). No top header: navigation lives in the sidebar on desktop and the bottom tab bar on mobile. The former Simulator tab was removed; scenario changes remain available through the API.
