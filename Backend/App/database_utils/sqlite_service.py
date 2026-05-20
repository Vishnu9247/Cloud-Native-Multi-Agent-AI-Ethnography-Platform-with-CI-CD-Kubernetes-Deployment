from App.database_utils.data_loader import ensure_database
from App.general_utils.logging_config import get_logger


logger = get_logger(__name__)


if __name__ == "__main__":
    ensure_database()
    logger.info("database_initialized")
