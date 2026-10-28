
from django.core.management.base import BaseCommand
from django.db import connections


class Command(BaseCommand):
    help = "List question sets from the read-only source MCQ database"

    def handle(self, *args, **options):
        connection = connections["source_mcq"]

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        qs.id,
                        qs.title,
                        qs.category,
                        qs.is_active,
                        COUNT(q.id) AS question_count
                    FROM mcq_questionset qs
                    LEFT JOIN mcq_question q
                        ON q.question_set_id = qs.id
                    GROUP BY
                        qs.id,
                        qs.title,
                        qs.category,
                        qs.is_active,
                        qs.created_at
                    ORDER BY qs.created_at DESC
                """)

                rows = cursor.fetchall()

                if not rows:
                    self.stdout.write("No question sets found.")
                    return

                for set_id, title, category, active, count in rows:
                    self.stdout.write(
                        f"ID: {set_id} | "
                        f"Title: {title} | "
                        f"Category: {category} | "
                        f"Active: {active} | "
                        f"Questions: {count}"
                    )
        finally:
            connection.close()
