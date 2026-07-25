"""Load a part file, build it, turn it into something a browser can show."""

import importlib.util
import pathlib
import sys
import time

import numpy as np
import trimesh


class BuildError(Exception):
    pass


def load(path):
    """Import a part file fresh and return its @part function."""
    path = pathlib.Path(path)
    modname = f"_nurb_part_{path.stem}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(modname, path)
    if spec is None or spec.loader is None:
        raise BuildError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    written = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # keep __pycache__ out of the user's parts/
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = written
        sys.modules.pop(modname, None)

    for value in vars(mod).values():
        if callable(value) and hasattr(value, "_nurb"):
            return value
    raise BuildError(f"no @part function in {path.name}")


def build(path, overrides=None, draft=False):
    """Build a part. Returns (shape, params, milliseconds)."""
    fn = load(path)
    defn = fn._nurb
    kwargs = dict(defn.params)
    if overrides:
        unknown = set(overrides) - set(kwargs)
        if unknown:
            raise BuildError(f"unknown parameter(s): {', '.join(sorted(unknown))}")
        kwargs.update(overrides)
    call = dict(kwargs)
    if defn.accepts_draft:
        call["draft"] = draft

    started = time.perf_counter()
    shape = fn(**call)
    elapsed = (time.perf_counter() - started) * 1000
    if shape is None:
        raise BuildError(f"{defn.name}() returned None")
    return shape, kwargs, elapsed


def to_mesh(shape, tolerance=0.1):
    """Tessellate to a triangle mesh.

    process=False matters: OCCT already splits vertices at face boundaries, which
    is exactly the layout we want (crisp edges, smooth curves). Letting trimesh
    weld them merges the box corners and smears the normals across perpendicular
    faces, which renders as a shadeless blob.
    """
    verts, tris = shape.tessellate(tolerance)
    mesh = trimesh.Trimesh(
        vertices=np.array([(v.X, v.Y, v.Z) for v in verts], dtype=np.float64),
        faces=np.array(tris, dtype=np.int64),
        process=False,
    )
    mesh.vertex_normals  # populate before export, or the GLB ships without normals
    return mesh


def to_glb(shape, tolerance=0.1):
    return trimesh.Scene([to_mesh(shape, tolerance)]).export(file_type="glb")


def stats(shape):
    bb = shape.bounding_box()
    return {
        "bbox": [round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)],
        "volume": round(shape.volume, 1),
    }


def find_parts(root):
    """Every part file in a project."""
    parts_dir = pathlib.Path(root) / "parts"
    if not parts_dir.is_dir():
        return []
    return sorted(p for p in parts_dir.glob("*.py") if not p.name.startswith("_"))
