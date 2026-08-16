"""Render the real SiroinoSotai_PC armature dancing with Blender."""

from __future__ import annotations

import math
import shutil
import subprocess
import urllib.request
from pathlib import Path

import bpy
from mathutils import Vector

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


def _scene_bounds(objects: list[bpy.types.Object]) -> tuple[Vector, Vector]:
    corners = [
        obj.matrix_world @ Vector(corner)
        for obj in objects
        for corner in obj.bound_box
    ]
    minimum = Vector(
        (min(point.x for point in corners), min(point.y for point in corners), min(point.z for point in corners))
    )
    maximum = Vector(
        (max(point.x for point in corners), max(point.y for point in corners), max(point.z for point in corners))
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


def _animate_pose(armature: bpy.types.Object, time_seconds: float) -> None:
    pose = armature.pose.bones
    phase = 2.0 * math.pi * time_seconds

    for name in REQUIRED_BONES:
        pose[name].rotation_mode = "XYZ"
        pose[name].rotation_euler = (0.0, 0.0, 0.0)
    pose["Hips"].location = (0.0, 0.0, 0.0)

    pose["Hips"].location.x = 0.035 * math.sin(phase)
    pose["Hips"].location.z = 0.025 * math.sin(2.0 * phase)
    pose["Hips"].rotation_euler.z = 0.12 * math.sin(phase)
    pose["Chest"].rotation_euler.y = -0.10 * math.sin(phase)
    pose["Chest"].rotation_euler.z = -0.16 * math.sin(phase)
    pose["Neck"].rotation_euler.z = 0.08 * math.sin(phase)
    pose["Head"].rotation_euler.z = 0.10 * math.sin(phase)

    arm_swing = 0.65 * math.sin(phase)
    pose["UpperArm_L"].rotation_euler.z = 0.45 + arm_swing
    pose["UpperArm_R"].rotation_euler.z = -0.45 - arm_swing
    pose["LowerArm_L"].rotation_euler.x = -0.35 - 0.25 * math.cos(phase)
    pose["LowerArm_R"].rotation_euler.x = -0.35 + 0.25 * math.cos(phase)

    leg_swing = 0.32 * math.sin(phase)
    pose["UpperLeg_L"].rotation_euler.x = leg_swing
    pose["UpperLeg_R"].rotation_euler.x = -leg_swing
    pose["LowerLeg_L"].rotation_euler.x = -0.18 - 0.15 * max(0.0, math.sin(phase))
    pose["LowerLeg_R"].rotation_euler.x = -0.18 - 0.15 * max(0.0, -math.sin(phase))
    bpy.context.view_layer.update()


def render_dance(
    output_dir: str | Path,
    *,
    duration_seconds: float,
    fps: int,
    size: int,
) -> str:
    """Render SiroinoSotai_PC moving under its real armature to H.264 MP4."""
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

    _download_siroino(fbx_path)
    _clear_scene()
    armature, meshes = _import_siroino(fbx_path)
    armature.animation_data_clear()
    _configure_scene(meshes, size)

    frame_count = max(2, round(duration_seconds * fps))
    scene = bpy.context.scene
    for frame_index in range(frame_count):
        _animate_pose(armature, frame_index / fps)
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
    return str(output_path)
