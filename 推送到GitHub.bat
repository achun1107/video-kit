@echo off
chcp 65001 >nul
cd /d "D:\video-kit-repo"

echo.
echo ============================================
echo   video-kit - 推送到 GitHub
echo ============================================
echo.
echo 如果没有保存过 token，会打印一个设备码，
echo 打开 https://github.com/login/device 输进去授权即可。
echo.
pause

python tools\gh-device-login.py --push --repo video-kit --dir "D:\video-kit-repo"

echo.
echo ============================================
pause
