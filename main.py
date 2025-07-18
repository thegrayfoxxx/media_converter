import argparse
import logging
import os

from image_converter import find_image_files, process_images
from video_converter import find_video_files, process_videos

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("media_converter.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Оптимизация медиафайлов для экономии места с сохранением метаданных"
    )
    parser.add_argument("directory", help="Директория для обработки")

    # Параметры для изображений
    parser.add_argument(
        "--process-images", action="store_true", help="Обрабатывать изображения"
    )
    parser.add_argument(
        "--image-quality",
        type=int,
        default=85,
        help="Качество для изображений WebP (1-100)",
    )

    # Параметры для видео
    parser.add_argument(
        "--process-videos", action="store_true", help="Обрабатывать видео"
    )
    parser.add_argument(
        "--video-crf",
        type=int,
        default=28,
        help="CRF для видео (0-51, меньше - лучше качество)",
    )
    parser.add_argument(
        "--video-preset",
        default="fast",
        choices=[
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
            "placebo",
        ],
        help="Пресет кодирования видео (быстрее -> лучше сжатие)",
    )

    # Общие параметры
    parser.add_argument(
        "--delete-original",
        action="store_true",
        help="Удалить оригинальные файлы после конвертации",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Пропускать уже конвертированные файлы",
    )

    args = parser.parse_args()

    if not os.path.isdir(args.directory):
        logger.error(f"Директория не существует: {args.directory}")
        return

    total_stats = {
        "images": {"success": 0, "skipped": 0, "errors": 0},
        "videos": {"success": 0, "skipped": 0, "errors": 0},
    }

    # Обработка изображений
    if args.process_images:
        logger.info("Поиск изображений...")
        image_files = find_image_files(args.directory)
        logger.info(f"Найдено {len(image_files)} изображений")

        if image_files:
            logger.info("Начало конвертации изображений в WebP...")
            img_success, img_skipped, img_errors = process_images(
                image_files,
                quality=args.image_quality,
                delete_original=args.delete_original,
                skip_existing=args.skip_existing,
            )
            total_stats["images"] = {
                "success": img_success,
                "skipped": img_skipped,
                "errors": img_errors,
            }

    # Обработка видео
    if args.process_videos:
        logger.info("Поиск видеофайлов...")
        video_files = find_video_files(args.directory)
        logger.info(f"Найдено {len(video_files)} видеофайлов")

        if video_files:
            logger.info("Начало конвертации видео в H265...")
            vid_success, vid_skipped, vid_errors = process_videos(
                video_files,
                crf=args.video_crf,
                preset=args.video_preset,
                delete_original=args.delete_original,
                skip_existing=args.skip_existing,
            )
            total_stats["videos"] = {
                "success": vid_success,
                "skipped": vid_skipped,
                "errors": vid_errors,
            }

    # Вывод итоговой статистики
    logger.info("\n" + "=" * 50)
    logger.info("ОБРАБОТКА ЗАВЕРШЕНА")
    logger.info("=" * 50)

    if args.process_images:
        img = total_stats["images"]
        logger.info(
            f"ИЗОБРАЖЕНИЯ: Успешно: {img['success']}, Пропущено: {img['skipped']}, Ошибки: {img['errors']}"
        )

    if args.process_videos:
        vid = total_stats["videos"]
        logger.info(
            f"ВИДЕО: Успешно: {vid['success']}, Пропущено: {vid['skipped']}, Ошибки: {vid['errors']}"
        )

    logger.info("=" * 50)


if __name__ == "__main__":
    main()
