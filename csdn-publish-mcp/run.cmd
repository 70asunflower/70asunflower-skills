@echo off
rem csdn-publish-mcp 启动器: install / test / doctor / run
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
if /i "%1"=="" (
  echo 用法: run.cmd install^|test
  echo   install  npm 安装依赖(playwright-core)
  echo   test     MCP 握手冒烟测试
  exit /b 0
)
rem 其他参数: 作为 MCP server 常驻（客户端直接调用，一般不手动跑）
"%NODE_EXE%" "%DIR%\server.mjs"
