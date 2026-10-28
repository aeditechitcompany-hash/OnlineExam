
import os
from pathlib import Path

import django
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connections

connection = connections["source_mcq"]

tables = [
    "mcq_questionset",
    "mcq_question",
    "mcq_option",
    "mcq_mcqsection",
]

try:
    with connection.cursor() as cursor:
        for table in tables:
            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                ORDER BY ordinal_position
                """,
                [table],
            )

            print(f"\n--- {table} ---")
            for column_name, data_type in cursor.fetchall():
                print(f"{column_name}: {data_type}")
finally:
    connection.close()
