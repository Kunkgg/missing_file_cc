"""
Database migration script to update scan result statistics columns.

This script updates the missing_file_scan_results table to:
- Remove total_missing column
- Add passed_count, target_file_count, baseline_file_count columns
- Add target_project_count, baseline_project_count columns
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def build_connection_url() -> str:
    """Build MySQL connection URL from environment variables."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "missing_file_check")

    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"


def migrate_database():
    """Execute database migration."""
    try:
        # Create engine
        connection_url = build_connection_url()
        engine = create_engine(connection_url, echo=True)

        print("=" * 70)
        print("Database Migration: Update Statistics Columns")
        print("=" * 70)

        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()

            try:
                # Check if table exists
                result = conn.execute(
                    text(
                        """
                    SELECT COUNT(*) as count
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                    AND table_name = 'missing_file_scan_results'
                    """
                    )
                )
                if result.fetchone()[0] == 0:
                    print("\n⚠️  Table 'missing_file_scan_results' does not exist.")
                    print("   Please run 'create_tables.py' first.")
                    return False

                # Check if total_missing column exists
                result = conn.execute(
                    text(
                        """
                    SELECT COUNT(*) as count
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                    AND table_name = 'missing_file_scan_results'
                    AND column_name = 'total_missing'
                    """
                    )
                )

                if result.fetchone()[0] == 0:
                    print("\n✅ Migration already applied or table is up to date.")
                    return True

                print("\n📝 Applying migration...")

                # Add new columns
                print("   Adding new columns...")
                conn.execute(
                    text(
                        """
                    ALTER TABLE missing_file_scan_results
                    ADD COLUMN passed_count INT DEFAULT 0 AFTER failed_count,
                    ADD COLUMN target_file_count INT DEFAULT 0 AFTER remapped_count,
                    ADD COLUMN baseline_file_count INT DEFAULT 0 AFTER target_file_count,
                    ADD COLUMN target_project_count INT DEFAULT 0 AFTER baseline_file_count,
                    ADD COLUMN baseline_project_count INT DEFAULT 0 AFTER target_project_count
                    """
                    )
                )

                # Calculate passed_count from existing data
                print("   Calculating passed_count from existing data...")
                conn.execute(
                    text(
                        """
                    UPDATE missing_file_scan_results
                    SET passed_count = IFNULL(shielded_count, 0) + IFNULL(remapped_count, 0)
                    WHERE passed_count = 0
                    """
                    )
                )

                # Drop old column
                print("   Dropping total_missing column...")
                conn.execute(
                    text(
                        """
                    ALTER TABLE missing_file_scan_results
                    DROP COLUMN total_missing
                    """
                    )
                )

                # Commit transaction
                trans.commit()

                print("\n✅ Migration completed successfully!")
                print("\n📊 New columns added:")
                print("   - passed_count (calculated from shielded + remapped)")
                print("   - target_file_count (defaults to 0)")
                print("   - baseline_file_count (defaults to 0)")
                print("   - target_project_count (defaults to 0)")
                print("   - baseline_project_count (defaults to 0)")
                print("\n⚠️  Note: File count columns are set to 0 for existing records.")
                print("   They will be populated correctly for new scans.")

                return True

            except Exception as e:
                trans.rollback()
                print(f"\n❌ Migration failed: {e}")
                return False

    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")
        return False


def main():
    """Main entry point."""
    print("\n🔧 Database Migration Tool")
    print("   Updates statistics columns in scan_results table\n")

    # Check environment
    if not os.getenv("DB_HOST"):
        print("⚠️  Warning: DB_HOST not set in environment")
        print("   Please configure .env file or set environment variables")
        print("\n   Required variables:")
        print("   - DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME")
        return 1

    # Confirm migration
    print("This will modify the database schema:")
    print("  - Remove: total_missing column")
    print("  - Add: passed_count, target_file_count, baseline_file_count,")
    print("         target_project_count, baseline_project_count columns")
    print("\nContinue? (yes/no): ", end="")

    response = input().strip().lower()
    if response not in ("yes", "y"):
        print("Migration cancelled.")
        return 0

    # Execute migration
    if migrate_database():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
