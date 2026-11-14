import React, { Component, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";
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
  { id: "nervous_sleep", label: "Nervous / Sleep", pos: [0, 1.25, 0.16], svgPos: [130, 42] },
  { id: "respiratory", label: "Respiratory / Thermal", pos: [-0.11, 0.64, 0.2], svgPos: [108, 102] },
  { id: "cardiovascular", label: "Cardiovascular", pos: [0.08, 0.6, 0.21], svgPos: [148, 112] },
  { id: "musculoskeletal", label: "EVA Shoulders / Bone", pos: [-0.33, 0.78, 0.08], svgPos: [76, 92] },
  { id: "metabolic", label: "Metabolic / Nutrition", pos: [0, 0.28, 0.19], svgPos: [130, 160] },
  { id: "radiation", label: "Radiation Shield", pos: [0.76, 0.42, 0], svgPos: [212, 136] },
];

export const ANATOMICAL_PARTS_META = {
  head: { id: "head", label: "Cabeça & Crânio", regionId: "head", systemId: "nervous_sleep" },
  neck: { id: "neck", label: "Pescoço & Cervical", regionId: "head", systemId: "nervous_sleep" },
  chest: { id: "chest", label: "Tórax & Peitoral", regionId: "chest", systemId: "cardiovascular" },
  abdomen: { id: "abdomen", label: "Abdômen & Core", regionId: "chest", systemId: "metabolic" },
  pelvis: { id: "pelvis", label: "Pelve & Quadril", regionId: "leg", systemId: "musculoskeletal" },
  left_shoulder: { id: "left_shoulder", label: "Ombro / Deltoide Esq.", regionId: "arm", systemId: "musculoskeletal" },
  right_shoulder: { id: "right_shoulder", label: "Ombro / Deltoide Dir.", regionId: "arm", systemId: "musculoskeletal" },
  left_upper_arm: { id: "left_upper_arm", label: "Braço Esq. (Bíceps)", regionId: "arm", systemId: "cardiovascular" },
  right_upper_arm: { id: "right_upper_arm", label: "Braço Dir. (Bíceps)", regionId: "arm", systemId: "cardiovascular" },
  left_forearm: { id: "left_forearm", label: "Antebraço Esq.", regionId: "arm", systemId: "cardiovascular" },
  right_forearm: { id: "right_forearm", label: "Antebraço Dir.", regionId: "arm", systemId: "cardiovascular" },
  left_hand: { id: "left_hand", label: "Mão Esquerda", regionId: "arm", systemId: "cardiovascular" },
  right_hand: { id: "right_hand", label: "Mão Direita", regionId: "arm", systemId: "cardiovascular" },
  left_thigh: { id: "left_thigh", label: "Coxa Esquerda", regionId: "leg", systemId: "musculoskeletal" },
  right_thigh: { id: "right_thigh", label: "Coxa Direita", regionId: "leg", systemId: "musculoskeletal" },
  left_calf: { id: "left_calf", label: "Panturrilha Esquerda", regionId: "leg", systemId: "musculoskeletal" },
  right_calf: { id: "right_calf", label: "Panturrilha Direita", regionId: "leg", systemId: "musculoskeletal" },
  left_foot: { id: "left_foot", label: "Pé Esquerdo", regionId: "leg", systemId: "musculoskeletal" },
  right_foot: { id: "right_foot", label: "Pé Direito", regionId: "leg", systemId: "musculoskeletal" },
};

const REGION_PARTS = {
  head: ["head", "neck"],
  chest: ["chest", "abdomen"],
  arm: [
    "left_shoulder",
    "right_shoulder",
    "left_upper_arm",
    "right_upper_arm",
    "left_forearm",
    "right_forearm",
    "left_hand",
    "right_hand",
  ],
  leg: ["pelvis", "left_thigh", "right_thigh", "left_calf", "right_calf", "left_foot", "right_foot"],
  full: Object.keys(ANATOMICAL_PARTS_META),
};

const SYSTEM_PARTS = {
  nervous_sleep: ["head", "neck"],
  cardiovascular: ["chest", "left_upper_arm", "left_forearm"],
  respiratory: ["chest", "neck"],
  musculoskeletal: [
    "left_shoulder",
    "right_shoulder",
    "pelvis",
    "left_thigh",
    "right_thigh",
    "left_calf",
    "right_calf",
  ],
  metabolic: ["abdomen"],
  radiation: Object.keys(ANATOMICAL_PARTS_META),
};

const SCAN_COLUMN_LEVELS = [-1.05, -0.74, -0.44, -0.14, 0.16, 0.46, 0.76, 1.06, 1.36];

/**
 * Sculpted Upper Torso (Chest, Pectorals, Ribcage, Clavicles, Trapezius, Upper Back)
 * Built from scratch with procedural musculature relief.
 */
function createChestGeometry() {
  const profile = [
    new THREE.Vector2(0.01, 0.45),
    new THREE.Vector2(0.205, 0.46), // Lower ribcage
    new THREE.Vector2(0.245, 0.56), // Mid chest / lats
    new THREE.Vector2(0.278, 0.68), // Broad pectorals
    new THREE.Vector2(0.265, 0.79), // Shoulder girdle / clavicle
    new THREE.Vector2(0.145, 0.87), // Trapezius slope
    new THREE.Vector2(0.082, 0.91), // Neck base
    new THREE.Vector2(0.01, 0.92),
  ];

  const geo = new THREE.LatheGeometry(profile, 32);
  const pos = geo.attributes.position;

  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i);
    const y = pos.getY(i);
    let z = pos.getZ(i);

    x *= 1.06;
    z *= 0.62;

    if (z > 0.02) {
      const chestMask =
        Math.exp(-Math.pow((y - 0.65) / 0.12, 2)) *
        Math.exp(-Math.pow((Math.abs(x) - 0.11) / 0.095, 2));
      const sternumGroove =
        Math.exp(-Math.pow(x / 0.028, 2)) *
        Math.exp(-Math.pow((y - 0.63) / 0.15, 2));
      const clavicle =
        Math.exp(-Math.pow((y - 0.79) / 0.025, 2)) *
        Math.exp(-Math.pow((Math.abs(x) - 0.11) / 0.09, 2));
      z += chestMask * 0.044 - sternumGroove * 0.016 + clavicle * 0.012;
    }

    if (z < -0.02) {
      const spineGroove =
        Math.exp(-Math.pow(x / 0.032, 2)) *
        Math.exp(-Math.pow((y - 0.65) / 0.2, 2));
      const scapula =
        Math.exp(-Math.pow((y - 0.68) / 0.11, 2)) *
        Math.exp(-Math.pow((Math.abs(x) - 0.11) / 0.08, 2));
      z += spineGroove * 0.015 - scapula * 0.018;
    }

    pos.setXYZ(i, x, y, z);
  }

  geo.computeVertexNormals();
  return geo;
}

/**
 * Sculpted Abdomen & Obliques (Rectus Abdominis 6-pack + Waist + Lumbar curve)
 */
function createAbdomenGeometry() {
  const profile = [
    new THREE.Vector2(0.01, 0.15),
    new THREE.Vector2(0.198, 0.16), // Lower abdomen / iliac transition
    new THREE.Vector2(0.184, 0.25), // Natural waist
    new THREE.Vector2(0.192, 0.35), // Upper abs
    new THREE.Vector2(0.205, 0.46), // Ribcage junction
    new THREE.Vector2(0.01, 0.47),
  ];

  const geo = new THREE.LatheGeometry(profile, 32);
  const pos = geo.attributes.position;

  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i);
    const y = pos.getY(i);
    let z = pos.getZ(i);

    x *= 1.05;
    z *= 0.62;

    if (z > 0.02) {
      const absColumn =
        Math.exp(-Math.pow((y - 0.32) / 0.13, 2)) *
        Math.exp(-Math.pow((Math.abs(x) - 0.048) / 0.042, 2));
      const lineaAlba =
        Math.exp(-Math.pow(x / 0.018, 2)) *
        Math.exp(-Math.pow((y - 0.31) / 0.14, 2));
      // 3 horizontal tendinous intersections (6-pack rows)
      const rowGrooves =
        (Math.exp(-Math.pow((y - 0.39) / 0.012, 2)) +
          Math.exp(-Math.pow((y - 0.31) / 0.012, 2)) +
          Math.exp(-Math.pow((y - 0.23) / 0.012, 2))) *
        Math.exp(-Math.pow(x / 0.09, 2));
      z += absColumn * 0.024 - lineaAlba * 0.01 - rowGrooves * 0.007;
    }

    if (z < -0.02) {
      const lumbarCurve = Math.exp(-Math.pow((y - 0.28) / 0.12, 2));
      z += lumbarCurve * 0.018;
    }

    pos.setXYZ(i, x, y, z);
  }

  geo.computeVertexNormals();
  return geo;
}

/**
 * Sculpted Pelvis, Iliac Crest & Gluteal Contour
 */
function createPelvisGeometry() {
  const profile = [
    new THREE.Vector2(0.01, -0.07),
    new THREE.Vector2(0.135, -0.04),
    new THREE.Vector2(0.212, 0.04), // Hip / trochanter breadth
    new THREE.Vector2(0.216, 0.11), // Iliac crest
    new THREE.Vector2(0.198, 0.16), // Waist junction
    new THREE.Vector2(0.01, 0.17),
  ];

  const geo = new THREE.LatheGeometry(profile, 30);
  const pos = geo.attributes.position;

  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i);
    const y = pos.getY(i);
    let z = pos.getZ(i);

    x *= 1.05;
    z *= 0.64;

    if (z < -0.02) {
      const gluteRelief =
        Math.exp(-Math.pow((y - 0.03) / 0.085, 2)) *
        Math.exp(-Math.pow((Math.abs(x) - 0.095) / 0.08, 2));
      const cleft =
        Math.exp(-Math.pow(x / 0.022, 2)) *
        Math.exp(-Math.pow((y - 0.02) / 0.08, 2));
      z -= gluteRelief * 0.038 - cleft * 0.016;
    }

    pos.setXYZ(i, x, y, z);
  }

  geo.computeVertexNormals();
  return geo;
}

/**
 * Sculpted Head with Cranium, Jawline, Brow Ridge, Nose Bridge, Eye Sockets, and Lips hint
 */
function createHeadGeometry() {
  const geo = new THREE.SphereGeometry(0.12, 28, 24);
  const pos = geo.attributes.position;

  for (let i = 0; i < pos.count; i++) {
    let x = pos.getX(i);
    let y = pos.getY(i);
    let z = pos.getZ(i);

    y *= 1.28;
    x *= 0.88;
    z *= 0.98;

    if (y < 0) {
      const jawFactor = Math.min(1, Math.abs(y) / 0.15);
      x *= 1 - jawFactor * 0.36;
      if (z > 0) {
        z *= 1 - jawFactor * 0.12;
      } else {
        z *= 1 - jawFactor * 0.45;
      }
    }

    if (z > 0.035) {
      const brow =
        Math.exp(-Math.pow((y - 0.032) / 0.02, 2)) *
        Math.exp(-Math.pow(x / 0.068, 2));
      const eyeSockets =
        Math.exp(-Math.pow((y - 0.012) / 0.018, 2)) *
        Math.exp(-Math.pow((Math.abs(x) - 0.036) / 0.02, 2));
      const nose =
        Math.exp(-Math.pow((y + 0.008) / 0.028, 2)) *
        Math.exp(-Math.pow(x / 0.015, 2));
      const chin =
        Math.exp(-Math.pow((y + 0.11) / 0.025, 2)) *
        Math.exp(-Math.pow(x / 0.028, 2));
      z += brow * 0.014 - eyeSockets * 0.01 + nose * 0.026 + chin * 0.008;
    }

    pos.setXYZ(i, x, y, z);
  }

  geo.computeVertexNormals();
  return geo;
}

function createLimbGeometry(profilePoints, radialSegments = 20) {
  const vecs = profilePoints.map(([r, y]) => new THREE.Vector2(r, y));
  const geo = new THREE.LatheGeometry(vecs, radialSegments);
  geo.computeVertexNormals();
  return geo;
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
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

const PALETTES = {
  eco: {
    body: "#E2F2EA",
    bodyEmissive: "#0F766E",
    bodyEmissiveIntensity: 0.08,
    bodyOpacity: 0.92,
    wire: "#0F766E",
    wireEmissive: "#10B981",
    wireOpacity: 0.22,
    hoverBody: "#A7F3D0",
    hoverEmissive: "#10B981",
    selectedBody: "#34D399",
    selectedEmissive: "#059669",
    selectedWire: "#065F46",
    ring: "#0EA5E9",
    ringEmissive: "#38BDF8",
    ringCap: "#059669",
    ringCapEmissive: "#10B981",
    disc: "#C8EE90",
    scan: "#10B981",
    scanActive: "#C8EE90",
  },
  holo: {
    body: "#1E40AF",
    bodyEmissive: "#0284C7",
    bodyEmissiveIntensity: 0.45,
    bodyOpacity: 0.62,
    wire: "#7DD3FC",
    wireEmissive: "#38BDF8",
    wireOpacity: 0.38,
    hoverBody: "#0EA5E9",
    hoverEmissive: "#38BDF8",
    selectedBody: "#10B981",
    selectedEmissive: "#34D399",
    selectedWire: "#A7F3D0",
    ring: "#38BDF8",
    ringEmissive: "#0EA5E9",
    ringCap: "#34D399",
    ringCapEmissive: "#10B981",
    disc: "#0EA5E9",
    scan: "#34D399",
    scanActive: "#A7F3D0",
  },
};

function HoloAstronautScene({
  systems,
  selectedSystem,
  selectedRegion,
  selectedPartId,
  hoveredPartId,
  onHoverPart,
  onSelectPart,
  onSelectSystem,
  autoRotate,
  measuring,
  palette = "holo",
  showLabels = false,
}) {
  const P = PALETTES[palette] || PALETTES.holo;
  const groupRef = useRef();
  const scanBeamRef = useRef();

  const geometries = useMemo(() => {
    const chest = createChestGeometry();
    const abdomen = createAbdomenGeometry();
    const pelvis = createPelvisGeometry();
    const head = createHeadGeometry();
    const thigh = createLimbGeometry([
      [0.01, 0.01],
      [0.106, -0.02],
      [0.104, -0.14], // Quadriceps sweep
      [0.089, -0.32],
      [0.066, -0.47], // Knee taper
      [0.01, -0.49],
    ]);
    const calf = createLimbGeometry([
      [0.01, 0.01],
      [0.064, -0.02],
      [0.08, -0.15], // Gastrocnemius muscle bulge
      [0.06, -0.32],
      [0.043, -0.48], // Achilles / ankle
      [0.01, -0.5],
    ]);
    const upperArm = createLimbGeometry([
      [0.01, 0.01],
      [0.074, -0.02],
      [0.068, -0.16], // Bicep / tricep curve
      [0.056, -0.29],
      [0.048, -0.38], // Elbow taper
      [0.01, -0.39],
    ]);
    const forearm = createLimbGeometry([
      [0.01, 0.01],
      [0.054, -0.03],
      [0.052, -0.11], // Brachioradialis curve
      [0.04, -0.24],
      [0.032, -0.34], // Wrist taper
      [0.01, -0.35],
    ]);
    return { chest, abdomen, pelvis, head, thigh, calf, upperArm, forearm };
  }, []);

  useEffect(() => {
    return () => {
      Object.values(geometries).forEach((g) => g.dispose());
    };
  }, [geometries]);

  useFrame((state, delta) => {
    if (groupRef.current && autoRotate) {
      groupRef.current.rotation.y += delta * 0.22;
    }
    if (scanBeamRef.current) {
      const speed = measuring ? 3.2 : 1.15;
      const t = state.clock.elapsedTime * speed;
      scanBeamRef.current.position.y = 0.15 + Math.sin(t) * 1.18;
    }
  });

  // Determine which parts are currently highlighted
  const highlightedParts = useMemo(() => {
    if (selectedPartId && ANATOMICAL_PARTS_META[selectedPartId]) {
      return new Set([selectedPartId]);
    }
    if (selectedRegion && REGION_PARTS[selectedRegion]) {
      return new Set(REGION_PARTS[selectedRegion]);
    }
    if (selectedSystem && SYSTEM_PARTS[selectedSystem]) {
      return new Set(SYSTEM_PARTS[selectedSystem]);
    }
    return new Set();
  }, [selectedPartId, selectedRegion, selectedSystem]);

  const getPartMaterials = (partId) => {
    const isExactSelected = selectedPartId === partId;
    const isRegionHighlighted = !selectedPartId && highlightedParts.has(partId);
    const isHovered = hoveredPartId === partId;

    const active = isExactSelected || isRegionHighlighted;

    const solid = {
      color: isExactSelected
        ? P.selectedBody
        : isHovered
        ? P.hoverBody
        : active
        ? P.selectedBody
        : P.body,
      emissive: isExactSelected
        ? P.selectedEmissive
        : isHovered
        ? P.hoverEmissive
        : active
        ? P.selectedEmissive
        : P.bodyEmissive,
      emissiveIntensity: isExactSelected
        ? 0.95
        : isHovered
        ? 0.75
        : active
        ? 0.65
        : P.bodyEmissiveIntensity,
      roughness: 0.35,
      metalness: 0.12,
      transparent: true,
      opacity: isExactSelected || isHovered ? 0.94 : active ? 0.85 : P.bodyOpacity,
    };

    const wire = {
      color: active || isHovered ? P.selectedWire : P.wire,
      emissive: active || isHovered ? P.selectedEmissive : P.wireEmissive,
      emissiveIntensity: active || isHovered ? 0.7 : 0.28,
      wireframe: true,
      transparent: true,
      opacity: active || isHovered ? 0.65 : P.wireOpacity,
    };

    return { solid, wire };
  };

  const bindPartEvents = (partId) => ({
    onClick: (e) => {
      e.stopPropagation();
      const meta = ANATOMICAL_PARTS_META[partId];
      if (meta) {
        onSelectPart?.(partId, meta);
        onSelectSystem?.(meta.systemId);
      }
    },
    onPointerOver: (e) => {
      e.stopPropagation();
      document.body.style.cursor = "pointer";
      onHoverPart?.(partId);
    },
    onPointerOut: (e) => {
      e.stopPropagation();
      document.body.style.cursor = "auto";
      onHoverPart?.(null);
    },
  });

  const radStatus = systems?.radiation?.status || "NOMINAL";
  const radColor = STATUS_HEX[radStatus];
  const heartColor = STATUS_HEX[systems?.cardiovascular?.status || "NOMINAL"];
  const lungColor = STATUS_HEX[systems?.respiratory?.status || "NOMINAL"];
  const brainColor = STATUS_HEX[systems?.nervous_sleep?.status || "NOMINAL"];

  const headMat = getPartMaterials("head");
  const neckMat = getPartMaterials("neck");
  const chestMat = getPartMaterials("chest");
  const abdomenMat = getPartMaterials("abdomen");
  const pelvisMat = getPartMaterials("pelvis");

  return (
    <group ref={groupRef} position={[0, -0.18, 0]}>
      {/* Stacked Concentric Biometric Scanner Column Rings */}
      {SCAN_COLUMN_LEVELS.map((y, idx) => {
        const isCap = idx === 0 || idx === SCAN_COLUMN_LEVELS.length - 1;
        return (
          <mesh key={y} rotation={[Math.PI / 2, 0, 0]} position={[0, y, 0]}>
            <torusGeometry args={[isCap ? 0.82 : 0.72, isCap ? 0.015 : 0.006, 10, 64]} />
            <meshStandardMaterial
              color={isCap ? P.ringCap : P.ring}
              emissive={isCap ? P.ringCapEmissive : P.ringEmissive}
              emissiveIntensity={isCap ? 0.75 : 0.45}
              transparent
              opacity={isCap ? 0.75 : 0.32}
            />
          </mesh>
        );
      })}

      {/* Base Emitter Disc */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.06, 0]}>
        <circleGeometry args={[0.82, 48]} />
        <meshBasicMaterial color={P.disc} transparent opacity={0.22} />
      </mesh>

      {/* Active Sweeping Volumetric Scan Ring */}
      <mesh ref={scanBeamRef} rotation={[Math.PI / 2, 0, 0]} position={[0, 0.2, 0]}>
        <torusGeometry args={[0.68, 0.013, 12, 64]} />
        <meshStandardMaterial
          color={measuring ? P.scanActive : P.scan}
          emissive={measuring ? P.scanActive : P.scan}
          emissiveIntensity={measuring ? 1.5 : 0.9}
          transparent
          opacity={0.85}
        />
      </mesh>

      {/* 1. CHEST / UPPER TORSO */}
      <group {...bindPartEvents("chest")}>
        <mesh geometry={geometries.chest}>
          <meshStandardMaterial {...chestMat.solid} />
        </mesh>
        <mesh geometry={geometries.chest} scale={[1.006, 1.003, 1.006]}>
          <meshStandardMaterial {...chestMat.wire} />
        </mesh>
      </group>

      {/* 2. ABDOMEN / CORE */}
      <group {...bindPartEvents("abdomen")}>
        <mesh geometry={geometries.abdomen}>
          <meshStandardMaterial {...abdomenMat.solid} />
        </mesh>
        <mesh geometry={geometries.abdomen} scale={[1.006, 1.003, 1.006]}>
          <meshStandardMaterial {...abdomenMat.wire} />
        </mesh>
      </group>

      {/* 3. PELVIS / HIPS */}
      <group {...bindPartEvents("pelvis")}>
        <mesh geometry={geometries.pelvis}>
          <meshStandardMaterial {...pelvisMat.solid} />
        </mesh>
        <mesh geometry={geometries.pelvis} scale={[1.006, 1.003, 1.006]}>
          <meshStandardMaterial {...pelvisMat.wire} />
        </mesh>
      </group>

      {/* 4. NECK */}
      <group position={[0, 0.97, 0.01]} rotation={[0.06, 0, 0]} {...bindPartEvents("neck")}>
        <mesh>
          <cylinderGeometry args={[0.066, 0.084, 0.16, 20]} />
          <meshStandardMaterial {...neckMat.solid} />
        </mesh>
        <mesh scale={[1.01, 1, 1.01]}>
          <cylinderGeometry args={[0.066, 0.084, 0.16, 16]} />
          <meshStandardMaterial {...neckMat.wire} />
        </mesh>
      </group>

      {/* 5. HEAD / CRANIUM */}
      <group position={[0, 1.18, 0.015]} {...bindPartEvents("head")}>
        <mesh geometry={geometries.head}>
          <meshStandardMaterial {...headMat.solid} />
        </mesh>
        <mesh geometry={geometries.head} scale={[1.008, 1.008, 1.008]}>
          <meshStandardMaterial {...headMat.wire} />
        </mesh>
        {[-1, 1].map((side) => (
          <mesh key={side} position={[side * 0.106, -0.01, -0.01]} scale={[0.45, 1, 0.65]}>
            <sphereGeometry args={[0.026, 10, 10]} />
            <meshStandardMaterial {...headMat.solid} />
          </mesh>
        ))}
        {/* Internal Brain Core */}
        <mesh position={[0, 0.03, 0]}>
          <sphereGeometry args={[0.052, 14, 14]} />
          <meshStandardMaterial color={brainColor} emissive={brainColor} emissiveIntensity={0.7} transparent opacity={0.45} />
        </mesh>
      </group>

      {/* Internal Heart & Lung Clinical Glow Core */}
      <mesh position={[0.06, 0.62, 0.025]}>
        <sphereGeometry args={[0.052, 14, 14]} />
        <meshStandardMaterial color={heartColor} emissive={heartColor} emissiveIntensity={0.8} transparent opacity={0.5} />
      </mesh>
      {[-1, 1].map((side) => (
        <mesh key={side} position={[side * 0.095, 0.64, 0.0]} scale={[0.75, 1.25, 0.65]}>
          <sphereGeometry args={[0.065, 12, 12]} />
          <meshStandardMaterial color={lungColor} emissive={lungColor} emissiveIntensity={0.45} transparent opacity={0.3} />
        </mesh>
      ))}

      {/* BILATERAL ARMS & LEGS (Each segment individually selectable) */}
      {[-1, 1].map((side) => {
        // Anatomical side: +X is Astronaut's Left, -X is Astronaut's Right
        const prefix = side === 1 ? "left" : "right";
        const shoulderId = `${prefix}_shoulder`;
        const upperArmId = `${prefix}_upper_arm`;
        const forearmId = `${prefix}_forearm`;
        const handId = `${prefix}_hand`;
        const thighId = `${prefix}_thigh`;
        const calfId = `${prefix}_calf`;
        const footId = `${prefix}_foot`;

        const shoulderMat = getPartMaterials(shoulderId);
        const upperArmMat = getPartMaterials(upperArmId);
        const forearmMat = getPartMaterials(forearmId);
        const handMat = getPartMaterials(handId);
        const thighMat = getPartMaterials(thighId);
        const calfMat = getPartMaterials(calfId);
        const footMat = getPartMaterials(footId);

        return (
          <group key={side}>
            {/* Shoulder & Arm Assembly in A-Pose */}
            <group position={[side * 0.275, 0.76, 0]} rotation={[0, 0, side * 0.54]}>
              {/* Deltoid / Shoulder */}
              <group {...bindPartEvents(shoulderId)}>
                <mesh scale={[1.15, 1.05, 0.95]}>
                  <sphereGeometry args={[0.084, 18, 16]} />
                  <meshStandardMaterial {...shoulderMat.solid} />
                </mesh>
                <mesh scale={[1.17, 1.07, 0.97]}>
                  <sphereGeometry args={[0.084, 14, 12]} />
                  <meshStandardMaterial {...shoulderMat.wire} />
                </mesh>
              </group>

              {/* Upper Arm (Biceps / Triceps) */}
              <group {...bindPartEvents(upperArmId)}>
                <mesh geometry={geometries.upperArm}>
                  <meshStandardMaterial {...upperArmMat.solid} />
                </mesh>
                <mesh geometry={geometries.upperArm} scale={[1.012, 1, 1.012]}>
                  <meshStandardMaterial {...upperArmMat.wire} />
                </mesh>
              </group>

              {/* Elbow, Forearm & Hand */}
              <group position={[0, -0.38, 0]} rotation={[-0.14, 0, side * -0.06]}>
                <group {...bindPartEvents(forearmId)}>
                  <mesh>
                    <sphereGeometry args={[0.05, 14, 12]} />
                    <meshStandardMaterial {...forearmMat.solid} />
                  </mesh>
                  <mesh geometry={geometries.forearm}>
                    <meshStandardMaterial {...forearmMat.solid} />
                  </mesh>
                  <mesh geometry={geometries.forearm} scale={[1.012, 1, 1.012]}>
                    <meshStandardMaterial {...forearmMat.wire} />
                  </mesh>
                </group>

                {/* Hand (Palm + Fingers + Thumb) */}
                <group
                  position={[0, -0.38, 0.01]}
                  rotation={[0, 0, side * -0.08]}
                  {...bindPartEvents(handId)}
                >
                  <mesh scale={[0.75, 1.35, 0.42]}>
                    <sphereGeometry args={[0.044, 14, 14]} />
                    <meshStandardMaterial {...handMat.solid} />
                  </mesh>
                  <mesh position={[0, -0.065, 0]} scale={[0.7, 1.15, 0.35]}>
                    <sphereGeometry args={[0.036, 12, 12]} />
                    <meshStandardMaterial {...handMat.solid} />
                  </mesh>
                  <mesh position={[side * -0.032, -0.02, 0.018]} rotation={[0.2, 0, side * -0.45]}>
                    <capsuleGeometry args={[0.01, 0.042, 6, 8]} />
                    <meshStandardMaterial {...handMat.solid} />
                  </mesh>
                </group>
              </group>
            </group>

            {/* Leg Assembly (Thigh -> Knee/Calf -> Foot) */}
            <group position={[side * 0.135, -0.02, 0]} rotation={[0, 0, side * 0.035]}>
              {/* Thigh (Quadriceps / Hamstrings) */}
              <group {...bindPartEvents(thighId)}>
                <mesh>
                  <sphereGeometry args={[0.1, 16, 14]} />
                  <meshStandardMaterial {...thighMat.solid} />
                </mesh>
                <mesh geometry={geometries.thigh}>
                  <meshStandardMaterial {...thighMat.solid} />
                </mesh>
                <mesh geometry={geometries.thigh} scale={[1.012, 1, 1.012]}>
                  <meshStandardMaterial {...thighMat.wire} />
                </mesh>
              </group>

              {/* Knee & Calf */}
              <group position={[0, -0.48, -0.008]}>
                <group {...bindPartEvents(calfId)}>
                  <mesh position={[0, 0, 0.02]} scale={[0.92, 1, 0.95]}>
                    <sphereGeometry args={[0.064, 14, 12]} />
                    <meshStandardMaterial {...calfMat.solid} />
                  </mesh>
                  <mesh geometry={geometries.calf}>
                    <meshStandardMaterial {...calfMat.solid} />
                  </mesh>
                  <mesh geometry={geometries.calf} scale={[1.012, 1, 1.012]}>
                    <meshStandardMaterial {...calfMat.wire} />
                  </mesh>
                </group>

                {/* Ankle & Grounded Foot */}
                <group
                  position={[0, -0.51, 0.055]}
                  rotation={[0, side * -0.08, 0]}
                  {...bindPartEvents(footId)}
                >
                  <mesh scale={[0.72, 0.48, 1.65]}>
                    <sphereGeometry args={[0.062, 14, 12]} />
                    <meshStandardMaterial {...footMat.solid} />
                  </mesh>
                  <mesh scale={[0.74, 0.5, 1.67]}>
                    <sphereGeometry args={[0.062, 12, 10]} />
                    <meshStandardMaterial {...footMat.wire} />
                  </mesh>
                </group>
              </group>
            </group>
          </group>
        );
      })}

      {/* Radiation Exo-Shield Orbital Ring */}
      <mesh rotation={[Math.PI / 2.4, 0.2, 0]} position={[0, 0.42, 0]}>
        <torusGeometry args={[0.84, 0.014, 12, 64]} />
        <meshStandardMaterial color={radColor} emissive={radColor} emissiveIntensity={0.55} transparent opacity={0.75} />
      </mesh>

      {/* Optional Clinical System Hotspots (for Analytics tab) */}
      {showLabels &&
        SYSTEM_NODES.map((node) => {
          const status = systems?.[node.id]?.status || "NOMINAL";
          const color = STATUS_HEX[status];
          const isSelected = selectedSystem === node.id;
          return (
            <group key={node.id} position={node.pos}>
              <mesh
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectSystem?.(node.id);
                }}
              >
                <sphereGeometry args={[isSelected ? 0.065 : 0.048, 18, 18]} />
                <meshStandardMaterial color={color} emissive={color} emissiveIntensity={isSelected ? 1.15 : 0.65} />
              </mesh>
              <Html distanceFactor={4.8} position={[0, 0.11, 0]} center>
                <button
                  type="button"
                  onClick={() => onSelectSystem?.(node.id)}
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
    <div className="relative w-full h-[360px] flex items-center justify-center bg-gradient-to-b from-[#EAF6FA] to-[#EFF9F2] rounded-2xl border border-[#D5E8DD]">
      <svg viewBox="0 0 260 320" className="h-[320px] w-auto">
        <defs>
          <radialGradient id="ecoGlow" cx="50%" cy="45%" r="50%">
            <stop offset="0%" stopColor="#86EFAC" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#EAF6FA" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="130" cy="145" r="115" fill="url(#ecoGlow)" />
        {[56, 98, 140, 182, 224, 272].map((cy) => (
          <ellipse key={cy} cx="130" cy={cy} rx="86" ry="12" fill="none" stroke="#0EA5E9" strokeWidth="1" opacity="0.35" />
        ))}
        <ellipse cx="130" cy="40" rx="16" ry="20" fill="#FFFFFF" stroke="#0F766E" strokeWidth="2" />
        <path
          d="M118 60 L142 60 L158 72 L192 146 L181 152 L156 96 L152 152 L147 188 L152 284 L138 286 L130 198 L122 286 L108 284 L113 188 L108 152 L104 96 L79 152 L68 146 L102 72 Z"
          fill="#FFFFFF"
          stroke="#0F766E"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        {SYSTEM_NODES.map((node) => {
          const st = systems?.[node.id]?.status || "NOMINAL";
          const color = STATUS_HEX[st];
          const active = selectedSystem === node.id;
          return (
            <g key={node.id} onClick={() => onSelectSystem?.(node.id)} style={{ cursor: "pointer" }}>
              <circle cx={node.svgPos[0]} cy={node.svgPos[1]} r={active ? 14 : 10} fill={color} opacity="0.22" />
              <circle cx={node.svgPos[0]} cy={node.svgPos[1]} r={active ? 7 : 5} fill={color} stroke="#fff" strokeWidth={2} />
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function HoloBodyCanvas({
  state,
  selectedSystem,
  selectedRegion,
  selectedPartId,
  onSelectPart,
  onSelectSystem,
  measuring = false,
}) {
  const [hoveredPartId, setHoveredPartId] = useState(null);
  const [autoRotate, setAutoRotate] = useState(true);
  const systems = state?.clinical_evaluation?.systems || {};

  const activePartMeta =
    (hoveredPartId && ANATOMICAL_PARTS_META[hoveredPartId]) ||
    (selectedPartId && ANATOMICAL_PARTS_META[selectedPartId]);

  return (
    <div className="relative h-[470px] w-full">
      {/* Top Interactive HUD Badge */}
      <div className="pointer-events-none absolute left-3 right-3 top-2 z-10 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 rounded-full border border-[#34D399]/40 bg-[#051829]/85 px-3.5 py-1 text-xs font-medium text-[#DBEAFE] shadow-sm backdrop-blur-md">
          <span
            className={`h-2 w-2 rounded-full ${
              measuring ? "animate-ping bg-[#34D399]" : "bg-[#34D399]"
            }`}
          />
          <span>
            {measuring
              ? "Escaneando parte selecionada..."
              : activePartMeta
              ? `Parte: ${activePartMeta.label}`
              : "Clique em qualquer parte do corpo 3D"}
          </span>
        </div>

        <button
          type="button"
          onClick={() => setAutoRotate((r) => !r)}
          className="pointer-events-auto flex items-center gap-1.5 rounded-full border border-[#38BDF8]/40 bg-[#051829]/85 px-3 py-1 text-[11px] font-medium text-[#A7F3D0] backdrop-blur-md transition hover:border-[#34D399]"
        >
          <RotateCw className="h-3 w-3" />
          {autoRotate ? "Giro Auto" : "Parado"}
        </button>
      </div>

      <WebGLErrorBoundary
        fallback={<SvgHoloFallback systems={systems} selectedSystem={selectedSystem} onSelectSystem={onSelectSystem} />}
      >
        <Canvas camera={{ position: [0, 0.2, 3.55], fov: 41 }} gl={{ alpha: true }}>
          <ambientLight intensity={0.7} color="#93C5FD" />
          <directionalLight position={[2.5, 4, 4]} intensity={1.05} color="#E0F2FE" />
          <directionalLight position={[-3, 1.5, -2.5]} intensity={0.85} color="#38BDF8" />
          <pointLight position={[0, -1.6, 2]} intensity={1.15} color="#10B981" />
          <HoloAstronautScene
            systems={systems}
            selectedSystem={selectedSystem}
            selectedRegion={selectedRegion}
            selectedPartId={selectedPartId}
            hoveredPartId={hoveredPartId}
            onHoverPart={setHoveredPartId}
            onSelectPart={(partId, meta) => {
              setAutoRotate(false);
              onSelectPart?.(partId, meta);
            }}
            onSelectSystem={onSelectSystem}
            autoRotate={autoRotate}
            measuring={measuring}
            palette="holo"
            showLabels={false}
          />
          <OrbitControls enablePan={false} minDistance={2.5} maxDistance={4.8} />
        </Canvas>
      </WebGLErrorBoundary>
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
  const [selectedPartId, setSelectedPartId] = useState(null);
  const [hoveredPartId, setHoveredPartId] = useState(null);
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
  const activePartMeta =
    (hoveredPartId && ANATOMICAL_PARTS_META[hoveredPartId]) ||
    (selectedPartId && ANATOMICAL_PARTS_META[selectedPartId]);

  return (
    <section className="eco-card rounded-3xl p-5 flex flex-col gap-3.5">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <span className="text-[11px] uppercase tracking-widest text-[#059669] font-bold flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5" /> Interactive 3D Anatomical Scanner
          </span>
          <h2 className="text-lg font-bold text-[#113D2E]">
            Inspect Body Parts &amp; Trigger Scan
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
              onClick={() => {
                setSelectedPartId(null);
                onSelectSystem(node.id);
              }}
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

      {/* Custom Procedural 3D Body Viewer */}
      <div className="relative h-[360px] w-full rounded-2xl overflow-hidden bg-gradient-to-b from-[#EAF6FA] via-[#F4FBF7] to-[#E6F5EC] border border-[#D5E8DD]">
        {activePartMeta && (
          <div className="pointer-events-none absolute left-3 top-3 z-10 rounded-full border border-[#CBE2D5] bg-white/95 px-3 py-1 text-xs font-bold text-[#113D2E] shadow-xs">
            Parte selecionada: {activePartMeta.label}
          </div>
        )}
        <WebGLErrorBoundary
          fallback={<SvgHoloFallback systems={systems} selectedSystem={selectedSystem} onSelectSystem={onSelectSystem} />}
        >
          <Canvas camera={{ position: [0, 0.35, 3.85], fov: 39 }}>
            <ambientLight intensity={0.95} />
            <directionalLight position={[2.5, 4.5, 4]} intensity={1.15} color="#FFFFFF" />
            <directionalLight position={[-3, 1.5, -2.5]} intensity={0.65} color="#38BDF8" />
            <pointLight position={[0, -1.6, 2.2]} intensity={0.75} color="#10B981" />
            <HoloAstronautScene
              systems={systems}
              selectedSystem={selectedSystem}
              selectedPartId={selectedPartId}
              hoveredPartId={hoveredPartId}
              onHoverPart={setHoveredPartId}
              onSelectPart={(partId) => {
                setSelectedPartId(partId);
                setAutoRotate(false);
              }}
              onSelectSystem={onSelectSystem}
              autoRotate={autoRotate}
              measuring={measuring}
              palette="eco"
              showLabels={true}
            />
            <OrbitControls enablePan={false} minDistance={2.4} maxDistance={5.4} />
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
            Clique em qualquer parte • Arraste para girar
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
