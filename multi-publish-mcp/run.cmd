@echo off
rem multi-publish-mcp 启动器: install / test
setlocal
set "DIR=%~dp0scripts"
where node >nul 2>nul && (set "NODE_EXE=node") || (set "NODE_EXE=C:\Users\qilin\.workbuddy\binaries\node\versions\22.22.2-6\node.exe")

if /i "%1"=="install" (
  pushd "%DIR%"
  call npm install
  popd
  echo [install] done.
  exit /b 0
)
if /i "%1"=="test" (
  echo {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke","version":"0.0.1"}}} | "%NODE_EXE%" "%DIR%\server.mjs"
  exit /b 0
)
echo 用法: run.cmd install^|test
"%NODE_EXE%" "%DIR%\server.mjs"
