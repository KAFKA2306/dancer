# video_generation.py
import os
import sys
import subprocess
import tempfile
from pymeshio import pmx
from pymeshio.pmx import writer

def generate_video_mmd(avatar, motion, music, background):
    # PMXファイルの読み込み
    model = pmx.Model()
    model.load(avatar)

    # モーションデータの読み込み
    motion_data = pmx.load_motion(motion)

    # モーションデータをモデルに適用
    model.motions = [motion_data]

    # 一時ディレクトリの作成
    with tempfile.TemporaryDirectory() as temp_dir:
        # 一時ファイルのパス
        temp_model_path = os.path.join(temp_dir, 'temp_model.pmx')
        temp_motion_path = os.path.join(temp_dir, 'temp_motion.vmd')
        output_path = os.path.join(temp_dir, 'output.mp4')

        # モデルの保存
        writer.write_to_file(model, temp_model_path)

        # モーションデータの保存
        pmx.save_motion(motion_data, temp_motion_path)

        # MMDの実行コマンド
        mmd_command = [
            'MMD.exe',
            '-model', temp_model_path,
            '-vmd', temp_motion_path,
            '-background', background,
            '-music', music,
            '-output', output_path
        ]

        # MMDの実行
        subprocess.run(mmd_command, check=True)

        # 生成された動画ファイルを読み込んで返す
        with open(output_path, 'rb') as file:
            video_data = file.read()

    return video_data

def generate_video_unity(avatar, motion, music, background):
    # Unityプロジェクトのパス
    project_path = '/path/to/unity/project'

    # Unityの実行コマンド
    unity_command = [
        'Unity.exe',
        '-batchmode',
        '-nographics',
        '-silent-crashes',
        '-projectPath', project_path,
        '-executeMethod', 'VideoGenerator.Generate',
        '-avatar', avatar,
        '-motion', motion,
        '-music', music,
        '-background', background,
        '-quit'
    ]

    # Unityの実行
    subprocess.run(unity_command, check=True)

    # 生成された動画ファイルのパス
    output_path = os.path.join(project_path, 'Output', 'output.mp4')

    # 生成された動画ファイルを読み込んで返す
    with open(output_path, 'rb') as file:
        video_data = file.read()

    return video_data

def generate_video(avatar, motion, music, background):
    # MMDを使用して動画を生成
    try:
        video_data = generate_video_mmd(avatar, motion, music, background)
        return video_data
    except Exception as e:
        print(f"Error generating video with MMD: {str(e)}")

    # MMDでの動画生成に失敗した場合、Unityを使用して動画を生成
    try:
        video_data = generate_video_unity(avatar, motion, music, background)
        return video_data
    except Exception as e:
        print(f"Error generating video with Unity: {str(e)}")
        raise Exception("動画の生成に失敗しました")
