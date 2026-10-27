@echo off
set PYTHONIOENCODING=utf-8
set STOCKFISH_PATH=C:\Users\44777\Downloads\stockfish-windows-x86-64-universal\stockfish\stockfish-windows-x86-64-universal.exe
cd /d C:\Users\44777\einstellung-chess
echo START %date% %time% > docs\outputs\run_full_depth24.log
python -u Stockfish_gate.py --depth 24 > docs\outputs\stockfish_gate_depth24_full.txt 2>&1
echo EXITCODE %errorlevel% >> docs\outputs\run_full_depth24.log
echo END %date% %time% >> docs\outputs\run_full_depth24.log