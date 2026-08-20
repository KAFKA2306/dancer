"""Render the real SiroinoSotai_PC armature with a cataloged BVH dance."""

from __future__ import annotations

import re
import shutil
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

from .motion_catalog import DanceMotion, download_motion

IMAGE2OUTFIT_COMMIT = "e6c3f707932fe3cdbddf07e77fa26279a0ff0252"
SIROINO_PATH = "Assets/SiroinoWorks/SiroinoSotai/FBX/SiroinoSotai_PC.fbx"
SIROINO_URL = (
    "https://raw.githubusercontent.com/KAFKA2306/image2outfit/"
    f"{IMAGE2OUTFIT_COMMIT}/{SIROINO_PATH}"
)
SIROINO_SIZE_BYTES = 3_862_972
SIROINO_BLOB_SHA = "13cc948a3db323ddce81e2b95e0b9ddc0b9480e2"
SIROINO_TERMS_URL = "https://booth.pm/ja/items/8268676"
SIROINO_LICENSE = "CC0-1.0"

REQUIRED_BONES = (
    "Hips",
    "Chest",
    "Neck",
    "Head",
    "UpperArm_L",
    "UpperArm_R",
    "LowerArm_L",
    "LowerArm_R",
    "UpperLeg_L",
    "UpperLeg_R",
    "LowerLeg_L",
    "LowerLeg_R",
)
SOURCE_TO_TARGET_BONES = {
    "Hips": "Hips",
    "Spine1": "Chest",
    "Neck1": "Neck",
    "Head": "Head",
    "LeftArm": "UpperArm_L",
    "RightArm": "UpperArm_R",
    "LeftForeArm": "LowerArm_L",
    "RightForeArm": "LowerArm_R",
    "LeftUpLeg": "UpperLeg_L",
    "RightUpLeg": "UpperLeg_R",
    "LeftLeg": "LowerLeg_L",
    "RightLeg": "LowerLeg_R",
}
CAMERA_PRESETS = ("front", "three_quarter_left", "three_quarter_right", "dolly")


@dataclass(frozen=True)
class RenderEvidence:
    width: int
    height: int
    camera_preset: str
    framing_margin: float
    camera_max_step_per_frame: float
    lighting: tuple[str, ...]
    background: str
    floor_present: bool


def _download_siroino(path: Path) -> None:
    urllib.request.urlretrieve(SIROINO_URL, path)
    if path.stat().st_size != SIROINO_SIZE_BYTES:
        raise ValueError(f"unexpected SiroinoSotai_PC.fbx size: {path.stat().st_size}")


def _clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def _import_siroino(path: Path) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    bpy.ops.preferences.addon_enable(module="io_scene_fbx")
    bpy.ops.import_scene.fbx(filepath=str(path), use_anim=False)
    candidates = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "ARMATURE"
        and all(name in obj.data.bones for name in REQUIRED_BONES)
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected one Siroino armature with required bones, found {len(candidates)}"
        )
    armature = candidates[0]
    skinned = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "MESH"
        and any(
            modifier.type == "ARMATURE" and modifier.object == armature
            for modifier in obj.modifiers
        )
    ]
    if not skinned:
        raise RuntimeError("Siroino armature has no skinned mesh")
    return armature, skinned


def _import_bvh(path: Path, target_armature: bpy.types.Object) -> bpy.types.Object:
    bpy.ops.preferences.addon_enable(module="io_anim_bvh")
    bpy.ops.import_anim.bvh(filepath=str(path), frame_start=1)
    source_bones = tuple(SOURCE_TO_TARGET_BONES)
    candidates = [
        obj
        for obj in bpy.context.scene.objects
        if obj.type == "ARMATURE"
        and obj != target_armature
        and all(name in obj.data.bones for name in source_bones)
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"expected one BVH armature with mapped bones, found {len(candidates)}"
        )
    return candidates[0]


def _parse_bvh_timing(path: Path) -> tuple[int, float]:
    text = path.read_text(encoding="ascii", errors="strict")
    motion = text.split("MOTION", maxsplit=1)
    if len(motion) != 2:
        raise ValueError("BVH has no MOTION section")
    frames_match = re.search(r"^Frames:\s*(\d+)\s*$", motion[1], re.MULTILINE)
    time_match = re.search(
        r"^Frame Time:\s*([0-9.eE+-]+)\s*$", motion[1], re.MULTILINE
    )
    if not frames_match or not time_match:
        raise ValueError("BVH timing metadata is missing")
    frame_count = int(frames_match.group(1))
    frame_time = float(time_match.group(1))
    if frame_count < 3 or frame_time <= 0:
        raise ValueError("BVH must contain a T-pose and at least two motion frames")
    return frame_count, frame_time


def _scene_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
    ]
    minimum = Vector(
        (
            min(point.x for point in corners),
            min(point.y for point in corners),
            min(point.z for point in corners),
        )
    )
    maximum = Vector(
        (
            max(point.x for point in corners),
            max(point.y for point in corners),
            max(point.z for point in corners),
        )
    )
    return minimum, maximum


def _look_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def _camera_direction(preset: str) -> Vector:
    if preset in {"front", "dolly"}:
        return Vector((0.0, -1.0, 0.08))
    if preset == "three_quarter_left":
        return Vector((-0.48, -1.0, 0.10)).normalized()
    if preset == "three_quarter_right":
        return Vector((0.48, -1.0, 0.10)).normalized()
    raise ValueError(f"unknown camera preset: {preset}")


def _configure_scene(
    meshes: list[bpy.types.Object],
    *,
    width: int,
    height: int,
    camera_preset: str,
) -> tuple[bpy.types.Object, Vector, Vector, float]:
    if camera_preset not in CAMERA_PRESETS:
        raise ValueError(f"unknown camera preset: {camera_preset}")
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.045, 0.052, 0.070)

    minimum, maximum = _scene_bounds(meshes)
    center = (minimum + maximum) * 0.5
    extent = maximum - minimum
    body_height = max(extent.z, 0.001)
    body_width = max(extent.x, extent.y, 0.001)
    aspect = width / height
    framing_scale = max(body_height, body_width / max(aspect, 0.25))
    distance = 3.05 * framing_scale

    camera_data = bpy.data.cameras.new("DanceCamera")
    camera = bpy.data.objects.new("DanceCamera", camera_data)
    scene.collection.objects.link(camera)
    direction = _camera_direction(camera_preset)
    camera.location = (
        center
        + direction * distance
        + Vector((0.0, 0.0, 0.10 * body_height))
    )
    camera.data.lens = 52
    _look_at(camera, center + Vector((0.0, 0.0, 0.04 * body_height)))
    scene.camera = camera
    base_camera_location = camera.location.copy()

    bpy.ops.mesh.primitive_plane_add(
        size=max(body_height * 5.0, 1.0),
        location=(center.x, center.y, minimum.z - 0.015 * body_height),
    )
    floor = bpy.context.active_object
    if floor is None:
        raise RuntimeError("failed to create floor")
    floor.name = "DanceFloor"
    floor_material = bpy.data.materials.new("DanceFloorMaterial")
    floor_material.diffuse_color = (0.07, 0.08, 0.11, 1.0)
    floor.data.materials.append(floor_material)

    lighting = (
        ("Key", (-1.25, -1.65, 2.1), 1300.0, 3.0),
        ("Fill", (1.35, -0.45, 1.25), 650.0, 2.5),
        ("Rim", (0.0, 1.45, 1.85), 1000.0, 2.0),
    )
    for name, offset, energy, radius in lighting:
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = radius
        light = bpy.data.objects.new(name, light_data)
        light.location = center + Vector(offset) * body_height
        _look_at(light, center)
        scene.collection.objects.link(light)
    return camera, center, base_camera_location, body_height


def _framing_margin(
    meshes: list[bpy.types.Object], camera: bpy.types.Object
) -> float:
    scene = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()
    margin = 1.0
    points_seen = 0
    for source in meshes:
        evaluated = source.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            step = max(1, len(mesh.vertices) // 600)
            for vertex_index in range(0, len(mesh.vertices), step):
                vertex = mesh.vertices[vertex_index]
                coordinate = world_to_camera_view(
                    scene, camera, evaluated.matrix_world @ vertex.co
                )
                if coordinate.z <= 0:
                    margin = min(margin, -1.0)
                else:
                    margin = min(
                        margin,
                        coordinate.x,
                        1.0 - coordinate.x,
                        coordinate.y,
                        1.0 - coordinate.y,
                    )
                points_seen += 1
        finally:
            evaluated.to_mesh_clear()
    if points_seen == 0:
        raise RuntimeError("unable to evaluate skinned mesh for framing")
    return float(margin)


def _bone_local_rest_rotation(bone: bpy.types.Bone) -> Matrix:
    rotation = bone.matrix_local.to_3x3()
    if bone.parent is None:
        return rotation
    return bone.parent.matrix_local.to_3x3().inverted() @ rotation


def _retarget_setup(
    source: bpy.types.Object, target: bpy.types.Object
) -> tuple[dict[str, object], dict[str, Matrix]]:
    scene = bpy.context.scene
    scene.frame_set(1)
    bpy.context.view_layer.update()
    source_baseline: dict[str, object] = {}
    basis_alignment: dict[str, Matrix] = {}
    for source_name, target_name in SOURCE_TO_TARGET_BONES.items():
        source_pose = source.pose.bones[source_name]
        target_pose = target.pose.bones[target_name]
        source_baseline[source_name] = source_pose.matrix_basis.to_quaternion().copy()
        source_rest = _bone_local_rest_rotation(source.data.bones[source_name])
        target_rest = _bone_local_rest_rotation(target.data.bones[target_name])
        basis_alignment[source_name] = target_rest.inverted() @ source_rest
        target_pose.rotation_mode = "QUATERNION"
        target_pose.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        target_pose.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    return source_baseline, basis_alignment


def _apply_motion_frame(
    source: bpy.types.Object,
    target: bpy.types.Object,
    source_frame: float,
    source_baseline: dict[str, object],
    basis_alignment: dict[str, Matrix],
) -> None:
    whole = int(source_frame)
    bpy.context.scene.frame_set(whole, subframe=source_frame - whole)
    bpy.context.view_layer.update()
    for source_name, target_name in SOURCE_TO_TARGET_BONES.items():
        current = source.pose.bones[source_name].matrix_basis.to_quaternion()
        delta = source_baseline[source_name].inverted() @ current
        basis = basis_alignment[source_name]
        target_delta = basis @ delta.to_matrix() @ basis.inverted()
        target.pose.bones[target_name].rotation_quaternion = target_delta.to_quaternion()
    bpy.context.view_layer.update()


def render_dance(
    output_dir: str | Path,
    *,
    motion_id: str,
    duration_seconds: float,
    fps: int,
    size: int | None = None,
    width: int | None = None,
    height: int | None = None,
    camera_preset: str = "front",
) -> tuple[str, DanceMotion, RenderEvidence]:
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    if fps <= 0:
        raise ValueError("fps must be positive")
    if size is not None:
        if width is not None or height is not None:
            raise ValueError("size cannot be combined with width/height")
        width = height = size
    if width is None or height is None:
        raise ValueError("width and height are required when size is omitted")
    if width <= 0 or height <= 0 or width % 2 or height % 2:
        raise ValueError("width and height must be positive even integers")
    if camera_preset not in CAMERA_PRESETS:
        raise ValueError(f"unknown camera preset: {camera_preset}")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    work = output / "siroino-render"
    if work.exists():
        raise FileExistsError(f"render work directory already exists: {work}")
    frame_dir = work / "frames"
    frame_dir.mkdir(parents=True)
    fbx_path = work / "SiroinoSotai_PC.fbx"
    bvh_path = work / "motion.bvh"

    _download_siroino(fbx_path)
    motion = download_motion(motion_id, bvh_path)
    source_frame_count, source_frame_time = _parse_bvh_timing(bvh_path)
    _clear_scene()
    target_armature, meshes = _import_siroino(fbx_path)
    target_armature.animation_data_clear()
    source_armature = _import_bvh(bvh_path, target_armature)
    source_baseline, basis_alignment = _retarget_setup(
        source_armature, target_armature
    )
    camera, camera_target, base_camera_location, body_height = _configure_scene(
        meshes,
        width=width,
        height=height,
        camera_preset=camera_preset,
    )

    frame_count = max(2, round(duration_seconds * fps))
    available_motion_seconds = (source_frame_count - 2) * source_frame_time
    if available_motion_seconds <= 0:
        raise ValueError("BVH contains no usable motion after its T-pose")

    scene = bpy.context.scene
    minimum_margin = 1.0
    maximum_camera_step = 0.0
    previous_camera_location = camera.location.copy()
    for frame_index in range(frame_count):
        time_seconds = frame_index / fps
        source_frame = 2.0 + (
            time_seconds % available_motion_seconds
        ) / source_frame_time
        source_frame = min(source_frame, float(source_frame_count))
        _apply_motion_frame(
            source_armature,
            target_armature,
            source_frame,
            source_baseline,
            basis_alignment,
        )
        if camera_preset == "dolly":
            progress = frame_index / max(frame_count - 1, 1)
            toward_target = (camera_target - base_camera_location).normalized()
            camera.location = base_camera_location + toward_target * (
                0.10 * body_height * progress
            )
            _look_at(camera, camera_target)
        camera_step = (camera.location - previous_camera_location).length
        maximum_camera_step = max(maximum_camera_step, float(camera_step))
        previous_camera_location = camera.location.copy()
        minimum_margin = min(minimum_margin, _framing_margin(meshes, camera))
        scene.render.filepath = str(frame_dir / f"{frame_index:04d}.png")
        bpy.ops.render.render(write_still=True)

    output_path = output / "dance.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-framerate",
            str(fps),
            "-i",
            str(frame_dir / "%04d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        check=True,
    )
    shutil.rmtree(work)
    evidence = RenderEvidence(
        width=width,
        height=height,
        camera_preset=camera_preset,
        framing_margin=minimum_margin,
        camera_max_step_per_frame=maximum_camera_step,
        lighting=("Key", "Fill", "Rim"),
        background="solid_world_plus_floor",
        floor_present=True,
    )
    return str(output_path), motion, evidence
