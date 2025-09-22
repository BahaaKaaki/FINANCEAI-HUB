"""
Check ingestion history and current database state.
"""

from app.database.connection import get_db_session
from app.database.models import DataIngestionLogDB, FinancialRecordDB
from sqlalchemy import desc, func

def main():
    with get_db_session() as session:
        # Check ingestion logs
        logs = session.query(DataIngestionLogDB).order_by(desc(DataIngestionLogDB.started_at)).limit(10).all()
        
        print('Recent ingestion history:')
        print('=' * 80)
        
        if logs:
            for log in logs:
                print(f'Source: {log.source}')
                print(f'File: {log.filename or "N/A"}')
                print(f'Status: {log.status}')
                print(f'Records: {log.records_processed} processed, {log.records_created} created')
                print(f'Started: {log.started_at}')
                if log.completed_at:
                    print(f'Duration: {log.processing_duration_seconds}s')
                if log.error_message:
                    print(f'Error: {log.error_message}')
                print('-' * 40)
        else:
            print('No ingestion history found.')
        
        # Check current data by source
        print('\nCurrent data breakdown by source:')
        print('=' * 50)
        
        source_stats = session.query(
            FinancialRecordDB.source,
            func.count(FinancialRecordDB.id).label('record_count'),
            func.min(FinancialRecordDB.period_start).label('earliest_period'),
            func.max(FinancialRecordDB.period_end).label('latest_period')
        ).group_by(FinancialRecordDB.source).all()
        
        for stat in source_stats:
            print(f'Source: {stat.source}')
            print(f'Records: {stat.record_count}')
            print(f'Period range: {stat.earliest_period} to {stat.latest_period}')
            print('-' * 30)

if __name__ == "__main__":
    main()