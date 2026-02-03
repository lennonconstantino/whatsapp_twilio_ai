
import os
import sys
import logging
import psycopg2
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

# Load .env
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def grant_permissions(db_url: str):
    """
    Grants necessary permissions for PostgREST roles on the 'app' schema.
    """
    commands = [
        # 1. Grant USAGE on schema 'app'
        "GRANT USAGE ON SCHEMA app TO anon, authenticated, service_role;",
        
        # 2. Grant access to all tables in 'app'
        "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO anon, authenticated, service_role;",
        
        # 3. Grant access to all sequences in 'app' (important for auto-increment IDs)
        "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app TO anon, authenticated, service_role;",
        
        # 4. Ensure future tables also get these permissions (optional but recommended)
        "ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON TABLES TO anon, authenticated, service_role;",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON SEQUENCES TO anon, authenticated, service_role;"
    ]
    
    try:
        logger.info("Connecting to database to grant permissions...")
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        for cmd in commands:
            logger.info(f"Executing: {cmd}")
            cursor.execute(cmd)
            
        logger.info("Successfully granted permissions on schema 'app'!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to execute SQL: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL is required in .env")
        sys.exit(1)

    grant_permissions(db_url)

if __name__ == "__main__":
    main()
