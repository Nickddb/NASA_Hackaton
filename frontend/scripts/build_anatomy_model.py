"""
Build frontend/public/models/anatomy.glb from the MakeHuman base mesh (CC0).

Inputs (download once from github.com/makehumancommunity/makehuman, assets under CC0 1.0):
  makehuman/data/3dobjs/base.obj           realistic neutral human mesh, A-pose
  makehuman/data/rigs/default_weights.mhw  bone weights of the default skeleton (CC0)
  makehuman/data/targets/macrodetails/*.target  optional morph targets (CC0), e.g. male body shape

Each vertex goes to the bone with the highest weight; bones map to the 25 body regions used by the app
(backend/app/engine/body_regions.py). The torso is split front/back and upper/lower, elbows and knees are cut
around the joint markers of the mesh. Normals are computed on the whole body before splitting, so the parts meet
without visible seams. Output: one glTF node per region (node name = region id), metres, feet at y = 0.

    python frontend/scripts/build_anatomy_model.py <base.obj> <default_weights.mhw> <out.glb> [target:weight ...]

Used for the app (young male, mean of the three MakeHuman ethnicities, moderate muscle):
    ... african-male-young.target:0.3333 asian-male-young.target:0.3333 caucasian-male-young.target:0.3333 \
        universal-male-young-maxmuscle-averageweight.target:0.4
"""

from __future__ import annotations

import json
import re
import struct
import sys
from collections import defaultdict

import numpy as np

HEIGHT_M = 1.80
KEEP_GROUPS = {"body", "helper-l-eye", "helper-r-eye"}
JOINTS = {
    "joint-l-elbow", "joint-r-elbow", "joint-l-knee", "joint-r-knee",
    "joint-l-shoulder", "joint-r-shoulder", "joint-l-upper-leg", "joint-r-upper-leg",
}


def bone_region(bone: str) -> str | None:
    side = "left" if bone.endswith(".L") else "right" if bone.endswith(".R") else None
    b = bone.rsplit(".", 1)[0] if side else bone
    if b in ("head", "jaw", "eye", "special04", "special05") or re.match(
        r"(levator|oculi|orbicularis|oris|risorius|tongue)", b
    ):
        return "head"
    if b.startswith("neck"):
        return "neck"
    if b in ("root", "pelvis"):
        return "pelvis"
    if b.startswith("spine") or b == "breast":
        return "torso"
    if b in ("clavicle", "shoulder01"):
        return f"{side}_shoulder"
    if b.startswith("upperarm"):
        return f"{side}_upper_arm"
    if b.startswith("lowerarm"):
        return f"{side}_forearm"
    if b in ("wrist",) or b.startswith(("metacarpal", "finger")):
        return f"{side}_hand"
    if b.startswith("upperleg"):
        return f"{side}_thigh"
    if b.startswith("lowerleg"):
        return f"{side}_calf"
    if b == "foot" or b.startswith("toe"):
        return f"{side}_foot"
    return None


def read_obj(path: str):
    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, list[int]]] = []  # (group_tag, vertex ids)
    joint_vertices: dict[str, set[int]] = defaultdict(set)
    group = ""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                verts.append((float(x), float(y), float(z)))
            elif line.startswith("g "):
                group = line[2:].strip()
            elif line.startswith("f "):
                ids = [int(tok.split("/")[0]) - 1 for tok in line.split()[1:]]
                if group in KEEP_GROUPS:
                    faces.append((0 if group == "body" else 1, ids))
                elif group in JOINTS:
                    joint_vertices[group].update(ids)
    return np.array(verts, dtype=np.float64), faces, joint_vertices


def apply_targets(V: np.ndarray, targets: list[tuple[str, float]]) -> np.ndarray:
    """MakeHuman .target files: 'vertex dx dy dz' offsets, blended by weight (morph targets)."""
    V = V.copy()
    for path, weight in targets:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip() or line.startswith("#"):
                    continue
                vid, dx, dy, dz = line.split()
                V[int(vid)] += weight * np.array([float(dx), float(dy), float(dz)])
    return V


def main(obj_path: str, weights_path: str, out_path: str, targets: list[tuple[str, float]] = ()) -> None:
    V, faces, joint_vertices = read_obj(obj_path)
    V = apply_targets(V, list(targets))
    weights = json.load(open(weights_path, encoding="utf-8"))["weights"]

    best_w = np.zeros(len(V))
    region = np.array([None] * len(V), dtype=object)
    for bone, pairs in weights.items():
        reg = bone_region(bone)
        if reg is None:
            continue
        for vid, w in pairs:
            if w > best_w[vid]:
                best_w[vid] = w
                region[vid] = reg

    # triangles of the kept groups; eyes always belong to the head
    tris: list[tuple[int, int, int]] = []
    eye_vertices: set[int] = set()
    for tag, ids in faces:
        for k in range(1, len(ids) - 1):
            tris.append((ids[0], ids[k], ids[k + 1]))
        if tag == 1:
            eye_vertices.update(ids)
    T = np.array(tris, dtype=np.int64)
    used = np.unique(T)
    for vid in eye_vertices:
        region[vid] = "head"

    # metres, feet on the floor
    ys = V[used, 1]
    scale = HEIGHT_M / (ys.max() - ys.min())
    V = (V - np.array([V[used, 0].mean(), ys.min(), V[used, 2].mean()])) * scale

    # torso: upper/lower at the bottom of the ribcage, front/back at the local mid-depth
    torso = np.array([i for i in used if region[i] == "torso"])
    split_y = np.percentile(V[torso, 1], 42)
    mid_z = np.median(V[torso, 2])
    for i in torso:
        upper = V[i, 1] >= split_y
        front = V[i, 2] >= mid_z
        region[i] = ("chest" if front else "upper_back") if upper else ("abdomen" if front else "lower_back")

    # elbows and knees: a sphere around the joint marker
    for joint, radius in (("joint-l-elbow", 0.05), ("joint-r-elbow", 0.05), ("joint-l-knee", 0.07), ("joint-r-knee", 0.07)):
        centre = V[list(joint_vertices[joint])].mean(axis=0)
        side = "left" if "-l-" in joint else "right"
        part = "elbow" if "elbow" in joint else "knee"
        limbs = {f"{side}_upper_arm", f"{side}_forearm"} if part == "elbow" else {f"{side}_thigh", f"{side}_calf"}
        near = np.linalg.norm(V[used] - centre, axis=1) < radius
        for i in used[near]:
            if region[i] in limbs:
                region[i] = f"{side}_{part}"

    # shoulders: the deltoid cap around the shoulder joint (bone weights give clavicle/shoulder very little)
    for side in ("l", "r"):
        name = "left" if side == "l" else "right"
        centre = V[list(joint_vertices[f"joint-{side}-shoulder"])].mean(axis=0)
        near = np.linalg.norm(V[used] - centre, axis=1) < 0.085
        for i in used[near]:
            if region[i] in (f"{name}_upper_arm", f"{name}_shoulder", "chest", "upper_back"):
                region[i] = f"{name}_shoulder"

    # hips & pelvis: everything of the trunk and upper thighs below the hip joints (incl. glutes)
    hip_y = np.mean([V[list(joint_vertices[f"joint-{s}-upper-leg"])].mean(axis=0)[1] for s in ("l", "r")])
    for i in used:
        r = region[i]
        if r in ("abdomen", "lower_back", "pelvis") and V[i, 1] < hip_y + 0.07:
            region[i] = "pelvis"
        elif r in ("left_thigh", "right_thigh") and V[i, 1] > hip_y - 0.02:
            region[i] = "pelvis"

    unassigned = [i for i in used if region[i] is None]
    if unassigned:
        print(f"warning: {len(unassigned)} vertices without a bone; assigning to the nearest assigned vertex")
        assigned = np.array([i for i in used if region[i] is not None])
        for i in unassigned:
            j = assigned[np.argmin(np.linalg.norm(V[assigned] - V[i], axis=1))]
            region[i] = region[j]

    # smooth normals on the whole body (area weighted) -> no seams where parts meet
    N = np.zeros_like(V)
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    for k in range(3):
        np.add.at(N, T[:, k], fn)
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)

    # a triangle belongs to the region most of its corners belong to
    by_region: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    for t in T:
        regs = [region[i] for i in t]
        by_region[max(set(regs), key=regs.count)].append(tuple(t))

    write_glb(out_path, V.astype(np.float32), N.astype(np.float32), by_region)
    for name in sorted(by_region):
        print(f"{name:16} {len(by_region[name]):6d} triangles")


def write_glb(path: str, V: np.ndarray, N: np.ndarray, by_region: dict[str, list[tuple[int, int, int]]]) -> None:
    blob = bytearray()
    views, accessors, meshes, nodes = [], [], [], []

    def add_view(data: bytes, target: int) -> int:
        while len(blob) % 4:
            blob.append(0)
        views.append({"buffer": 0, "byteOffset": len(blob), "byteLength": len(data), "target": target})
        blob.extend(data)
        return len(views) - 1

    for name in sorted(by_region):
        tris = np.array(by_region[name], dtype=np.int64)
        local_ids, inverse = np.unique(tris.ravel(), return_inverse=True)
        pos, nor = V[local_ids], N[local_ids]
        idx = inverse.astype(np.uint32)
        a_pos = len(accessors)
        accessors.append({
            "bufferView": add_view(pos.tobytes(), 34962), "componentType": 5126, "count": len(pos), "type": "VEC3",
            "min": pos.min(axis=0).tolist(), "max": pos.max(axis=0).tolist(),
        })
        accessors.append({"bufferView": add_view(nor.tobytes(), 34962), "componentType": 5126, "count": len(nor), "type": "VEC3"})
        accessors.append({"bufferView": add_view(idx.tobytes(), 34963), "componentType": 5125, "count": len(idx), "type": "SCALAR"})
        meshes.append({"name": name, "primitives": [{"attributes": {"POSITION": a_pos, "NORMAL": a_pos + 1}, "indices": a_pos + 2}]})
        nodes.append({"name": name, "mesh": len(meshes) - 1})

    gltf = {
        "asset": {"version": "2.0", "generator": "AstraCare build_anatomy_model.py", "copyright": "MakeHuman base mesh, CC0 1.0"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "accessors": accessors,
        "bufferViews": views,
        "buffers": [{"byteLength": len(blob)}],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    blob += b"\0" * (-len(blob) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(blob), 0x004E4942) + bytes(blob))


if __name__ == "__main__":
    # extra args: target.target:weight (e.g. caucasian-male-young.target:0.333)
    extra = [(a.rsplit(":", 1)[0], float(a.rsplit(":", 1)[1])) for a in sys.argv[4:]]
    main(*sys.argv[1:4], targets=extra)
