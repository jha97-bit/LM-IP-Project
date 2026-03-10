#!/usr/bin/env python3
"""
Verification script for VFT database integration.
Shows latest run_id and counts rows in each VFT table.
"""

from persistence.engine import get_engine
from sqlalchemy import text

def verify_vft_integration():
    """Query and display VFT data in database."""
    try:
        engine = get_engine()
        
        with engine.begin() as conn:
            # Get latest VFT run
            result = conn.execute(text("""
                SELECT run_id::text, scenario_id::text, preference_set_id::text, 
                       executed_at, executed_by, method
                FROM runs
                WHERE method = 'vft'
                ORDER BY executed_at DESC
                LIMIT 1
            """)).mappings().first()
            
            if not result:
                print("❌ No VFT runs found in database")
                return
            
            run_id = result['run_id']
            print(f"\n✓ Latest VFT Run: {run_id}")
            print(f"  Scenario ID: {result['scenario_id']}")
            print(f"  Preference Set ID: {result['preference_set_id']}")
            print(f"  Executed by: {result['executed_by']}")
            print(f"  Executed at: {result['executed_at']}")
            
            # Count rows in each table
            tables = [
                'vft_run_config',
                'vft_criterion_utilities',
                'vft_weighted_utilities',
                'result_scores'
            ]
            
            print("\n📊 Rows persisted for this run:")
            for table in tables:
                count_result = conn.execute(text(f"""
                    SELECT COUNT(*) as cnt FROM {table}
                    WHERE run_id = :run_id
                """), {"run_id": run_id}).mappings().first()
                count = count_result['cnt']
                print(f"  {table}: {count} rows")
            
            # Show sample data
            print("\n📋 Sample Data:")
            
            config = conn.execute(text("""
                SELECT * FROM vft_run_config WHERE run_id = :run_id
            """), {"run_id": run_id}).mappings().first()
            if config:
                print(f"\n  vft_run_config:")
                print(f"    scaling_type: {config.get('scaling_type', 'N/A')}")
            
            utilities = conn.execute(text("""
                SELECT * FROM vft_criterion_utilities
                WHERE run_id = :run_id
                LIMIT 1
            """), {"run_id": run_id}).mappings().first()
            if utilities:
                print(f"\n  vft_criterion_utilities (first row):")
                for key, val in utilities.items():
                    if key != 'run_id':
                        print(f"    {key}: {val}")
            
            print("\n✓ VFT database integration verified!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_vft_integration()
