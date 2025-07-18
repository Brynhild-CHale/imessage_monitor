#!/usr/bin/env python3
"""Test script to explore Apple's chat.db structure."""

import sqlite3
import sys
from pathlib import Path


def explore_database(db_path: str):
    """Explore the Apple chat.db structure and print table schemas."""
    try:
        # Connect to database
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        
        print(f"=== Exploring Apple chat.db at {db_path} ===\n")
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
        print()
        
        # For each table, get the schema
        for table in tables:
            table_name = table[0]
            print(f"=== Table: {table_name} ===")
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("Columns:")
            for col in columns:
                col_id, name, data_type, not_null, default_val, primary_key = col
                pk_str = " (PRIMARY KEY)" if primary_key else ""
                nn_str = " NOT NULL" if not_null else ""
                default_str = f" DEFAULT {default_val}" if default_val else ""
                print(f"  {name}: {data_type}{nn_str}{default_str}{pk_str}")
            
            # Get row count
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"Row count: {count}")
            except sqlite3.Error as e:
                print(f"Could not get row count: {e}")
            
            # Show sample data for key tables
            if table_name in ['message', 'handle', 'chat'] and count > 0:
                print("Sample data (first 2 rows):")
                try:
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 2")
                    sample_rows = cursor.fetchall()
                    for i, row in enumerate(sample_rows, 1):
                        print(f"  Row {i}: {dict(zip([col[1] for col in columns], row))}")
                except sqlite3.Error as e:
                    print(f"Could not get sample data: {e}")
            
            print()
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Main function."""
    # Default path to Apple's chat.db
    default_path = Path.home() / "Library" / "Messages" / "chat.db"
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = str(default_path)
    
    if not Path(db_path).exists():
        print(f"Error: Database file not found at {db_path}")
        print(f"Usage: python {sys.argv[0]} [path_to_chat.db]")
        sys.exit(1)
    
    explore_database(db_path)


if __name__ == "__main__":
    main()