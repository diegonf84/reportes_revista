"""
Database connection manager for consistent database access across modules.

This module provides a centralized way to manage database connections
and common database operations used throughout the application.
"""

import sqlite3
import os
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Dict, Any
from dotenv import load_dotenv
import pandas as pd

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database connection manager with consistent configuration and error handling.
    """
    
    def __init__(self):
        """Initialize database manager with environment configuration."""
        load_dotenv()
        self.db_path = os.getenv('DATABASE')
        
        if not self.db_path:
            raise ValueError("DATABASE environment variable not set")
        
        if not Path(self.db_path).exists():
            logger.warning(f"Database file does not exist: {self.db_path}")
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Context manager for database connections.
        
        Yields:
            sqlite3.Connection: Database connection
            
        Example:
            >>> db = DatabaseManager()
            >>> with db.get_connection() as conn:
            ...     cursor = conn.cursor()
            ...     cursor.execute("SELECT * FROM table")
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
            yield conn
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Unexpected error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """
        Execute a SELECT query and return results as DataFrame.
        
        Args:
            query (str): SQL query to execute
            params (Optional[tuple]): Query parameters
            
        Returns:
            pd.DataFrame: Query results
            
        Example:
            >>> db = DatabaseManager()
            >>> df = db.execute_query("SELECT * FROM tabla WHERE periodo = ?", (202501,))
        """
        with self.get_connection() as conn:
            return pd.read_sql_query(query, conn, params=params or [])
    
    def execute_non_query(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute a non-SELECT query (INSERT, UPDATE, DELETE, CREATE, etc.).
        
        Args:
            query (str): SQL query to execute
            params (Optional[tuple]): Query parameters
            
        Returns:
            int: Number of affected rows
            
        Example:
            >>> db = DatabaseManager()
            >>> rows = db.execute_non_query("DELETE FROM tabla WHERE periodo = ?", (202501,))
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or [])
            conn.commit()
            return cursor.rowcount
    
    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.
        
        Args:
            table_name (str): Name of the table to check
            
        Returns:
            bool: True if table exists, False otherwise
        """
        query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
        """
        df = self.execute_query(query, (table_name,))
        return len(df) > 0
    
    def get_table_count(self, table_name: str) -> int:
        """
        Get the number of rows in a table.
        
        Args:
            table_name (str): Name of the table
            
        Returns:
            int: Number of rows in the table
            
        Raises:
            ValueError: If table doesn't exist
        """
        if not self.table_exists(table_name):
            raise ValueError(f"Table '{table_name}' does not exist")
        
        df = self.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
        return df['count'].iloc[0]
    
    def drop_table_if_exists(self, table_name: str) -> None:
        """
        Drop a table if it exists.
        
        Args:
            table_name (str): Name of the table to drop
        """
        query = f"DROP TABLE IF EXISTS {table_name}"
        self.execute_non_query(query)
        logger.info(f"Table '{table_name}' dropped if it existed")
    
    def insert_dataframe(self, df: pd.DataFrame, table_name: str, 
                        if_exists: str = 'append') -> None:
        """
        Insert a DataFrame into a database table.
        
        Args:
            df (pd.DataFrame): DataFrame to insert
            table_name (str): Name of the target table
            if_exists (str): What to do if table exists ('fail', 'replace', 'append')
        """
        with self.get_connection() as conn:
            df.to_sql(table_name, conn, index=False, if_exists=if_exists)
            logger.info(f"Inserted {len(df):,} rows into table '{table_name}'")
    
    def get_recent_periods(self, table_name: str = 'datos_balance', 
                          limit: int = 10) -> list:
        """
        Get the most recent periods from a table.
        
        Args:
            table_name (str): Name of the table to query
            limit (int): Maximum number of periods to return
            
        Returns:
            list: List of recent periods sorted in descending order
        """
        query = f"""
        SELECT DISTINCT periodo 
        FROM {table_name} 
        ORDER BY periodo DESC 
        LIMIT ?
        """
        df = self.execute_query(query, (limit,))
        return df['periodo'].tolist()
    
    def period_exists(self, periodo: int, table_name: str = 'datos_balance') -> bool:
        """
        Check if a specific period exists in a table.
        
        Args:
            periodo (int): Period to check
            table_name (str): Name of the table to check
            
        Returns:
            bool: True if period exists, False otherwise
        """
        query = f"SELECT COUNT(*) as count FROM {table_name} WHERE periodo = ?"
        df = self.execute_query(query, (periodo,))
        return df['count'].iloc[0] > 0


# Global instance for convenience
db_manager = DatabaseManager()


# Convenience functions for backward compatibility
def get_db_connection():
    """Get database connection context manager."""
    return db_manager.get_connection()


def execute_query(query: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """Execute query and return DataFrame."""
    return db_manager.execute_query(query, params)


def execute_non_query(query: str, params: Optional[tuple] = None) -> int:
    """Execute non-query and return affected rows."""
    return db_manager.execute_non_query(query, params)