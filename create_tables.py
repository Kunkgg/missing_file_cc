"""
Database table creation script.

Creates all tables required for the missing file check system.
Run this script once to set up the database schema.
"""

import os
from dotenv import load_dotenv

from missing_file_check.storage.database import DatabaseManager
from missing_file_check.storage.models import Base

# Load environment variables from .env file
load_dotenv()


def main():
    """Create all tables in the database."""
    print("=" * 60)
    print("Missing File Check - Database Setup")
    print("=" * 60)

    # Check environment variables
    required_vars = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"\n❌ Error: Missing environment variables: {', '.join(missing_vars)}")
        print("\nPlease set the following environment variables:")
        print("  - DB_HOST: Database host")
        print("  - DB_USER: Database user")
        print("  - DB_PASSWORD: Database password")
        print("  - DB_NAME: Database name")
        print("\nYou can create a .env file in the project root with these variables.")
        return

    # Create database manager
    db_manager = DatabaseManager()

    print(f"\nConnecting to database...")
    print(f"  Host: {os.getenv('DB_HOST')}")
    print(f"  Port: {os.getenv('DB_PORT', '3306')}")
    print(f"  User: {os.getenv('DB_USER')}")
    print(f"  Database: {os.getenv('DB_NAME')}")

    try:
        # Initialize connection
        db_manager.initialize()
        print("✓ Connected successfully")

        # Create tables
        print("\nCreating tables...")
        db_manager.create_tables()
        print("✓ Tables created successfully")

        # List created tables
        print("\nCreated tables:")
        tables = [
            "missing_file_tasks",
            "missing_file_project_relation",
            "missing_file_path_prefixes",
            "missing_file_shield_rules",
            "missing_file_mapping_rules",
            "missing_file_scan_results",
            "missing_file_details",
        ]
        for table in tables:
            print(f"  ✓ {table}")

        print("\n" + "=" * 60)
        print("Database setup completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease check your database connection settings.")
        return

    finally:
        db_manager.close()


if __name__ == "__main__":
    main()
