"""
Logging configuration for JellyDemon.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import Config


def setup_logging(config: 'Config') -> logging.Logger:
    """Setup logging configuration."""
    logger = logging.getLogger('jellydemon')
    
    # Set log level
    log_level = getattr(logging, config.daemon.log_level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    if config.daemon.log_file:
        log_file = Path(config.daemon.log_file)
        
        # Parse max size (convert "10MB" to bytes)
        max_size = config.daemon.log_max_size
        if max_size.upper().endswith('MB'):
            max_bytes = int(max_size[:-2]) * 1024 * 1024
        elif max_size.upper().endswith('KB'):
            max_bytes = int(max_size[:-2]) * 1024
        else:
            max_bytes = int(max_size)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=config.daemon.log_backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Don't propagate to root logger
    logger.propagate = False
    
    return logger 