import os
import sys
import subprocess
import ast
import json
from pathlib import Path

REPORT_FILE = "harness_report.json"

def log_result(check_name, status, message):
    icon = "✔" if status else "❌"
    print(f"{icon} [Harness] {check_name}: {message}")
    return {"check": check_name, "success": status, "message": message}

def run_harness():
    reports = []
    all_passed = True

    print("🔍 [Harness] Запуск комплексной проверки проекта...\n")

    # 1. Linting & Code Health (Проверка синтаксиса ключевых скриптов)
    scripts_to_check = ["subtitles.py", "render_video_original.py"]
    for script in scripts_to_check:
        if os.path.exists(script):
            try:
                with open(script, "r", encoding="utf-8") as f:
                    source = f.read()
                ast.parse(source)
                reports.append(log_result(f"Linting ({script})", True, "Синаксис в норме."))
            except SyntaxError as e:
                all_passed = False
                reports.append(log_result(f"Linting ({script})", False, f"Ошибка синтаксиса: {e}"))
        else:
            reports.append(log_result(f"Linting ({script})", True, "Файл отсутствует в проекте (пропущено)."))

    # 2. Asset Validation (Проверка видео, шрифтов и субтитров)
    if os.path.exists("input_video.mp4"):
        reports.append(log_result("Asset Validation (Video)", True, "input_video.mp4 найден."))
    else:
        all_passed = False
        reports.append(log_result("Asset Validation (Video)", False, "input_video.mp4 не найден в папке проекта!"))

    # Ищем любые .ttf или .otf шрифты в папке
    fonts = list(Path(".").glob("*.ttf")) + list(Path(".").glob("*.otf"))
    if fonts:
        reports.append(log_result("Asset Validation (Fonts)", True, f"Найдено шрифтов: {len(fonts)}"))
    else:
        all_passed = False
        reports.append(log_result("Asset Validation (Fonts)", False, "Шрифты (.ttf/.otf) не найдены! Субтитры могут не примениться."))

    if os.path.exists("subtitles.ass"):
        reports.append(log_result("Asset Validation (Subtitles)", True, "Файл subtitles.ass присутствует."))
    else:
        all_passed = False
        reports.append(log_result("Asset Validation (Subtitles)", False, "Файл subtitles.ass отсутствует!"))

    # 3. Dry-Run Rendering (Тестовый прогон FFmpeg на 3 секунды)
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        reports.append(log_result("FFmpeg System Check", True, "FFmpeg доступен в системе."))

        if os.path.exists("input_video.mp4"):
            dry_run_cmd = [
                "ffmpeg", "-y", "-ss", "0", "-t", "3", "-i", "input_video.mp4",
                "-vf", "scale=720:1280", "-c:v", "libx264", "-preset", "ultrafast", "dry_run_test.mp4"
            ]
            res = subprocess.run(dry_run_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if res.returncode == 0:
                reports.append(log_result("Dry-Run Render", True, "Тестовый рендер первых 3 секунд прошел успешно."))
                if os.path.exists("dry_run_test.mp4"):
                    os.remove("dry_run_test.mp4")
            else:
                all_passed = False
                err_msg = res.stderr.decode("utf-8", errors="ignore").splitlines()[-1] if res.stderr else "Unknown error"
                reports.append(log_result("Dry-Run Render", False, f"Ошибка рендеринга FFmpeg: {err_msg}"))
    except Exception as e:
        all_passed = False
        reports.append(log_result("FFmpeg System Check", False, f"FFmpeg не найден или ошибка запуска: {e}"))

    # 4. Log Reporting (Сохранение структурированного отчёта для агента)
    report_data = {
        "status": "SUCCESS" if all_passed else "FAILED",
        "summary": "Все проверки пройдены" if all_passed else "Найдены проблемы, требующие исправления",
        "details": reports
    }
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"\n📄 [Harness] Отчёт сохранён в '{REPORT_FILE}' для ИИ-агента.")
    
    if all_passed:
        print("✅ [Harness] Среда абсолютно здорова и готова к работе!\n")
        return True
    else:
        print("⚠️ [Harness] Обнаружены проблемы. Агент сможет прочитать 'harness_report.json' и устранить их.\n")
        return False

if __name__ == "__main__":
    success = run_harness()
    if not success:
        sys.exit(1)
