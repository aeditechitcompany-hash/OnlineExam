
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

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database(), current_user")
        print("Connected database and user:", cursor.fetchone())

        cursor.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
              AND tablename IN (
                  'mcq_questionset',
                  'mcq_question',
                  'mcq_option',
                  'mcq_mcqsection'
              )
            ORDER BY tablename
        """)
        print("MCQ tables:", cursor.fetchall())
finally:
    connection.close()
