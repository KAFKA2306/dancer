@echo off

rem 必要な依存関係のインストール
pip install -r requirements.txt

rem MMDの環境変数の設定
set MMD_PATH=C:\path\to\MMD

rem Unityの環境変数の設定
set UNITY_PATH=C:\Program Files\Unity\Hub\Editor\2022.3.6f1\Editor\Unity.exe

rem YouTube APIの認証情報の設定
echo YouTube APIの認証情報を credentials.json ファイルに追加してください。

rem Slack APIの認証情報の設定
echo Slack APIの認証情報を config.yaml ファイルに追加してください。

echo セットアップが完了しました。
