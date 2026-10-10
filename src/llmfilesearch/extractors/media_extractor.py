"""Extractor for media files: images, video, audio — metadata only."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from llmfilesearch.extractors.base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class MediaExtractor(BaseExtractor):
    """Extract metadata from image, video, and audio files."""

    def extract(self, file_path: Path) -> ExtractionResult:
        ext = file_path.suffix.lower()

        try:
            if ext in (".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a", ".opus", ".aiff"):
                return self._extract_audio(file_path)
            elif ext in (".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"):
                return self._extract_video(file_path)
            else:
                return self._extract_image(file_path)
        except Exception as e:
            logger.warning("Failed to extract media metadata from %s: %s", file_path, e)
            return ExtractionResult(status="failed", error=str(e))

    def _extract_image(self, file_path: Path) -> ExtractionResult:
        metadata: dict = {}

        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            img = Image.open(file_path)
            metadata["width"] = img.width
            metadata["height"] = img.height
            metadata["format"] = img.format or file_path.suffix.upper().strip(".")
            metadata["mode"] = img.mode

            # EXIF data
            exif_data = img.getexif()
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, str(tag_id))
                    if tag_name in ("Make", "Model", "DateTime", "DateTimeOriginal",
                                    "Software", "ImageDescription", "Artist"):
                        try:
                            metadata[tag_name.lower()] = str(value)
                        except Exception:
                            pass

            img.close()
        except Exception as e:
            logger.debug("PIL failed for %s: %s, trying exifread", file_path, e)

        # Try exifread for more detailed EXIF (especially GPS)
        try:
            import exifread

            with open(file_path, "rb") as f:
                tags = exifread.process_file(f, details=False)

            if tags:
                for key in ("EXIF DateTimeOriginal", "Image DateTime",
                            "GPS GPSLatitude", "GPS GPSLongitude",
                            "Image Make", "Image Model"):
                    if key in tags:
                        clean_key = key.split(" ", 1)[-1].lower().replace(" ", "_")
                        metadata[clean_key] = str(tags[key])
        except Exception:
            pass

        # Build a text description from metadata
        parts = []
        if "width" in metadata and "height" in metadata:
            parts.append(f"{metadata['width']}x{metadata['height']}")
        if "make" in metadata or "model" in metadata:
            camera = " ".join(filter(None, [metadata.get("make"), metadata.get("model")]))
            parts.append(f"Camera: {camera}")
        if "datetimeoriginal" in metadata:
            parts.append(f"Taken: {metadata['datetimeoriginal']}")
        elif "datetime" in metadata:
            parts.append(f"Date: {metadata['datetime']}")
        if "gpslatitude" in metadata:
            parts.append(f"GPS: {metadata.get('gpslatitude')}, {metadata.get('gpslongitude', 'N/A')}")

        text = ". ".join(parts) if parts else ""

        return ExtractionResult(
            text=text,
            metadata=metadata,
            status="metadata_only",
        )

    def _extract_audio(self, file_path: Path) -> ExtractionResult:
        metadata: dict = {}

        try:
            from mutagen import File as MutagenFile

            audio = MutagenFile(file_path)
            if audio is not None:
                if audio.info:
                    metadata["duration_seconds"] = round(audio.info.length, 1)
                    if hasattr(audio.info, "sample_rate"):
                        metadata["sample_rate"] = audio.info.sample_rate
                    if hasattr(audio.info, "bitrate"):
                        metadata["bitrate"] = audio.info.bitrate

                # Common tags
                for key in ("title", "artist", "album", "date", "genre", "tracknumber"):
                    values = audio.get(key) or audio.get(key.upper())
                    if values:
                        val = values[0] if isinstance(values, list) else values
                        metadata[key] = str(val)
        except Exception as e:
            logger.debug("Mutagen failed for %s: %s", file_path, e)

        parts = []
        if "title" in metadata:
            parts.append(metadata["title"])
        if "artist" in metadata:
            parts.append(f"by {metadata['artist']}")
        if "album" in metadata:
            parts.append(f"Album: {metadata['album']}")
        if "duration_seconds" in metadata:
            mins = int(metadata["duration_seconds"] // 60)
            secs = int(metadata["duration_seconds"] % 60)
            parts.append(f"Duration: {mins}:{secs:02d}")

        text = ". ".join(parts) if parts else ""

        return ExtractionResult(
            text=text,
            metadata=metadata,
            status="metadata_only",
        )

    def _extract_video(self, file_path: Path) -> ExtractionResult:
        metadata: dict = {}

        # Use mutagen for video container metadata
        try:
            from mutagen import File as MutagenFile

            video = MutagenFile(file_path)
            if video is not None and video.info:
                metadata["duration_seconds"] = round(video.info.length, 1)
                if hasattr(video.info, "width") and video.info.width:
                    metadata["width"] = video.info.width
                if hasattr(video.info, "height") and video.info.height:
                    metadata["height"] = video.info.height
                if hasattr(video.info, "bitrate") and video.info.bitrate:
                    metadata["bitrate"] = video.info.bitrate
        except Exception as e:
            logger.debug("Mutagen failed for video %s: %s", file_path, e)

        parts = []
        if "width" in metadata and "height" in metadata:
            parts.append(f"{metadata['width']}x{metadata['height']}")
        if "duration_seconds" in metadata:
            mins = int(metadata["duration_seconds"] // 60)
            secs = int(metadata["duration_seconds"] % 60)
            parts.append(f"Duration: {mins}:{secs:02d}")

        text = ". ".join(parts) if parts else ""

        return ExtractionResult(
            text=text,
            metadata=metadata,
            status="metadata_only",
        )
