import { Component, useMemo, useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";

/*
 * Sculpted anatomical body (A-pose, ~1.80 m), built procedurally so that every region is its own selectable
 * part. Ids match backend/app/engine/body_regions.py. Limbs and torso are lathe surfaces with anatomical
 * radius profiles (smoothed with a Catmull-Rom spline) and elliptical cross-sections; muscle groups
 * (pectorals, deltoids, biceps, quadriceps, calves) are added as smooth volumes inside the same part.
 */

// regionId / systemId keep compatibility with the dashboard (exam card, system highlight)
export const ANATOMICAL_PARTS_META = {
  head: { id: "head", label: "Head", regionId: "head", systemId: "nervous_sleep" },
  neck: { id: "neck", label: "Neck", regionId: "head", systemId: "nervous_sleep" },
  chest: { id: "chest", label: "Chest", regionId: "chest", systemId: "cardiovascular" },
  abdomen: { id: "abdomen", label: "Abdomen", regionId: "chest", systemId: "metabolic" },
  upper_back: { id: "upper_back", label: "Upper back", regionId: "chest", systemId: "musculoskeletal" },
  lower_back: { id: "lower_back", label: "Lower back", regionId: "chest", systemId: "musculoskeletal" },
  pelvis: { id: "pelvis", label: "Hips & pelvis", regionId: "leg", systemId: "musculoskeletal" },
  left_shoulder: { id: "left_shoulder", label: "Left shoulder", regionId: "arm", systemId: "musculoskeletal" },
  right_shoulder: { id: "right_shoulder", label: "Right shoulder", regionId: "arm", systemId: "musculoskeletal" },
  left_upper_arm: { id: "left_upper_arm", label: "Left upper arm", regionId: "arm", systemId: "cardiovascular" },
  right_upper_arm: { id: "right_upper_arm", label: "Right upper arm", regionId: "arm", systemId: "cardiovascular" },
  left_elbow: { id: "left_elbow", label: "Left elbow", regionId: "arm", systemId: "musculoskeletal" },
  right_elbow: { id: "right_elbow", label: "Right elbow", regionId: "arm", systemId: "musculoskeletal" },
  left_forearm: { id: "left_forearm", label: "Left forearm", regionId: "arm", systemId: "cardiovascular" },
  right_forearm: { id: "right_forearm", label: "Right forearm", regionId: "arm", systemId: "cardiovascular" },
  left_hand: { id: "left_hand", label: "Left hand", regionId: "arm", systemId: "cardiovascular" },
  right_hand: { id: "right_hand", label: "Right hand", regionId: "arm", systemId: "cardiovascular" },
  left_thigh: { id: "left_thigh", label: "Left thigh", regionId: "leg", systemId: "musculoskeletal" },
  right_thigh: { id: "right_thigh", label: "Right thigh", regionId: "leg", systemId: "musculoskeletal" },
  left_knee: { id: "left_knee", label: "Left knee", regionId: "leg", systemId: "musculoskeletal" },
  right_knee: { id: "right_knee", label: "Right knee", regionId: "leg", systemId: "musculoskeletal" },
  left_calf: { id: "left_calf", label: "Left lower leg", regionId: "leg", systemId: "musculoskeletal" },
  right_calf: { id: "right_calf", label: "Right lower leg", regionId: "leg", systemId: "musculoskeletal" },
  left_foot: { id: "left_foot", label: "Left foot", regionId: "leg", systemId: "musculoskeletal" },
  right_foot: { id: "right_foot", label: "Right foot", regionId: "leg", systemId: "musculoskeletal" },
};

// ---------------------------------------------------------------- geometry helpers
const FRONT = [-Math.PI / 2, Math.PI]; // lathe phi range facing +z (anterior)
const BACK = [Math.PI / 2, Math.PI]; // posterior half
const FULL = [0, Math.PI * 2];

/** Smooth lathe surface from [radius, y] control points (bottom to top). */
function lathe(points, [phiStart, phiLength] = FULL, radial = 40, samples = 36) {
  const curve = new THREE.SplineCurve(points.map(([r, y]) => new THREE.Vector2(r, y)));
  const pts = curve.getPoints(samples).map((p) => new THREE.Vector2(Math.max(p.x, 0.0005), p.y));
  const geo = new THREE.LatheGeometry(pts, radial, phiStart, phiLength);
  geo.computeVertexNormals();
  return geo;
}

const sphere = (r = 1, w = 32, h = 24) => new THREE.SphereGeometry(r, w, h);
const capsule = (r, len) => new THREE.CapsuleGeometry(r, len, 6, 14);

// Anatomical profiles (radius in m, height in m). Torso profiles are scaled in z to be flatter front-to-back.
const P = {
  upperTorso: [
    [0.145, 1.10], [0.152, 1.16], [0.166, 1.23], [0.180, 1.30], [0.190, 1.36], [0.196, 1.405], [0.178, 1.44], [0.120, 1.468], [0.062, 1.49],
  ],
  lowerTorso: [
    [0.160, 0.915], [0.150, 0.96], [0.137, 1.005], [0.134, 1.045], [0.138, 1.08], [0.145, 1.115],
  ],
  pelvis: [
    [0.060, 0.765], [0.135, 0.785], [0.165, 0.83], [0.170, 0.87], [0.163, 0.925],
  ],
  neck: [
    [0.058, 1.46], [0.054, 1.50], [0.050, 1.54], [0.050, 1.58], [0.054, 1.60],
  ],
  skull: [
    [0.001, 1.555], [0.042, 1.565], [0.062, 1.59], [0.076, 1.63], [0.085, 1.68], [0.088, 1.72], [0.082, 1.76], [0.062, 1.795], [0.030, 1.812], [0.001, 1.815],
  ],
  // limbs: local coordinates, joint at y = 0, segment extends to negative y
  upperArm: [[0.034, -0.30], [0.038, -0.27], [0.044, -0.20], [0.047, -0.13], [0.046, -0.07], [0.047, -0.02], [0.044, 0.0]],
  forearm: [[0.025, -0.265], [0.026, -0.235], [0.031, -0.18], [0.039, -0.11], [0.043, -0.05], [0.038, -0.01], [0.033, 0.0]],
  thigh: [[0.050, -0.40], [0.055, -0.36], [0.066, -0.29], [0.077, -0.20], [0.086, -0.11], [0.093, -0.04], [0.094, 0.0]],
  calf: [[0.031, -0.40], [0.032, -0.35], [0.039, -0.27], [0.051, -0.19], [0.059, -0.12], [0.056, -0.06], [0.049, 0.0]],
};

// ---------------------------------------------------------------- materials
const CLAY = "#C9CED6";
const PAIN_COLORS = [
  [3, "#F2B35B"], // mild
  [6, "#F08A4B"], // moderate
  [10, "#E5484D"], // severe
];

function partColor({ selected, hovered, pain }) {
  if (pain) {
    const c = PAIN_COLORS.find(([max]) => pain <= max)?.[1] || "#E5484D";
    return { color: c, emissive: c, emissiveIntensity: selected ? 0.35 : 0.18 };
  }
  if (selected) return { color: "#7EE2B8", emissive: "#10B981", emissiveIntensity: 0.25 };
  if (hovered) return { color: "#E6E9EE", emissive: "#94A3B8", emissiveIntensity: 0.08 };
  return { color: CLAY, emissive: "#000000", emissiveIntensity: 0 };
}

function Part({ id, selectedId, hoveredId, painByRegion, onHover, onSelect, children }) {
  const look = partColor({ selected: selectedId === id, hovered: hoveredId === id, pain: painByRegion[id] });
  const material = useMemo(
    () => new THREE.MeshStandardMaterial({ roughness: 0.62, metalness: 0.04, side: THREE.DoubleSide }),
    [],
  );
  material.color.set(look.color);
  material.emissive.set(look.emissive);
  material.emissiveIntensity = look.emissiveIntensity;

  return (
    <group
      name={id}
      onPointerOver={(e) => {
        e.stopPropagation();
        onHover(id);
        document.body.style.cursor = "pointer";
      }}
      onPointerOut={(e) => {
        e.stopPropagation();
        onHover(null);
        document.body.style.cursor = "auto";
      }}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(id);
      }}
    >
      {typeof children === "function" ? children(material) : null}
    </group>
  );
}

// ---------------------------------------------------------------- body sections
function Head({ m }) {
  const skull = useMemo(() => lathe(P.skull, FULL, 48, 40), []);
  return (
    <group>
      {/* cranium + face: slightly narrow and deep, like a real head */}
      <mesh geometry={skull} material={m} scale={[0.9, 1, 1.1]} />
      {/* jaw and chin */}
      <mesh geometry={sphere(0.06)} material={m} position={[0, 1.605, 0.022]} scale={[1.0, 0.7, 1.0]} />
      <mesh geometry={sphere(0.022)} material={m} position={[0, 1.575, 0.075]} scale={[1.3, 0.9, 0.8]} />
      {/* brow ridge */}
      <mesh geometry={sphere(0.05)} material={m} position={[0, 1.705, 0.058]} scale={[1.35, 0.32, 0.55]} />
      {/* nose */}
      <mesh geometry={new THREE.ConeGeometry(0.014, 0.05, 16)} material={m} position={[0, 1.665, 0.093]} rotation={[0.35, 0, 0]} />
      <mesh geometry={sphere(0.013)} material={m} position={[0, 1.643, 0.097]} scale={[1.4, 0.8, 1]} />
      {/* ears */}
      {[-1, 1].map((s) => (
        <mesh key={`e${s}`} geometry={sphere(0.022)} material={m} position={[s * 0.08, 1.67, -0.005]} scale={[0.35, 1.25, 0.8]} />
      ))}
    </group>
  );
}

function Torso({ partProps }) {
  const upperFront = useMemo(() => lathe(P.upperTorso, FRONT), []);
  const upperBack = useMemo(() => lathe(P.upperTorso, BACK), []);
  const lowerFront = useMemo(() => lathe(P.lowerTorso, FRONT), []);
  const lowerBack = useMemo(() => lathe(P.lowerTorso, BACK), []);
  const pelvis = useMemo(() => lathe(P.pelvis, FULL), []);
  const neck = useMemo(() => lathe(P.neck, FULL, 32), []);
  const torsoScale = [1, 1, 0.64];

  return (
    <>
      <Part id="neck" {...partProps}>
        {(m) => (
          <>
            <mesh geometry={neck} material={m} scale={[1, 1, 0.92]} />
            {/* sternocleidomastoid / trapezius slope */}
            {[-1, 1].map((s) => (
              <mesh key={s} geometry={sphere(0.06)} material={m} position={[s * 0.085, 1.455, -0.02]} scale={[1.7, 0.45, 0.85]} rotation={[0, 0, s * -0.32]} />
            ))}
          </>
        )}
      </Part>
      <Part id="head" {...partProps}>
        {(m) => <Head m={m} />}
      </Part>
      <Part id="chest" {...partProps}>
        {(m) => (
          <>
            <mesh geometry={upperFront} material={m} scale={torsoScale} />
            {/* pectorals */}
            {[-1, 1].map((s) => (
              <mesh key={s} geometry={sphere(0.09)} material={m} position={[s * 0.074, 1.335, 0.052]} scale={[1.08, 0.58, 0.3]} rotation={[0, 0, s * -0.18]} />
            ))}
            {/* clavicles */}
            {[-1, 1].map((s) => (
              <mesh key={`c${s}`} geometry={capsule(0.011, 0.12)} material={m} position={[s * 0.08, 1.445, 0.06]} rotation={[0, 0, s * 1.38]} />
            ))}
          </>
        )}
      </Part>
      <Part id="upper_back" {...partProps}>
        {(m) => (
          <>
            <mesh geometry={upperBack} material={m} scale={torsoScale} />
            {/* scapulae / trapezius */}
            {[-1, 1].map((s) => (
              <mesh key={s} geometry={sphere(0.07)} material={m} position={[s * 0.08, 1.33, -0.075]} scale={[1, 1.2, 0.35]} />
            ))}
          </>
        )}
      </Part>
      <Part id="abdomen" {...partProps}>
        {(m) => (
          <>
            <mesh geometry={lowerFront} material={m} scale={torsoScale} />
            {/* rectus abdominis, external obliques */}
            <mesh geometry={sphere(0.07)} material={m} position={[0, 1.035, 0.05]} scale={[1.0, 1.45, 0.3]} />
            {[-1, 1].map((s) => (
              <mesh key={s} geometry={sphere(0.05)} material={m} position={[s * 0.098, 0.975, 0.025]} scale={[0.75, 1.25, 0.45]} />
            ))}
          </>
        )}
      </Part>
      <Part id="lower_back" {...partProps}>
        {(m) => <mesh geometry={lowerBack} material={m} scale={torsoScale} />}
      </Part>
      <Part id="pelvis" {...partProps}>
        {(m) => (
          <>
            <mesh geometry={pelvis} material={m} scale={[1, 1, 0.7]} />
            {/* glutes */}
            {[-1, 1].map((s) => (
              <mesh key={s} geometry={sphere(0.085)} material={m} position={[s * 0.07, 0.83, -0.05]} scale={[1, 1, 0.75]} />
            ))}
          </>
        )}
      </Part>
    </>
  );
}

function Arm({ side, partProps }) {
  // side: 1 = astronaut's left (screen right when facing us), -1 = right
  const s = side;
  const name = side === 1 ? "left" : "right";
  const upper = useMemo(() => lathe(P.upperArm, FULL, 32), []);
  const fore = useMemo(() => lathe(P.forearm, FULL, 32), []);
  const shoulder = [s * 0.19, 1.415, -0.008];
  const abduct = s * 0.6; // A-pose (~34 deg from the body)

  return (
    <group position={shoulder} rotation={[0, 0, abduct]}>
      <Part id={`${name}_shoulder`} {...partProps}>
        {(m) => (
          <mesh geometry={sphere(0.064)} material={m} position={[0, -0.03, 0]} scale={[0.98, 1.5, 1.05]} />
        )}
      </Part>
      <Part id={`${name}_upper_arm`} {...partProps}>
        {(m) => (
          <>
            <mesh geometry={upper} material={m} scale={[1, 1, 1.08]} />
            {/* biceps / triceps */}
            <mesh geometry={sphere(0.03)} material={m} position={[0, -0.16, 0.016]} scale={[1, 2.4, 0.85]} />
            <mesh geometry={sphere(0.032)} material={m} position={[0, -0.13, -0.015]} scale={[1, 2.6, 0.85]} />
          </>
        )}
      </Part>
      <group position={[0, -0.3, 0]} rotation={[0.12, 0, s * -0.08]}>
        <Part id={`${name}_elbow`} {...partProps}>
          {(m) => <mesh geometry={sphere(0.035)} material={m} scale={[1, 1.15, 1]} />}
        </Part>
        <Part id={`${name}_forearm`} {...partProps}>
          {(m) => (
            <>
              <mesh geometry={fore} material={m} position={[0, -0.01, 0]} scale={[1.12, 1, 0.92]} />
              {/* brachioradialis */}
              <mesh geometry={sphere(0.028)} material={m} position={[s * 0.016, -0.07, 0.008]} scale={[0.9, 2.2, 0.9]} />
            </>
          )}
        </Part>
        <group position={[0, -0.285, 0]} rotation={[0, s * 0.2, 0]}>
          <Part id={`${name}_hand`} {...partProps}>
            {(m) => <Hand m={m} side={s} />}
          </Part>
        </group>
      </group>
    </group>
  );
}

function Hand({ m, side }) {
  const fingers = [
    { x: 0.021, len: [0.044, 0.028, 0.021], r: 0.0078 }, // index
    { x: 0.007, len: [0.048, 0.031, 0.023], r: 0.0081 }, // middle
    { x: -0.007, len: [0.045, 0.029, 0.021], r: 0.0077 }, // ring
    { x: -0.02, len: [0.036, 0.023, 0.018], r: 0.0068 }, // little
  ];
  return (
    <group scale={[side, 1, 1]}>
      {/* wrist and palm: long, flat */}
      <mesh geometry={sphere(0.024)} material={m} position={[0, -0.004, 0]} scale={[1.15, 0.8, 0.7]} />
      <mesh geometry={sphere(0.045)} material={m} position={[0, -0.052, 0]} scale={[0.9, 1.15, 0.36]} />
      {fingers.map((f, i) => {
        let y = -0.1;
        return (
          <group key={i} position={[f.x, 0, 0.002]} rotation={[0.1 + i * 0.02, 0, (i - 1.5) * -0.035]}>
            {f.len.map((l, j) => {
              const r = f.r * (1 - j * 0.1);
              const node = <mesh key={j} geometry={capsule(r, Math.max(l - 2 * r, 0.002))} material={m} position={[0, y - l / 2, 0.0025 * j]} />;
              y -= l * 0.97;
              return node;
            })}
          </group>
        );
      })}
      {/* thumb along the side of the palm */}
      <group position={[0.03, -0.035, 0.012]} rotation={[0.35, 0.3, -0.42]}>
        <mesh geometry={capsule(0.0105, 0.026)} material={m} position={[0, -0.018, 0]} />
        <mesh geometry={capsule(0.0092, 0.018)} material={m} position={[0, -0.046, 0.003]} />
      </group>
    </group>
  );
}

function Leg({ side, partProps }) {
  const s = side;
  const name = side === 1 ? "left" : "right";
  const thigh = useMemo(() => lathe(P.thigh, FULL, 36), []);
  const calf = useMemo(() => lathe(P.calf, FULL, 36), []);
  const hip = [s * 0.095, 0.88, 0];

  return (
    <group position={hip} rotation={[0, 0, s * 0.035]}>
      <Part id={`${name}_thigh`} {...partProps}>
        {(m) => (
          <>
            <mesh geometry={thigh} material={m} scale={[1, 1, 1.05]} />
            {/* quadriceps (vastus medialis tear-drop) and hamstrings */}
            <mesh geometry={sphere(0.055)} material={m} position={[0, -0.18, 0.024]} scale={[1, 2.6, 0.75]} />
            <mesh geometry={sphere(0.034)} material={m} position={[-s * 0.028, -0.34, 0.022]} scale={[1, 1.5, 0.75]} />
            <mesh geometry={sphere(0.055)} material={m} position={[0, -0.17, -0.026]} scale={[1, 2.5, 0.7]} />
          </>
        )}
      </Part>
      <group position={[0, -0.415, 0]}>
        <Part id={`${name}_knee`} {...partProps}>
          {(m) => (
            <>
              <mesh geometry={sphere(0.048)} material={m} scale={[1, 1.15, 0.95]} />
              {/* patella */}
              <mesh geometry={sphere(0.022)} material={m} position={[0, 0.008, 0.036]} scale={[1, 1.2, 0.5]} />
            </>
          )}
        </Part>
        <Part id={`${name}_calf`} {...partProps}>
          {(m) => (
            <>
              <mesh geometry={calf} material={m} position={[0, -0.02, 0]} scale={[1, 1, 1.05]} />
              {/* gastrocnemius (posterior) and tibialis (anterior) */}
              <mesh geometry={sphere(0.046)} material={m} position={[0, -0.12, -0.02]} scale={[1, 2.0, 0.8]} />
              <mesh geometry={sphere(0.022)} material={m} position={[s * 0.012, -0.16, 0.03]} scale={[1, 3, 0.8]} />
            </>
          )}
        </Part>
        <group position={[0, -0.43, 0]}>
          <Part id={`${name}_foot`} {...partProps}>
            {(m) => <Foot m={m} side={s} />}
          </Part>
        </group>
      </group>
    </group>
  );
}

function Foot({ m, side }) {
  return (
    <group rotation={[0, side * 0.12, 0]}>
      {/* ankle, heel, arch, forefoot */}
      <mesh geometry={sphere(0.034)} material={m} position={[0, 0.0, 0]} scale={[1.05, 0.9, 1]} />
      <mesh geometry={sphere(0.034)} material={m} position={[0, -0.03, -0.03]} scale={[0.95, 0.75, 1]} />
      <mesh geometry={sphere(0.05)} material={m} position={[0, -0.04, 0.05]} scale={[0.9, 0.42, 1.65]} />
      {/* toes */}
      {[0.022, 0.008, -0.006, -0.018, -0.028].map((x, i) => (
        <mesh
          key={i}
          geometry={sphere(i === 0 ? 0.012 : 0.0085)}
          material={m}
          position={[x * side, -0.05, 0.128 - i * 0.006]}
          scale={[1, 0.8, 1.25]}
        />
      ))}
    </group>
  );
}

function BodyScene({ selectedId, hoveredId, painByRegion, onHover, onSelect }) {
  const partProps = { selectedId, hoveredId, painByRegion, onHover, onSelect };
  return (
    <group position={[0, -0.92, 0]}>
      <Torso partProps={partProps} />
      <Arm side={1} partProps={partProps} />
      <Arm side={-1} partProps={partProps} />
      <Leg side={1} partProps={partProps} />
      <Leg side={-1} partProps={partProps} />
      {/* floor shadow */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.0, 0]}>
        <circleGeometry args={[0.45, 48]} />
        <meshBasicMaterial color="#000000" transparent opacity={0.35} />
      </mesh>
    </group>
  );
}

class WebGLErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  render() {
    return this.state.hasError ? this.props.fallback : this.props.children;
  }
}

/**
 * Canvas with the sculpted body. Same name/props as the previous model so the dashboard keeps working.
 * painReports: [{region, intensity}] tint the parts that hurt (amber -> red by intensity).
 */
export function HoloBodyCanvas({ selectedPartId, onSelectPart, painReports = [], measuring = false }) {
  const [hoveredId, setHoveredId] = useState(null);
  const controls = useRef(null);
  const painByRegion = useMemo(
    () => Object.fromEntries(painReports.map((r) => [r.region, r.intensity])),
    [painReports],
  );
  const label = ANATOMICAL_PARTS_META[hoveredId || selectedPartId]?.label;

  const turn = (angle) => {
    const c = controls.current;
    if (!c) return;
    const r = Math.hypot(c.object.position.x, c.object.position.z);
    c.object.position.set(Math.sin(angle) * r, c.object.position.y, Math.cos(angle) * r);
    c.update();
  };

  return (
    <div className="relative h-[440px] w-full sm:h-[560px]">
      <div className="pointer-events-none absolute inset-x-3 top-3 z-10 flex items-center justify-between gap-2">
        <span className="rounded-full bg-black/55 px-3 py-1 text-xs text-slate-200 backdrop-blur">
          {measuring ? "Scanning…" : label || "Tap the body where it hurts"}
        </span>
        <div className="pointer-events-auto flex rounded-full bg-black/55 p-0.5 text-xs backdrop-blur" role="group" aria-label="View">
          <button type="button" onClick={() => turn(0)} className="min-h-[30px] rounded-full px-3 text-slate-200 hover:text-white cursor-pointer">
            Front
          </button>
          <button type="button" onClick={() => turn(Math.PI)} className="min-h-[30px] rounded-full px-3 text-slate-200 hover:text-white cursor-pointer">
            Back
          </button>
        </div>
      </div>
      <WebGLErrorBoundary
        fallback={<p className="flex h-full items-center justify-center text-sm text-slate-400">3D view unavailable on this device.</p>}
      >
        <Canvas camera={{ position: [0, 0.02, 3.1], fov: 36 }} gl={{ alpha: true, antialias: true }} dpr={[1, 2]}>
          <hemisphereLight args={["#F8FAFC", "#1E293B", 0.75]} />
          <directionalLight position={[1.6, 2.4, 2.6]} intensity={1.6} />
          <directionalLight position={[-2, 1.2, -2.4]} intensity={0.7} color="#BAE6FD" />
          <directionalLight position={[0, -1, 2]} intensity={0.25} />
          <BodyScene
            selectedId={selectedPartId}
            hoveredId={hoveredId}
            painByRegion={painByRegion}
            onHover={setHoveredId}
            onSelect={(id) => onSelectPart?.(id, ANATOMICAL_PARTS_META[id])}
          />
          <OrbitControls ref={controls} enablePan={false} minDistance={1.3} maxDistance={4} target={[0, 0, 0]} />
        </Canvas>
      </WebGLErrorBoundary>
    </div>
  );
}
