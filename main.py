import pandas as pd
import psycopg2
import json
import ast
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any, List
import os
import logging
import numpy as np

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'Data',
    'user': 'postgres',
    'password': '2006',
    'port': 5432
}

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CSVPostgreSQLParser:
    def __init__(self, db_config: Dict[str, Any]):
        """Initialize the parser with database configuration."""
        self.db_config = db_config
        self.connection = None
        
    def connect_to_db(self):
        """Establish connection to PostgreSQL database."""
        try:
            self.connection = psycopg2.connect(**self.db_config)
            self.connection.autocommit = False
            logger.info("Successfully connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def close_connection(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def safe_eval_json(self, json_str: str) -> Optional[str]:
        """
        Safely evaluate JSON-like strings with single quotes and convert to proper JSON.
        Handles both list and dict structures.
        """
        if pd.isna(json_str) or json_str == '' or json_str is None:
            return None
        
        try:
            if json_str.startswith('"') and json_str.endswith('"'):
                json_str = json_str[1:-1]  # Remove outer quotes
            
            parsed = ast.literal_eval(json_str)
            
            return json.dumps(parsed)
        
        except (ValueError, SyntaxError) as e:
            try:
                cleaned = json_str.replace("'", '"')
                parsed = json.loads(cleaned)
                return json.dumps(parsed)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse JSON: {json_str[:100]}...")
                return None
    
    def create_movies_metadata_table(self):
        create_table_sql = """
        DROP TABLE IF EXISTS movies_metadata CASCADE;
        CREATE TABLE movies_metadata (
            adult BOOLEAN,
            belongs_to_collection JSONB,
            budget BIGINT,
            genres JSONB,
            homepage TEXT,
            id INTEGER PRIMARY KEY,
            imdb_id VARCHAR(10),
            original_language VARCHAR(10),
            original_title TEXT,
            overview TEXT,
            popularity FLOAT,
            poster_path TEXT,
            production_companies JSONB,
            production_countries JSONB,
            release_date DATE,
            revenue BIGINT,
            runtime FLOAT,
            spoken_languages JSONB,
            status VARCHAR(50),
            tagline TEXT,
            title TEXT,
            video BOOLEAN,
            vote_average FLOAT,
            vote_count INTEGER
        );
        """
        
        with self.connection.cursor() as cursor:
            cursor.execute(create_table_sql)
            self.connection.commit()
            logger.info("Created movies_metadata table")
    
    def create_links_table(self):
        """Create the links table."""
        create_table_sql = """
        DROP TABLE IF EXISTS links CASCADE;
        CREATE TABLE links (
            movieId INTEGER PRIMARY KEY,
            imdbId VARCHAR(10),
            tmdbId BIGINT
        );
        """
        
        with self.connection.cursor() as cursor:
            cursor.execute(create_table_sql)
            self.connection.commit()
            logger.info("Created links table")
    
    def create_credits_table(self):
        """Create the credits table."""
        create_table_sql = """
        DROP TABLE IF EXISTS credits CASCADE;
        CREATE TABLE credits (
            "cast" JSONB,
            crew JSONB,
            id INTEGER PRIMARY KEY
        );
        """
        
        with self.connection.cursor() as cursor:
            cursor.execute(create_table_sql)
            self.connection.commit()
            logger.info("Created credits table")
    
    def clean_dataframe_for_postgres(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean DataFrame to handle PostgreSQL compatibility issues."""
        df_clean = df.copy()
        
        # Handle NaN and NaT values
        for col in df_clean.columns:
            if df_clean[col].dtype == 'datetime64[ns]':
                # Convert NaT to None
                df_clean[col] = df_clean[col].where(pd.notna(df_clean[col]), None)
            elif df_clean[col].dtype == 'object':
                # Handle string NaN values
                df_clean[col] = df_clean[col].where(pd.notna(df_clean[col]), None)
            elif np.issubdtype(df_clean[col].dtype, np.number):
                # Handle numeric NaN values
                df_clean[col] = df_clean[col].where(pd.notna(df_clean[col]), None)
        
        return df_clean
    
    def process_movies_metadata(self, csv_file: str, chunk_size: int = 1000):
        """Process and import movies_metadata.csv."""
        logger.info(f"Processing {csv_file}")
        
        # JSON columns that need special handling
        json_columns = ['belongs_to_collection', 'genres', 'production_companies', 
                       'production_countries', 'spoken_languages']
        
        # Read CSV in chunks to handle large files
        chunk_count = 0
        for chunk in pd.read_csv(csv_file, chunksize=chunk_size, low_memory=False):
            chunk_count += 1
            logger.info(f"Processing chunk {chunk_count}")
            
            # Process JSON columns
            for col in json_columns:
                if col in chunk.columns:
                    chunk[col] = chunk[col].apply(self.safe_eval_json)
            
            # Handle boolean columns
            chunk['adult'] = chunk['adult'].astype(str).str.lower() == 'true'
            chunk['video'] = chunk['video'].astype(str).str.lower() == 'true'
            
            # Handle date columns - convert to datetime and handle errors
            chunk['release_date'] = pd.to_datetime(chunk['release_date'], errors='coerce')
            
            # Clean the DataFrame
            chunk = self.clean_dataframe_for_postgres(chunk)
            
            # Insert data
            self._insert_dataframe_to_table(chunk, 'movies_metadata')
    
    def process_links(self, csv_file: str, chunk_size: int = 5000):
        """Process and import links.csv."""
        logger.info(f"Processing {csv_file}")
        
        chunk_count = 0
        for chunk in pd.read_csv(csv_file, chunksize=chunk_size):
            chunk_count += 1
            logger.info(f"Processing chunk {chunk_count}")
            
            # Clean the DataFrame
            chunk = self.clean_dataframe_for_postgres(chunk)
            
            # Insert data directly (no JSON columns)
            self._insert_dataframe_to_table(chunk, 'links')
    
    def process_credits(self, csv_file: str, chunk_size: int = 1000):
        """Process and import credits.csv."""
        logger.info(f"Processing {csv_file}")
        
        chunk_count = 0
        for chunk in pd.read_csv(csv_file, chunksize=chunk_size):
            chunk_count += 1
            logger.info(f"Processing chunk {chunk_count}")
            
            # Process JSON columns
            if 'cast' in chunk.columns:
                chunk['cast'] = chunk['cast'].apply(self.safe_eval_json)
            if 'crew' in chunk.columns:
                chunk['crew'] = chunk['crew'].apply(self.safe_eval_json)
            
            # Clean the DataFrame
            chunk = self.clean_dataframe_for_postgres(chunk)
            
            # Insert data with special handling for quoted column names
            self._insert_credits_to_table(chunk)
    
    def _insert_dataframe_to_table(self, df: pd.DataFrame, table_name: str):
        """Insert DataFrame data into PostgreSQL table."""
        try:
            # Get column names
            columns = ', '.join(df.columns)
            placeholders = ', '.join(['%s'] * len(df.columns))
            
            insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            
            with self.connection.cursor() as cursor:
                # Convert DataFrame to list of tuples, properly handling None values
                data = []
                for _, row in df.iterrows():
                    row_data = []
                    for value in row:
                        if pd.isna(value) or value is None:
                            row_data.append(None)
                        else:
                            row_data.append(value)
                    data.append(tuple(row_data))
                
                cursor.executemany(insert_sql, data)
                self.connection.commit()
                logger.info(f"Inserted {len(data)} rows into {table_name}")
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error inserting data into {table_name}: {e}")
            raise
    
    def _insert_credits_to_table(self, df: pd.DataFrame):
        """Insert credits DataFrame data with quoted column names."""
        try:
            # Handle the reserved keyword 'cast' by quoting it
            columns = []
            for col in df.columns:
                if col == 'cast':
                    columns.append('"cast"')
                else:
                    columns.append(col)
            
            columns_str = ', '.join(columns)
            placeholders = ', '.join(['%s'] * len(df.columns))
            
            insert_sql = f"INSERT INTO credits ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            
            with self.connection.cursor() as cursor:
                # Convert DataFrame to list of tuples, properly handling None values
                data = []
                for _, row in df.iterrows():
                    row_data = []
                    for value in row:
                        if pd.isna(value) or value is None:
                            row_data.append(None)
                        else:
                            row_data.append(value)
                    data.append(tuple(row_data))
                
                cursor.executemany(insert_sql, data)
                self.connection.commit()
                logger.info(f"Inserted {len(data)} rows into credits")
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error inserting data into credits: {e}")
            raise
    
    def create_all_tables(self):
        """Create all necessary tables."""
        self.create_movies_metadata_table()
        self.create_links_table()
        self.create_credits_table()
    
    def import_all_csv_files(self, base_path: str = '.'):
        """Import all CSV files from the specified directory."""
        csv_files = {
            'movies_metadata.csv': self.process_movies_metadata,
            'links.csv': self.process_links,
            'credits.csv': self.process_credits
        }
        
        for filename, processor in csv_files.items():
            filepath = os.path.join(base_path, filename)
            if os.path.exists(filepath):
                try:
                    processor(filepath)
                    logger.info(f"Successfully processed {filename}")
                except Exception as e:
                    logger.error(f"Failed to process {filename}: {e}")
            else:
                logger.warning(f"File not found: {filepath}")

def main():
    """Main function to run the CSV parser."""
    parser = CSVPostgreSQLParser(DB_CONFIG)
    
    try:
        # Connect to database
        parser.connect_to_db()
        
        # Create tables
        logger.info("Creating database tables...")
        parser.create_all_tables()
        
        # Import CSV files
        logger.info("Starting CSV import process...")
        parser.import_all_csv_files()
        
        logger.info("CSV import process completed successfully!")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise
    
    finally:
        parser.close_connection()

if __name__ == "__main__":
    main()