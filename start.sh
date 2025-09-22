#!/bin/bash

# Render.com startup script
echo "Starting FinanceAI-Hub..."

# Initialize database if needed
python -c "
from app.database.connection import init_database
try:
    init_database()
    print('Database initialized successfully')
except Exception as e:
    print(f'Database initialization error: {e}')
"

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}