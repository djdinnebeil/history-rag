# config.py
import os
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables once
load_dotenv()

# Set up all required environment variables
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["COHERE_API_KEY"] = os.getenv("COHERE_API_KEY") 
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

# Feature flags
using_cohere = True  # Set to False to disable Cohere reranking for debugging

# Developer mode
developer_mode = True

# Directory paths
PROJECTS_DIR = Path.cwd() / "projects"
ARCHIVE_DIR = Path.cwd() / "archive"

# Processing settings
BATCH_SIZE = 12  # tune for performance

# Model settings
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4.1-nano"
AGENT_MODEL = "gpt-4.1-nano"

# Vector store settings
DEFAULT_COLLECTION_PREFIX = "_docs"
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 80

# Retrieval settings
ENABLE_DYNAMIC_RETRIEVAL_SCALING = True  # Set to False to use fixed retrieval parameters
FIXED_RETRIEVAL_K = 15  # Used when dynamic scaling is disabled
FIXED_FINAL_K = 10  # Used when dynamic scaling is disabled

# UI settings
DEFAULT_SOURCE_TYPES = ["book", "journal", "newspaper", "report", "web_article", "misc", "unsorted"]
DEFAULT_SEARCH_MODE = "Standard"

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# =============================================================================
# EASY LOGGING CONTROL - MODIFY THESE SETTINGS AS NEEDED
# =============================================================================

# Set to True to disable all logging output
DISABLE_LOGGING = False

# Set the logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
# DEBUG = most verbose, CRITICAL = least verbose
LOG_LEVEL = "DEBUG"

# =============================================================================
# ADVANCED LOGGING SETTINGS (usually no need to change these)
# =============================================================================

# Override with environment variables if set
if os.getenv("DISABLE_LOGGING"):
    DISABLE_LOGGING = os.getenv("DISABLE_LOGGING", "false").lower() in ("true", "1", "yes", "on")

if os.getenv("LOG_LEVEL"):
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Global flag to track if logging has been configured
_logging_configured = False

def setup_logging():
    """Configure logging for the application (singleton pattern)."""
    global _logging_configured
    
    # Only configure logging once
    if _logging_configured:
        return
    
    # Check if logging is disabled
    if DISABLE_LOGGING:
        # Set root logger to CRITICAL level to suppress all logs
        logging.getLogger().setLevel(logging.CRITICAL)
        _logging_configured = True
        return
    
    # Create a custom formatter
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    # Configure root logger to WARNING level to suppress third-party debug messages
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)
    
    # Only add handler if it doesn't already exist
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.addHandler(console_handler)
    
    # Create a separate handler for application debug messages
    app_handler = logging.StreamHandler(sys.stdout)
    app_handler.setFormatter(formatter)
    app_handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    
    # Set specific loggers to appropriate levels to suppress third-party debug messages
    # Core libraries
    logging.getLogger("streamlit").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    
    # AI/ML libraries
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)
    logging.getLogger("langchain_core").setLevel(logging.WARNING)
    logging.getLogger("langchain_community").setLevel(logging.WARNING)
    logging.getLogger("langchain_openai").setLevel(logging.WARNING)
    logging.getLogger("langchain_qdrant").setLevel(logging.WARNING)
    logging.getLogger("langgraph").setLevel(logging.WARNING)
    logging.getLogger("langsmith").setLevel(logging.WARNING)
    logging.getLogger("tavily").setLevel(logging.WARNING)
    
    # Database and vector stores
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    
    # Data processing libraries
    logging.getLogger("pandas").setLevel(logging.WARNING)
    logging.getLogger("numpy").setLevel(logging.WARNING)
    logging.getLogger("pydantic").setLevel(logging.WARNING)
    logging.getLogger("pydantic_core").setLevel(logging.WARNING)
    
    # HTTP and networking
    logging.getLogger("h11").setLevel(logging.WARNING)
    logging.getLogger("h2").setLevel(logging.WARNING)
    logging.getLogger("hpack").setLevel(logging.WARNING)
    logging.getLogger("hyperframe").setLevel(logging.WARNING)
    logging.getLogger("grpcio").setLevel(logging.WARNING)
    
    # Other common libraries that generate debug messages
    logging.getLogger("tornado").setLevel(logging.WARNING)
    logging.getLogger("tornado.access").setLevel(logging.WARNING)
    logging.getLogger("tornado.application").setLevel(logging.WARNING)
    logging.getLogger("tornado.general").setLevel(logging.WARNING)
    logging.getLogger("watchdog").setLevel(logging.WARNING)
    logging.getLogger("git").setLevel(logging.WARNING)
    logging.getLogger("gitpython").setLevel(logging.WARNING)
    logging.getLogger("tqdm").setLevel(logging.WARNING)
    
    # Set root level for any other third-party libraries
    # This ensures that only your application code shows DEBUG messages
    for logger_name in logging.Logger.manager.loggerDict:
        if not logger_name.startswith(('historical_research_assistant', '__main__')):
            logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Set the log level specifically for your application modules
    set_application_log_level(LOG_LEVEL)
    
    # Mark as configured
    _logging_configured = True
    
    # Log the configuration only once
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {LOG_LEVEL}")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    logger = logging.getLogger(name)
    
    # Ensure the logger is properly configured
    if not logger.handlers and LOG_LEVEL != "CRITICAL":
        # Create a handler for this specific logger
        formatter = logging.Formatter(
            fmt=LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        logger.addHandler(handler)
        logger.propagate = False
    
    return logger

def set_application_log_level(level: str):
    """Set the log level specifically for your application modules."""
    app_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create a dedicated handler for application loggers
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT
    )
    app_handler = logging.StreamHandler(sys.stdout)
    app_handler.setFormatter(formatter)
    app_handler.setLevel(app_level)
    
    # Set level for your application modules and add the handler
    for logger_name in logging.Logger.manager.loggerDict:
        if logger_name.startswith(('historical_research_assistant', '__main__')):
            logger = logging.getLogger(logger_name)
            logger.setLevel(app_level)
            # Clear existing handlers and add our app handler
            logger.handlers.clear()
            logger.addHandler(app_handler)
            logger.propagate = False  # Prevent propagation to root logger
    
    # Also set the root logger level for your application
    logging.getLogger().setLevel(app_level)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def ensure_directories():
    """Ensure all required directories exist."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

def initialize_app():
    """Initialize the application with directories and logging."""
    ensure_directories()
    setup_logging()

def get_project_path(project_name: str) -> Path:
    """Get the full path for a project directory."""
    return PROJECTS_DIR / project_name

def get_archive_path(archive_name: str) -> Path:
    """Get the full path for an archive file."""
    return ARCHIVE_DIR / archive_name