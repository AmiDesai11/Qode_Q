"""
Centralized logging module for X-Scraper project.

This module provides logging functionality with automatic directory management
and structured log formatting for all project components.
"""

import os
import logging
import inspect
from datetime import datetime
from pathlib import Path


class Logger:
    """
    Centralized logger class for managing application logs.

    This class handles log directory creation, date-wise log organization,
    and provides structured logging functionality for all project modules.
    """

    def __init__(self, base_path: str = None):
        """
        Initialize the Logger instance.

        Args:
            base_path (str, optional): Base directory path for logs.
                                        Defaults to parent directory of current file.
        """
        if base_path is None:
            self.logs_dir = Path("../logs")
        else:
            self.base_path = Path(base_path)
            self.logs_dir = self.base_path / "logs"

        self._create_log_directory()

    def _create_log_directory(self):
        """
        Create the main logs directory if it does not exist.

        This private method ensures that the logs folder exists in the
        parent directory before any logging operations.

        Returns:
            None
        """
        if not self.logs_dir.exists():
            self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _create_date_folder(self):
        """
        Create a date-wise folder for current date logs.

        This private method creates a folder with the current date in
        'dd-mm-yyyy' format within the logs directory if it does not exist.

        Returns:
            Path: Path object pointing to the date-wise log folder.
        """
        current_date = datetime.now().strftime("%d-%m-%Y")
        date_folder = self.logs_dir / current_date

        if not date_folder.exists():
            date_folder.mkdir(parents=True, exist_ok=True)

        return date_folder

    def log(
        self,
        level: str,
        class_name: str,
        function_name: str,
        line_number: int,
        message: str
    ):
        """
        Log a message with specified parameters.

        This public method logs messages with structured formatting including
        timestamp, level, class, function, line number, and message content.
        The log is saved in a date-wise folder within the logs directory.

        Args:
            level (str): Log level (INFO, ERROR, CRITICAL, WARNING, DEBUG).
            class_name (str): Name of the class generating the log.
            function_name (str): Name of the function generating the log.
            line_number (int): Line number where log is generated.
            message (str): The log message content.

        Returns:
            None
        """
        date_folder = self._create_date_folder()
        log_file = date_folder / "app.log"

        current_time = datetime.now().strftime("%H:%M:%S")

        log_entry = (
            f"{current_time} - {level.upper()} - {class_name} - "
            f"{function_name} - {line_number} - {message}\n"
        )

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

        level_map = {
            "INFO": logging.INFO,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
            "WARNING": logging.WARNING,
            "DEBUG": logging.DEBUG,
        }

        console_logger = logging.getLogger("x-scraper")
        if not console_logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S",
            )
            handler.setFormatter(formatter)
            console_logger.addHandler(handler)
            console_logger.setLevel(logging.DEBUG)

        log_level = level_map.get(level.upper(), logging.INFO)
        console_message = f"{class_name} - {function_name} - {line_number} - {message}"
        console_logger.log(log_level, console_message)


def _ln() -> int:
    """
    Return the caller line number for logging.

    Returns:
        int: Line number of the caller.
    """
    return inspect.currentframe().f_back.f_lineno