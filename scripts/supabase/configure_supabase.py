
import os
import sys
import logging
import psycopg2
from urllib.parse import urlparse

# Add project root to path
sys.path.append(os.getcwd())

from src.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def configure_via_sql(db_url: str, schemas: list[str]):
    """
    Updates the exposed schemas via direct SQL command.
    """
    schema_list = ", ".join(schemas)
    commands = [
        f"ALTER ROLE authenticator SET pgrst.db_schemas TO '{schema_list}';",
        "NOTIFY pgrst, 'reload config';"
    ]
    
    try:
        logger.info(f"Connecting to database to expose schemas: {schema_list}...")
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        for cmd in commands:
            logger.info(f"Executing: {cmd}")
            cursor.execute(cmd)
            
        logger.info("Successfully updated PostgREST configuration via SQL!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to execute SQL: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def main():
    # 1. Get Database URL
    # We need the DIRECT connection string (port 5432), usually available as DATABASE_URL in .env
    # If not present, we can construct it if we have user/pass/host.
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        logger.error("Error: DATABASE_URL is required in .env for this operation.")
        logger.info("Format: postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres")
        sys.exit(1)

    # 2. Define schemas
    target_schemas = ["public", "graphql_public", "app"]
    
    # 3. Execute
    success = configure_via_sql(db_url, target_schemas)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
