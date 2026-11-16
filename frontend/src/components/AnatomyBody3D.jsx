import { Component, Suspense, useMemo, useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";

/*
 * Realistic anatomical body: the MakeHuman base mesh (CC0 1.0), split into 25 selectable parts by the bone
 * weights of its default skeleton (frontend/scripts/build_anatomy_model.py -> public/models/anatomy.glb).
 * Node names are the region ids used by the backend (backend/app/engine/body_regions.py).
 */
const MODEL_URL = `${import.meta.env.BASE_URL}models/anatomy.glb`;

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

// ---------------------------------------------------------------- look
const CLAY = "#C4C8CE";
const PAIN_COLORS = [
  [3, "#F2B35B"], // mild
  [6, "#F08A4B"], // moderate
  [10, "#E5484D"], // severe
];

function partLook({ selected, hovered, pain }) {
  if (pain) {
    const c = PAIN_COLORS.find(([max]) => pain <= max)?.[1] || "#E5484D";
    return { color: c, emissive: c, emissiveIntensity: selected ? 0.32 : 0.16 };
  }
  if (selected) return { color: "#86E3BE", emissive: "#10B981", emissiveIntensity: 0.22 };
  if (hovered) return { color: "#E2E5EA", emissive: "#94A3B8", emissiveIntensity: 0.07 };
  return { color: CLAY, emissive: "#000000", emissiveIntensity: 0 };
}

function BodyPart({ node, selectedId, hoveredId, painByRegion, onHover, onSelect }) {
  const id = node.name;
  const material = useMemo(() => new THREE.MeshStandardMaterial({ roughness: 0.58, metalness: 0.02 }), []);
  const look = partLook({ selected: selectedId === id, hovered: hoveredId === id, pain: painByRegion[id] });
  material.color.set(look.color);
  material.emissive.set(look.emissive);
  material.emissiveIntensity = look.emissiveIntensity;

  return (
    <mesh
      geometry={node.geometry}
      material={material}
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
    />
  );
}

function BodyModel(props) {
  const { nodes } = useGLTF(MODEL_URL);
  const parts = useMemo(
    () => Object.values(nodes).filter((n) => n.isMesh && ANATOMICAL_PARTS_META[n.name]),
    [nodes],
  );
  return (
    <group position={[0, -0.9, 0]}>
      {parts.map((node) => (
        <BodyPart key={node.name} node={node} {...props} />
      ))}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.001, 0]}>
        <circleGeometry args={[0.42, 48]} />
        <meshBasicMaterial color="#000000" transparent opacity={0.35} />
      </mesh>
    </group>
  );
}
useGLTF.preload(MODEL_URL);

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
 * Canvas with the anatomical body. Same name/props as the previous model so the dashboard keeps working.
 * painReports: [{region, intensity}] tint the parts that hurt (amber -> red by intensity).
 */
export function HoloBodyCanvas({ selectedPartId, onSelectPart, painReports = [], measuring = false }) {
  const [hoveredId, setHoveredId] = useState(null);
  const controls = useRef(null);
  const painByRegion = useMemo(() => Object.fromEntries(painReports.map((r) => [r.region, r.intensity])), [painReports]);
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
          <hemisphereLight args={["#F8FAFC", "#1E293B", 0.7]} />
          <directionalLight position={[1.4, 2.6, 2.8]} intensity={1.7} />
          <directionalLight position={[-2.2, 1.6, -2.6]} intensity={1.25} color="#E2E8F0" />
          <directionalLight position={[2.4, 1.2, -2.2]} intensity={0.6} color="#BAE6FD" />
          <directionalLight position={[0, -1, 2]} intensity={0.22} />
          <Suspense fallback={null}>
            <BodyModel
              selectedId={selectedPartId}
              hoveredId={hoveredId}
              painByRegion={painByRegion}
              onHover={setHoveredId}
              onSelect={(id) => onSelectPart?.(id, ANATOMICAL_PARTS_META[id])}
            />
          </Suspense>
          <OrbitControls ref={controls} enablePan={false} minDistance={1.3} maxDistance={4} target={[0, 0, 0]} />
        </Canvas>
      </WebGLErrorBoundary>
    </div>
  );
}
