@echo off
chcp 65001 > nul
echo 🚀 ЗАПУСК УПРОЩЁННОЙ СИСТЕМЫ RENODE
echo.

cd /d C:\Users\Student\Desktop\renode_real_system

echo 📁 Запуск TCP сервера...
start "Renode TCP Server" cmd /k "python host_receiver/renode_tcp_receiver.py"

timeout /t 3 > nul

echo.
echo 🔌 Запуск эмулятора прошивки...
start "STM32 Firmware" cmd /k "python firmware/sensor_firmware_emulator.py"

timeout /t 3 > nul

echo.
echo 🖥️ Запуск Renode...
renode renode_scripts/simple_stm32.resc

echo.
echo ✅ Система запущена!