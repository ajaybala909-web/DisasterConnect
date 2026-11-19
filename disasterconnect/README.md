# DisasterConnect (academic prototype)

## Easiest way to run
- Windows: double-click run.bat
- Mac/Linux: run ./run.sh in a terminal (first time: chmod +x run.sh)
- VS Code: open this folder, open the terminal, type  .\run.bat  (Windows)  or  ./run.sh

The first run installs everything (about a minute). The browser opens at http://localhost:5000.
Admin page: http://localhost:5000/admin/login   Default password: admin123
Set your own with the ADMIN_PASSWORD environment variable. Press Ctrl+C to stop.

Photos save to ./uploads until S3_BUCKET is set (Phase 5).
Production (EC2): gunicorn -w 2 -b 0.0.0.0:8000 app:app
