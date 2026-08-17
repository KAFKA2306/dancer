"""Render the real SiroinoSotai_PC armature with a cataloged BVH dance."""

from __future__ import annotations

import re
import shutil
import subprocess
import urllib.request
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from .motion_catalog import DanceMotion, download_motion

IMAGE2OUTFIT_COMMIT = "e6c3f707932fe3cdbddf07e77fa26279a0ff0252"
SIROINO_PATH = "Assets/SiroinoWorks/SiroinoSotai/FBX/SiroinoSotai_PC.fbx"
SIROINO_URL = (
    "https://raw.githubusercontent.com/KAFKA2306/image2outfit/"
    f"{IMAGE2OUTFIT_COMMIT}/{SIROINO_PATH}"
)
SIROINO_SIZE_BYTES = 3_862_972
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


def _download_siroino(path: Path) -> None:
    urllib.request.urlretrieve(SIROINO_URL, path)
    if path.stat().st_size != SIROINO_SIZE_BYTES:
        raise ValueError(
            f"unexpected SiroinoSotai_PC.fbx size: {path.stat().st_size}"
        )


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


def _configure_scene(meshes: list[bpy.types.Object], size: int) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.world.color = (0.055, 0.065, 0.085)

    minimum, maximum = _scene_bounds(meshes)
    center = (minimum + maximum) * 0.5
    extent = maximum - minimum
    height = max(extent.z, 0.001)

    camera_data = bpy.data.cameras.new("DanceCamera")
    camera = bpy.data.objects.new("DanceCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = center + Vector((0.0, -2.6 * height, 0.18 * height))
    camera.data.lens = 55
    _look_at(camera, center + Vector((0.0, 0.0, 0.05 * height)))
    scene.camera = camera

    for name, offset, energy, radius in (
        ("Key", (-1.2, -1.5, 2.0), 1200.0, 3.0),
        ("Fill", (1.4, -0.4, 1.2), 700.0, 2.5),
        ("Rim", (0.0, 1.4, 1.8), 900.0, 2.0),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = radius
        light = bpy.data.objects.new(name, light_data)
        light.location = center + Vector(offset) * height
        _look_at(light, center)
        scene.collection.objects.link(light)


def _bone_local_rest_rotation(bone: bpy.types.Bone) -> Matrix:
    rotation = bone.matrix_local.to_3x3()
    if bone.parent is None:
        return rotation
    return bone.parent.matrix_local.to_3x3().inverted() @ rotation


def _retarget_setup(
    source: bpy.types.Object,
    target: bpy.types.Object,
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
    size: int,
) -> tuple[str, DanceMotion]:
    """Retarget one cataloged BVH motion to SiroinoSotai_PC and render H.264."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    if fps <= 0:
        raise ValueError("fps must be positive")
    if size <= 0 or size % 2:
        raise ValueError("size must be a positive even integer")

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
    source_baseline, basis_alignment = _retarget_setup(source_armature, target_armature)
    _configure_scene(meshes, size)

    frame_count = max(2, round(duration_seconds * fps))
    available_motion_seconds = (source_frame_count - 2) * source_frame_time
    if available_motion_seconds <= 0:
        raise ValueError("BVH contains no usable motion after its T-pose")

    scene = bpy.context.scene
    for frame_index in range(frame_count):
        time_seconds = frame_index / fps
        source_frame = 2.0 + (time_seconds % available_motion_seconds) / source_frame_time
        source_frame = min(source_frame, float(source_frame_count))
        _apply_motion_frame(
            source_armature,
            target_armature,
            source_frame,
            source_baseline,
            basis_alignment,
        )
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
    return str(output_path), motion
