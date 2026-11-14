import React, { Component, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import {
  Activity,
  CheckCircle2,
  Cpu,
  RotateCw,
  Scan,
  ShieldAlert,
  Sparkles,
} from "lucide-react";

const STATUS_HEX = {
  NOMINAL: "#059669",
  WARNING: "#D97706",
  CRITICAL: "#DC2626",
};

const SYSTEM_NODES = [
  { id: "nervous_sleep", label: "Nervous / Sleep", pos: [0, 1.56, 0.14], svgPos: [130, 42] },
  { id: "respiratory", label: "Respiratory / Thermal", pos: [-0.14, 1.02, 0.24], svgPos: [108, 102] },
  { id: "cardiovascular", label: "Cardiovascular", pos: [0.12, 0.96, 0.28], svgPos: [148, 112] },
  { id: "musculoskeletal", label: "EVA Shoulders / Bone", pos: [-0.46, 1.15, 0.08], svgPos: [72, 92] },
  { id: "metabolic", label: "Metabolic / Nutrition", pos: [0, 0.45, 0.26], svgPos: [130, 165] },
  { id: "radiation", label: "Radiation Shield", pos: [0.58, 0.72, 0], svgPos: [204, 136] },
];

class WebGLErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

function HoloAstronautScene({ systems, selectedSystem, onSelectSystem, autoRotate }) {
  const groupRef = useRef();

  useFrame((_, delta) => {
    if (groupRef.current && autoRotate) {
      groupRef.current.rotation.y += delta * 0.22;
    }
  });

  const radStatus = systems?.radiation?.status || "NOMINAL";
  const radColor = STATUS_HEX[radStatus];

  return (
    <group ref={groupRef} position={[0, -0.35, 0]}>
      {/* Cleanroom Bio-Telemetry Floor Rings */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.08, 0]}>
        <ringGeometry args={[0.75, 0.82, 48]} />
        <meshBasicMaterial color="#0D9488" transparent opacity={0.35} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.08, 0]}>
        <ringGeometry args={[1.05, 1.08, 48]} />
        <meshBasicMaterial color={radColor} transparent opacity={0.4} />
      </mesh>

      {/* Head */}
      <mesh position={[0, 1.54, 0]}>
        <sphereGeometry args={[0.23, 24, 24]} />
        <meshStandardMaterial color="#115E59" emissive="#10B981" emissiveIntensity={0.18} wireframe transparent opacity={0.78} />
      </mesh>
      {/* Neck */}
      <mesh position={[0, 1.28, 0]}>
        <cylinderGeometry args={[0.09, 0.11, 0.18, 16]} />
        <meshStandardMaterial color="#0F766E" emissive="#14B8A6" emissiveIntensity={0.15} transparent opacity={0.72} />
      </mesh>
      {/* Upper Torso / Chest */}
      <mesh position={[0, 0.86, 0]}>
        <boxGeometry args={[0.64, 0.66, 0.34]} />
        <meshStandardMaterial color="#115E59" emissive="#0EA5E9" emissiveIntensity={0.15} wireframe transparent opacity={0.72} />
      </mesh>
      {/* Abdomen / Metabolic Core */}
      <mesh position={[0, 0.34, 0]}>
        <cylinderGeometry args={[0.25, 0.22, 0.42, 18]} />
        <meshStandardMaterial color="#0F766E" emissive="#10B981" emissiveIntensity={0.14} wireframe transparent opacity={0.7} />
      </mesh>
      {/* Pelvis */}
      <mesh position={[0, 0.04, 0]}>
        <boxGeometry args={[0.5, 0.2, 0.28]} />
        <meshStandardMaterial color="#115E59" emissive="#0EA5E9" emissiveIntensity={0.12} wireframe transparent opacity={0.68} />
      </mesh>

      {/* Shoulders, Arms & Legs */}
      {[-1, 1].map((side) => (
        <group key={side}>
          <mesh position={[side * 0.42, 1.12, 0]}>
            <sphereGeometry args={[0.13, 16, 16]} />
            <meshStandardMaterial
              color={STATUS_HEX[systems?.musculoskeletal?.status || "NOMINAL"]}
              emissive={STATUS_HEX[systems?.musculoskeletal?.status || "NOMINAL"]}
              emissiveIntensity={0.35}
              transparent
              opacity={0.8}
            />
          </mesh>
          <mesh position={[side * 0.48, 0.66, 0]} rotation={[0, 0, side * 0.1]}>
            <cylinderGeometry args={[0.09, 0.075, 0.78, 14]} />
            <meshStandardMaterial color="#0F766E" emissive="#14B8A6" emissiveIntensity={0.15} wireframe transparent opacity={0.7} />
          </mesh>
          <mesh position={[side * 0.17, -0.56, 0]}>
            <cylinderGeometry args={[0.11, 0.085, 0.96, 14]} />
            <meshStandardMaterial color="#0F766E" emissive="#14B8A6" emissiveIntensity={0.15} wireframe transparent opacity={0.7} />
          </mesh>
        </group>
      ))}

      {/* Radiation Exo-Shield Ring */}
      <mesh rotation={[Math.PI / 2.4, 0.2, 0]} position={[0, 0.72, 0]}>
        <torusGeometry args={[0.88, 0.018, 12, 64]} />
        <meshStandardMaterial color={radColor} emissive={radColor} emissiveIntensity={0.55} transparent opacity={0.85} />
      </mesh>

      {/* 6 Interactive Anatomical Hotspots */}
      {SYSTEM_NODES.map((node) => {
        const status = systems?.[node.id]?.status || "NOMINAL";
        const color = STATUS_HEX[status];
        const isSelected = selectedSystem === node.id;
        return (
          <group key={node.id} position={node.pos}>
            <mesh
              onClick={(e) => {
                e.stopPropagation();
                onSelectSystem(node.id);
              }}
              onPointerOver={() => {
                document.body.style.cursor = "pointer";
              }}
              onPointerOut={() => {
                document.body.style.cursor = "auto";
              }}
            >
              <sphereGeometry args={[isSelected ? 0.11 : 0.085, 20, 20]} />
              <meshStandardMaterial color={color} emissive={color} emissiveIntensity={isSelected ? 1.1 : 0.65} />
            </mesh>
            <Html distanceFactor={5.2} position={[0, 0.14, 0]} center>
              <button
                type="button"
                onClick={() => onSelectSystem(node.id)}
                className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold tracking-wide whitespace-nowrap border shadow-sm transition-all cursor-pointer ${
                  isSelected
                    ? "bg-[#113D2E] text-white border-[#113D2E]"
                    : "bg-white/95 text-[#113D2E] border-[#CBE2D5] hover:border-[#113D2E]"
                }`}
              >
                <span
                  className="inline-block w-1.5 h-1.5 rounded-full mr-1 align-middle"
                  style={{ backgroundColor: color }}
                />
                {node.label}
              </button>
            </Html>
          </group>
        );
      })}
    </group>
  );
}

function SvgHoloFallback({ systems, selectedSystem, onSelectSystem }) {
  return (
    <div className="relative w-full h-[340px] flex items-center justify-center bg-gradient-to-b from-[#EAF6FA] to-[#EFF9F2] rounded-2xl border border-[#D5E8DD]">
      <svg viewBox="0 0 260 320" className="h-[310px] w-auto">
        <defs>
          <radialGradient id="ecoGlow" cx="50%" cy="45%" r="50%">
            <stop offset="0%" stopColor="#86EFAC" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#EAF6FA" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="130" cy="145" r="115" fill="url(#ecoGlow)" />
        <circle cx="130" cy="42" r="21" fill="#FFFFFF" stroke="#0F766E" strokeWidth="2" />
        <rect x="96" y="72" width="68" height="82" rx="16" fill="#FFFFFF" stroke="#0F766E" strokeWidth="2" />
        <rect x="103" y="156" width="54" height="36" rx="10" fill="#FFFFFF" stroke="#0F766E" strokeWidth="2" />
        <line x1="96" y1="84" x2="66" y2="164" stroke="#0F766E" strokeWidth="12" strokeLinecap="round" opacity="0.35" />
        <line x1="164" y1="84" x2="194" y2="164" stroke="#0F766E" strokeWidth="12" strokeLinecap="round" opacity="0.35" />
        <line x1="114" y1="192" x2="108" y2="290" stroke="#0F766E" strokeWidth="15" strokeLinecap="round" opacity="0.35" />
        <line x1="146" y1="192" x2="152" y2="290" stroke="#0F766E" strokeWidth="15" strokeLinecap="round" opacity="0.35" />
        <ellipse
          cx="130"
          cy="145"
          rx="95"
          ry="40"
          fill="none"
          stroke={STATUS_HEX[systems?.radiation?.status || "NOMINAL"]}
          strokeWidth="1.8"
          strokeDasharray="4 4"
        />
        {SYSTEM_NODES.map((node) => {
          const st = systems?.[node.id]?.status || "NOMINAL";
          const color = STATUS_HEX[st];
          const active = selectedSystem === node.id;
          return (
            <g key={node.id} onClick={() => onSelectSystem(node.id)} style={{ cursor: "pointer" }}>
              <circle cx={node.svgPos[0]} cy={node.svgPos[1]} r={active ? 14 : 10} fill={color} opacity="0.22" />
              <circle cx={node.svgPos[0]} cy={node.svgPos[1]} r={active ? 7 : 5} fill={color} stroke="#fff" strokeWidth={2} />
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function BodyModel3D({
  state,
  selectedSystem,
  onSelectSystem,
  onTriggerMeasurement,
}) {
  const [autoRotate, setAutoRotate] = useState(true);
  const [measuring, setMeasuring] = useState(false);
  const [lastReading, setLastReading] = useState(null);
  const [showDeconModal, setShowDeconModal] = useState(false);
  const [deconChecks, setDeconChecks] = useState([]);

  const systems = state?.clinical_evaluation?.systems || {};
  const sysGuide = state?.systems_guide?.[selectedSystem] || {};
  const activeSys = systems[selectedSystem] || Object.values(systems)[0];
  const deconRequired = Boolean(state?.clinical_evaluation?.decontamination_required);
  const deconChecklist = state?.clinical_evaluation?.decontamination_checklist || [];

  const executeScan = async () => {
    setMeasuring(true);
    try {
      const res = await onTriggerMeasurement(selectedSystem);
      setLastReading(res);
    } finally {
      setMeasuring(false);
    }
  };

  const handleScanClick = () => {
    if (deconRequired) {
      setDeconChecks(new Array(deconChecklist.length).fill(false));
      setShowDeconModal(true);
      return;
    }
    executeScan();
  };

  const allDeconChecked = deconChecks.length > 0 && deconChecks.every(Boolean);

  return (
    <section className="eco-card rounded-3xl p-5 flex flex-col gap-3.5">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <span className="text-[11px] uppercase tracking-widest text-[#059669] font-bold flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5" /> Interactive 3D Anatomical Scanner
          </span>
          <h2 className="text-lg font-bold text-[#113D2E]">
            Inspect Body Systems &amp; Trigger Scan
          </h2>
        </div>
        <button
          type="button"
          onClick={() => setAutoRotate((r) => !r)}
          className="min-h-[44px] px-3.5 rounded-full border border-[#D5E8DD] bg-[#EFF9F2] hover:border-[#113D2E] text-xs font-semibold text-[#113D2E] flex items-center gap-1.5 cursor-pointer"
        >
          <RotateCw className={`w-3.5 h-3.5 ${autoRotate ? "text-[#059669]" : "text-[#476458]"}`} />
          {autoRotate ? "Orbit: Auto" : "Orbit: Manual"}
        </button>
      </div>

      {/* Quick System Selector Pills */}
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5">
        {SYSTEM_NODES.map((node) => {
          const st = systems[node.id]?.status || "NOMINAL";
          const isSelected = selectedSystem === node.id;
          return (
            <button
              key={node.id}
              type="button"
              onClick={() => onSelectSystem(node.id)}
              className={`min-h-[44px] px-2 py-1.5 rounded-2xl border text-[11px] font-semibold flex flex-col items-center justify-center gap-1 transition-all cursor-pointer ${
                isSelected
                  ? "bg-[#113D2E] border-[#113D2E] text-white shadow-sm"
                  : "bg-[#F7FBF9] border-[#D5E8DD] text-[#113D2E] hover:bg-[#EFF9F2]"
              }`}
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: STATUS_HEX[st] }}
              />
              <span className="truncate w-full text-center">{node.label.split("/")[0].trim()}</span>
            </button>
          );
        })}
      </div>

      {/* 3D Canvas in Light Biophilic Cleanroom Palette */}
      <div className="relative h-[340px] w-full rounded-2xl overflow-hidden bg-gradient-to-b from-[#EAF6FA] via-[#F4FBF7] to-[#E6F5EC] border border-[#D5E8DD]">
        <WebGLErrorBoundary
          fallback={<SvgHoloFallback systems={systems} selectedSystem={selectedSystem} onSelectSystem={onSelectSystem} />}
        >
          <Canvas camera={{ position: [0, 0.55, 3.65], fov: 42 }}>
            <ambientLight intensity={1.1} />
            <pointLight position={[3, 4, 4]} intensity={1.2} color="#10B981" />
            <pointLight position={[-3, -2, -2]} intensity={0.8} color="#38BDF8" />
            <HoloAstronautScene
              systems={systems}
              selectedSystem={selectedSystem}
              onSelectSystem={onSelectSystem}
              autoRotate={autoRotate}
            />
            <OrbitControls enablePan={false} minDistance={2.4} maxDistance={5.2} />
          </Canvas>
        </WebGLErrorBoundary>

        {/* Legend overlay */}
        <div className="absolute bottom-2.5 left-2.5 right-2.5 flex items-center justify-between text-[11px] pointer-events-none">
          <div className="flex items-center gap-2.5 bg-white/90 border border-[#D5E8DD] px-3 py-1 rounded-full shadow-xs font-medium">
            <span className="flex items-center gap-1 text-[#065F46]">
              <span className="w-2 h-2 rounded-full bg-[#059669]" /> Nominal
            </span>
            <span className="flex items-center gap-1 text-[#92400E]">
              <span className="w-2 h-2 rounded-full bg-[#D97706]" /> Warning
            </span>
            <span className="flex items-center gap-1 text-[#991B1B]">
              <span className="w-2 h-2 rounded-full bg-[#DC2626]" /> Critical
            </span>
          </div>
          <span className="bg-white/90 border border-[#D5E8DD] px-2.5 py-1 rounded-full text-[#476458] hidden sm:inline">
            Drag to rotate • Scroll to zoom
          </span>
        </div>
      </div>

      {/* Selected System Clinical Detail & Trigger */}
      {activeSys && (
        <div className="bg-[#EFF9F2] border border-[#CBE2D5] rounded-2xl p-4 space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span
                  className="px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-white"
                  style={{
                    color: STATUS_HEX[activeSys.status],
                    border: `1px solid ${STATUS_HEX[activeSys.status]}55`,
                  }}
                >
                  {activeSys.status}
                </span>
                <h3 className="font-bold text-sm text-[#113D2E]">{activeSys.name}</h3>
              </div>
              <p className="text-xs text-[#334E44] mt-1">{activeSys.summary}</p>
            </div>

            <button
              type="button"
              onClick={handleScanClick}
              disabled={measuring}
              className="min-h-[44px] px-4 rounded-full bg-[#113D2E] hover:bg-[#19533F] text-white font-bold text-xs flex items-center gap-1.5 shrink-0 cursor-pointer disabled:opacity-60 shadow-sm"
            >
              <Scan className="w-4 h-4 text-[#C8EE90]" />
              {measuring ? "Scanning..." : deconRequired ? "Decon & Scan" : "Run Manual Scan"}
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
            <div className="bg-white p-3 rounded-xl border border-[#D5E8DD]">
              <div className="text-[10px] uppercase tracking-wider text-[#059669] font-bold mb-1">
                How to Measure ({activeSys.checs_device})
              </div>
              <p className="text-[#334E44] leading-relaxed">{sysGuide.how_to_measure}</p>
            </div>
            <div className="bg-[#EAF6FA] p-3 rounded-xl border border-[#C7E4EE]">
              <div className="text-[10px] uppercase tracking-wider text-[#0369A1] font-bold mb-1">
                Why It Matters ({activeSys.reference_standard})
              </div>
              <p className="text-[#1E4352] leading-relaxed">{sysGuide.why_it_matters}</p>
            </div>
          </div>

          <div className="flex items-start gap-2 text-xs bg-white border border-[#D5E8DD] rounded-xl p-3">
            <Sparkles className="w-4 h-4 text-[#059669] shrink-0 mt-0.5" />
            <div>
              <span className="font-bold text-[#113D2E]">Recommended Crew Action: </span>
              <span className="text-[#334E44]">{activeSys.recommended_action}</span>
            </div>
          </div>

          {lastReading && lastReading.system_id === selectedSystem && (
            <div className="flex items-center gap-2 text-xs bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] rounded-xl p-2.5 font-mono-telemetry">
              <Activity className="w-4 h-4 text-[#059669] shrink-0" />
              <span>{lastReading.reading_summary}</span>
            </div>
          )}
        </div>
      )}

      {/* Mandatory Planetary Surface Regolith Decontamination Modal */}
      {showDeconModal && (
        <div className="fixed inset-0 z-50 bg-[#113D2E]/45 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-[#D5E8DD] rounded-3xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-start gap-3">
              <ShieldAlert className="w-6 h-6 text-[#D97706] shrink-0 mt-0.5" />
              <div>
                <span className="text-[11px] uppercase tracking-widest text-[#B45309] font-bold">
                  Planetary Surface Guardrail
                </span>
                <h3 className="text-lg font-bold text-[#113D2E]">
                  Mandatory Regolith &amp; Dust Decontamination Checklist
                </h3>
                <p className="text-xs text-[#476458] mt-1">
                  Abrasive lunar regolith and Martian perchlorates contaminate capillary glucose strips and NIBP cuffs. Confirm all 4 steps before initiating exam.
                </p>
              </div>
            </div>

            <div className="space-y-2">
              {deconChecklist.map((step, idx) => (
                <label
                  key={idx}
                  className="flex items-start gap-3 p-3 rounded-xl bg-[#F7FBF9] border border-[#D5E8DD] hover:border-[#113D2E] cursor-pointer text-xs text-[#113D2E]"
                >
                  <input
                    type="checkbox"
                    checked={Boolean(deconChecks[idx])}
                    onChange={(e) => {
                      const next = [...deconChecks];
                      next[idx] = e.target.checked;
                      setDeconChecks(next);
                    }}
                    className="mt-0.5 w-4 h-4 accent-[#113D2E]"
                  />
                  <span>{step}</span>
                </label>
              ))}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowDeconModal(false)}
                className="min-h-[44px] px-4 rounded-full border border-[#D5E8DD] text-xs font-semibold text-[#113D2E] hover:bg-[#EFF9F2] cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!allDeconChecked}
                onClick={async () => {
                  setShowDeconModal(false);
                  await executeScan();
                }}
                className="min-h-[44px] px-5 rounded-full bg-[#113D2E] hover:bg-[#19533F] disabled:bg-slate-200 disabled:text-slate-400 text-white font-bold text-xs flex items-center gap-1.5 cursor-pointer"
              >
                <CheckCircle2 className="w-4 h-4 text-[#C8EE90]" />
                Confirm Clean Airlock &amp; Execute Scan
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
