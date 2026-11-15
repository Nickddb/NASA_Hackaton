# AstraCare AI — Biophilic Aerospace Medical Cockpit Design System (`DESIGN.md`)

> Redesigned from the **Clean Eco-Tech / Biophilic Daylight** visual reference (`media_1794682106903_f639a15e.jpg`): airy white canvas, soft mint-sage & glacial-sky tinted cards, deep forest-pine typography, and pill-shaped controls, paired with high-contrast `NASA-STD-3001` traffic-light clinical encoding.

---

## 1. Visual Identity & Core Rules
- **Theme:** *Biophilic Aerospace Medical Cleanroom* — bright, calm, high-clarity clinical interface that reduces cognitive fatigue for astronauts in confined habitats.
- **Compliance:**
  - **No NASA logos, insignia, or Space Apps branding** inside the application UI. Use the plain text badge `"Built with NASA Data • NASA-STD-3001 & OCHMO Clinical Standards"`.
  - **Contrast:** Primary headings/text in Deep Forest (`#113D2E`) on `#FFFFFF` / `#F1FAF4` exceed `11:1` contrast. Secondary labels (`#476458`) exceed `5.5:1`.
  - **Touch Targets:** Minimum `44px` height/width on all buttons, scenario pills, 3D system triggers, and modal actions.

---

## 2. Color Palette & CSS / Tailwind v4 Tokens

```css
@theme {
  --color-bg: #F7FBF9;
  --color-surface: #FFFFFF;
  --color-surface-mint: #EFF9F2;
  --color-surface-sky: #EAF6FA;
  --color-border: #D5E8DD;
  --color-text-primary: #113D2E;
  --color-text-secondary: #476458;
  --color-accent: #16A34A;
  --color-accent-lime: #C8EE90;
  --color-accent-sky: #0284C7;
  --color-nominal: #059669;
  --color-warning: #D97706;
  --color-critical: #DC2626;
  --font-sans: "Space Grotesk", "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", "IBM Plex Mono", monospace;
  --radius-md: 1rem;
  --radius-lg: 1.5rem;
}
```

### Traffic-Light Clinical Encoding (Light-Mode High Contrast)
| Status | Dot / Solid | Light Surface Tint | Border | Text |
| :--- | :--- | :--- | :--- | :--- |
| **NOMINAL** | `#10B981` | `#ECFDF5` | `#A7F3D0` | `#065F46` |
| **WARNING** | `#F59E0B` | `#FFFBEB` | `#FDE68A` | `#92400E` |
| **CRITICAL** | `#EF4444` | `#FEF2F2` | `#FECACA` | `#991B1B` |

---

## 3. Typography & Shapes
- **Headings:** `Space Grotesk` (bold, `#113D2E`), clean editorial spacing.
- **Body:** `Inter` (`#334E44` / `#476458`), `14px–16px`, line height `1.5`.
- **Telemetry:** `JetBrains Mono` (`tabular-nums`) for BPM, HRV, BP, Glucose, Radiation `mSv/h`, and ML scores.
- **Cards:** `rounded-2xl` (`16px`) / `rounded-3xl` (`24px`), crisp `1px` `#D5E8DD` borders, soft elevation shadow (`0 10px 30px -12px rgba(17, 61, 46, 0.08)`), alternating pure white, soft mint (`#EFF9F2`), and soft sky (`#EAF6FA`) surfaces.
- **Buttons:** Pill-shaped (`rounded-full`) with `min-h-[44px]`:
  - Primary CTA: `#113D2E` fill with `#FFFFFF` text.
  - Lime Highlight CTA: `#C8EE90` fill with `#113D2E` bold text.
  - Sky Secondary CTA: `#DFF1F8` fill with `#0C4A6E` text.
- **Footer:** Deep forest-green (`#113D2E`) full-width band with crisp white/mint text.
