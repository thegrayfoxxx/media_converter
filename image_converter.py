import concurrent.futures
import datetime
import logging
import os

from PIL import Image
from PIL.ExifTags import TAGS
from tqdm import tqdm

logger = logging.getLogger(__name__)
IMAGE_FORMATS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".gif")


def find_image_files(directory):
    """Рекурсивно находит все изображения в указанной директории."""
    image_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(IMAGE_FORMATS):
                image_files.append(os.path.join(root, file))
    return image_files


def get_original_datetime(image_path):
    """Получает дату съемки из метаданных изображения"""
    try:
        with Image.open(image_path) as img:
            exif = img.getexif()
            if exif:
                for tag, value in exif.items():
                    tag_name = TAGS.get(tag, tag)
                    if tag_name == "DateTimeOriginal":
                        return datetime.datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    # Если метаданных нет, используем дату изменения файла
    return datetime.datetime.fromtimestamp(os.path.getmtime(image_path))


def convert_image_to_webp(
    image_path, quality=85, delete_original=False, skip_existing=True
):
    """Конвертирует изображение в формат WebP с сохранением метаданных"""
    try:
        output_path = os.path.splitext(image_path)[0] + ".webp"

        # Пропуск существующих файлов
        if skip_existing and os.path.exists(output_path):
            return "skipped"

        # Сохраняем исходные метаданные
        original_date = get_original_datetime(image_path)

        # Создание директории если нужно
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with Image.open(image_path) as img:
            # Сохраняем EXIF данные
            exif_data = img.info.get("exif", b"")

            # Конвертация в RGB для JPEG
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Сохраняем изображение с исходными EXIF
            save_params = {
                "quality": quality,
                "method": 6,
            }
            if exif_data:
                save_params["exif"] = exif_data

            img.save(output_path, "webp", **save_params)

        # Восстанавливаем исходную дату создания/изменения
        timestamp = original_date.timestamp()
        os.utime(output_path, (timestamp, timestamp))

        if delete_original:
            os.remove(image_path)

        return "success"
    except Exception as e:
        logger.error(f"Ошибка при конвертации {image_path}: {str(e)}")
        return "error"


def process_images(images, quality=85, delete_original=False, skip_existing=True):
    """Обрабатывает изображения с сохранением метаданных"""
    if not images:
        return 0, 0, 0

    success_count = 0
    skipped_count = 0
    error_count = 0

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = []
        for img in images:
            futures.append(
                executor.submit(
                    convert_image_to_webp, img, quality, delete_original, skip_existing
                )
            )

        # Обработка результатов с прогресс-баром
        for future in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(images),
            desc="Конвертация изображений",
        ):
            result = future.result()
            if result == "success":
                success_count += 1
            elif result == "skipped":
                skipped_count += 1
            elif result == "error":
                error_count += 1

    return success_count, skipped_count, error_count
