import os
from dotenv import load_dotenv

load_dotenv()

SERVER   = os.getenv('DB_SERVER', 'VICTOR\\SQLEXPRESS')
DATABASE = os.getenv('DB_NAME', 'LogisticaDB')
DRIVER   = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')

CONNECTION_STRING = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

SECRET_KEY = os.getenv('SECRET_KEY', 'logistica_secret_2024')
