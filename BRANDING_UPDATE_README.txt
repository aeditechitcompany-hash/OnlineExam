NIBANGSH ONLINE EXAM BRANDING UPDATE

Included changes:
- Original Nibangsh logo added at static/branding/nibangsh-logo.png
- Branded site header and footer with official website and contact details
- Clickable WhatsApp links for +977 9851001970
- Redesigned student dashboard while preserving existing exam-card context and URL routes
- Subtle non-interactive logo watermark on the live take-exam question card
- Confidential label on the live exam page
- Existing mobile question navigator retained

No print, PDF export, or question-paper download feature has been added.

Deployment notes:
1. Back up the current project before replacing files.
2. Merge the included templates/ and static/ folders into the project.
3. Ensure Django static files are collected during deployment (python manage.py collectstatic --noinput) if the hosting setup uses STATIC_ROOT.
4. Test dashboard, exam start/continue, answer autosave, question navigation, timer, submission, and WhatsApp links before promoting to production.

The archive intentionally excludes .env, local databases, virtual environments, Git metadata, and backup files. Keep your existing environment variables and database unchanged.
