"""Render an articulated 3D character dancing with VTK and encode it with FFmpeg."""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

import vtk


def _segment(renderer: vtk.vtkRenderer, radius: float, color: tuple[float, float, float]):
    line = vtk.vtkLineSource()
    tube = vtk.vtkTubeFilter()
    tube.SetInputConnection(line.GetOutputPort())
    tube.SetRadius(radius)
    tube.SetNumberOfSides(16)
    tube.CappingOn()
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(tube.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    renderer.AddActor(actor)
    return line


def _sphere(renderer: vtk.vtkRenderer, radius: float, color: tuple[float, float, float]):
    source = vtk.vtkSphereSource()
    source.SetRadius(radius)
    source.SetThetaResolution(24)
    source.SetPhiResolution(24)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(source.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    renderer.AddActor(actor)
    return actor


def _pose(time_seconds: float):
    phase = 2.0 * math.pi * time_seconds
    bounce = 0.10 * math.sin(2.0 * phase)
    sway = 0.18 * math.sin(phase)
    hip = (sway, 0.0, 1.05 + bounce)
    chest = (-0.5 * sway, 0.0, 1.85 + bounce)
    neck = (-0.6 * sway, 0.0, 2.15 + bounce)
    head = (neck[0], 0.0, 2.52 + bounce)

    elbow_left = (chest[0] - 0.55, 0.10, 1.95 + bounce + 0.35 * math.sin(phase))
    hand_left = (chest[0] - 0.92, 0.16, 2.10 + bounce + 0.55 * math.sin(phase))
    elbow_right = (chest[0] + 0.55, -0.10, 1.95 + bounce - 0.35 * math.sin(phase))
    hand_right = (chest[0] + 0.92, -0.16, 2.10 + bounce - 0.55 * math.sin(phase))

    left_lift = max(0.0, math.sin(phase))
    right_lift = max(0.0, -math.sin(phase))
    knee_left = (hip[0] - 0.28, 0.05, 0.62 + 0.18 * left_lift)
    foot_left = (hip[0] - 0.40, 0.15, 0.10 + 0.10 * left_lift)
    knee_right = (hip[0] + 0.28, -0.05, 0.62 + 0.18 * right_lift)
    foot_right = (hip[0] + 0.40, -0.15, 0.10 + 0.10 * right_lift)

    return {
        "segments": [
            (hip, chest),
            (chest, neck),
            (chest, elbow_left),
            (elbow_left, hand_left),
            (chest, elbow_right),
            (elbow_right, hand_right),
            (hip, knee_left),
            (knee_left, foot_left),
            (hip, knee_right),
            (knee_right, foot_right),
        ],
        "head": head,
        "hand_left": hand_left,
        "hand_right": hand_right,
    }


def render_dance(
    output_dir: str | Path,
    *,
    duration_seconds: float,
    fps: int,
    size: int,
) -> str:
    """Render a moving 3D character to an H.264 MP4 and return its path."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    if fps <= 0:
        raise ValueError("fps must be positive")
    if size <= 0 or size % 2:
        raise ValueError("size must be a positive even integer")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    frame_dir = output / "frames"
    if frame_dir.exists():
        raise FileExistsError(f"frame directory already exists: {frame_dir}")
    frame_dir.mkdir()

    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0.96, 0.96, 0.96)
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.AddRenderer(renderer)
    window.SetSize(size, size)

    floor = vtk.vtkPlaneSource()
    floor.SetOrigin(-3.0, -3.0, 0.0)
    floor.SetPoint1(3.0, -3.0, 0.0)
    floor.SetPoint2(-3.0, 3.0, 0.0)
    floor_mapper = vtk.vtkPolyDataMapper()
    floor_mapper.SetInputConnection(floor.GetOutputPort())
    floor_actor = vtk.vtkActor()
    floor_actor.SetMapper(floor_mapper)
    floor_actor.GetProperty().SetColor(0.82, 0.85, 0.88)
    renderer.AddActor(floor_actor)

    body_color = (0.15, 0.35, 0.75)
    skin_color = (0.95, 0.70, 0.55)
    segments = [
        _segment(renderer, 0.16 if index == 0 else 0.10, body_color)
        for index in range(10)
    ]
    head = _sphere(renderer, 0.30, skin_color)
    hand_left = _sphere(renderer, 0.12, skin_color)
    hand_right = _sphere(renderer, 0.12, skin_color)

    camera = renderer.GetActiveCamera()
    camera.SetPosition(4.5, -7.0, 3.2)
    camera.SetFocalPoint(0.0, 0.0, 1.3)
    camera.SetViewUp(0.0, 0.0, 1.0)
    renderer.ResetCameraClippingRange()

    frame_count = max(2, round(duration_seconds * fps))
    for frame_index in range(frame_count):
        pose = _pose(frame_index / fps)
        for source, (start, end) in zip(segments, pose["segments"], strict=True):
            source.SetPoint1(*start)
            source.SetPoint2(*end)
            source.Modified()
        head.SetPosition(*pose["head"])
        hand_left.SetPosition(*pose["hand_left"])
        hand_right.SetPosition(*pose["hand_right"])

        window.Render()
        capture = vtk.vtkWindowToImageFilter()
        capture.SetInput(window)
        capture.Update()
        writer = vtk.vtkPNGWriter()
        writer.SetFileName(str(frame_dir / f"{frame_index:04d}.png"))
        writer.SetInputConnection(capture.GetOutputPort())
        writer.Write()

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
    shutil.rmtree(frame_dir)
    return str(output_path)
