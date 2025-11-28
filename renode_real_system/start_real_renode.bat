@echo off
chcp 65001 > nul
echo 🚀 ЗАПУСК РЕАЛЬНОЙ СИСТЕМЫ RENODE
echo.

cd /d %~dp0

echo 📁 Запуск TCP сервера...
start "Renode TCP Server" cmd /k "python host_receiver/renode_tcp_receiver.py"

timeout /t 3 > nul

echo.
echo 🔌 Запуск эмулятора прошивки...
start "STM32 Firmware" cmd /k "python firmware/sensor_firmware_emulator.py"

timeout /t 3 > nul

echo.
echo 💡 Команда для запуска Renode:
echo    renode renode_scripts/stm32_sensor_node.resc
echo.
echo ✅ Система готова к работе!