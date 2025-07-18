import datetime
import logging
import os
import subprocess

from tqdm import tqdm

logger = logging.getLogger(__name__)
SUPPORTED_FORMATS = (
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".flv",
    ".wmv",
    ".webm",
    ".3gp",
    ".vob",
)


def find_video_files(directory):
    """Находит видеофайлы в директории и поддиректориях"""
    video_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(SUPPORTED_FORMATS):
                video_files.append(os.path.join(root, file))
    return video_files


def get_video_creation_date(input_path):
    """Получает дату создания видео с учетом временной зоны."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format_tags=creation_time",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            input_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        date_str = result.stdout.strip()
        if date_str:
            # Парсим дату как UTC
            utc_date = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            # Преобразуем UTC в локальное время
            local_date = utc_date.replace(tzinfo=datetime.timezone.utc).astimezone()
            # Удаляем информацию о временной зоне для совместимости с os.utime
            return local_date.replace(tzinfo=None)
    except Exception as e:
        logger.warning(f"Не удалось извлечь дату создания для {input_path}: {str(e)}")
    # Фолбэк: дата изменения файла
    return datetime.datetime.fromtimestamp(os.path.getmtime(input_path))


def convert_video(input_path, output_path, crf, preset, delete_original, skip_existing):
    """Конвертирует видео в H265 с сохранением метаданных"""
    try:
        # Пропуск существующих файлов
        if skip_existing and os.path.exists(output_path):
            return "skipped"

        # Сохраняем исходную дату создания
        original_date = get_video_creation_date(input_path)

        # Проверяем, не является ли видео уже в H265
        cmd_check = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            input_path,
        ]
        result = subprocess.run(cmd_check, capture_output=True, text=True)
        codec_name = result.stdout.strip()
        if codec_name == "hevc":
            logger.info(f"Видео уже в HEVC: {input_path}")
            return "skipped"

        # Создаем директорию если нужно
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Команда конвертации с сохранением метаданных
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-map_metadata",
            "0",  # Копируем все метаданные
            "-map",
            "0",  # Копируем все потоки
            "-c:v",
            "libx265",  # Видео кодек
            "-crf",
            str(crf),  # Качество
            "-preset",
            preset,  # Скорость кодирования
            "-c:a",
            "copy",  # Копируем аудио без изменений
            "-c:s",
            "copy",  # Копируем субтитры
            "-movflags",
            "use_metadata_tags",  # Сохраняем метаданные
            "-map_metadata",
            "0",  # Дублируем для совместимости
            output_path,
        ]

        # Запускаем процесс
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        # Ждем завершения
        process.communicate()

        # Проверяем результат
        if process.returncode == 0:
            # Восстанавливаем исходную дату создания/изменения
            timestamp = original_date.timestamp()
            os.utime(output_path, (timestamp, timestamp))

            if delete_original:
                os.remove(input_path)
            return "success"

        # Логируем ошибку
        logger.error(f"Ошибка конвертации {input_path} (код {process.returncode})")
        return "error"

    except Exception as e:
        logger.error(f"Критическая ошибка при конвертации {input_path}: {str(e)}")
        return "error"


def process_videos(
    video_files, crf=28, preset="fast", delete_original=False, skip_existing=True
):
    """Последовательно обрабатывает видеофайлы с сохранением даты"""
    if not video_files:
        return 0, 0, 0

    success_count = 0
    skipped_count = 0
    error_count = 0

    for video_path in tqdm(video_files, desc="Конвертация видео"):
        output_path = os.path.splitext(video_path)[0] + ".mkv"
        result = convert_video(
            video_path, output_path, crf, preset, delete_original, skip_existing
        )

        if result == "success":
            success_count += 1
        elif result == "skipped":
            skipped_count += 1
        elif result == "error":
            error_count += 1

    return success_count, skipped_count, error_count
