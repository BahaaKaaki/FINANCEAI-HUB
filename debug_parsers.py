#!/usr/bin/env python3
"""
Debug script for testing QuickBooks and Rootfi parsers.

This script provides detailed debugging information about the parsing process,
including intermediate steps, data structures, and validation results.
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('parser_debug.log')
    ]
)

logger = logging.getLogger(__name__)

def debug_quickbooks_parser():
    """Debug QuickBooks parser with detailed logging."""
    print("=" * 80)
    print("🔍 DEBUGGING QUICKBOOKS PARSER")
    print("=" * 80)
    
    try:
        from app.parsers.quickbooks_parser import QuickBooksParser, parse_quickbooks_file
        
        # Check if QuickBooks data file exists
        qb_file = "data_set_1.json"
        try:
            with open(qb_file, 'r') as f:
                qb_data = json.load(f)
            print(f"✅ Successfully loaded QuickBooks file: {qb_file}")
            print(f"📊 File size: {len(json.dumps(qb_data))} characters")
        except FileNotFoundError:
            print(f"❌ QuickBooks file not found: {qb_file}")
            return
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in QuickBooks file: {e}")
            return
        
        # Initialize parser with debug logging
        parser = QuickBooksParser()
        print(f"🔧 Initialized QuickBooks parser")
        
        # Parse data with detailed debugging
        print("\n📋 PARSING QUICKBOOKS DATA...")
        financial_records, accounts, account_values = parser.parse_data(qb_data)
        
        # Display parsing results
        print(f"\n📈 QUICKBOOKS PARSING RESULTS:")
        print(f"   Financial Records: {len(financial_records)}")
        print(f"   Accounts: {len(accounts)}")
        print(f"   Account Values: {len(account_values)}")
        
        # Show sample data
        if financial_records:
            print(f"\n💰 SAMPLE FINANCIAL RECORD:")
            record = financial_records[0]
            print(f"   Source: {record.source}")
            print(f"   Period: {record.period_start} to {record.period_end}")
            print(f"   Currency: {record.currency}")
            print(f"   Revenue: ${record.revenue:,.2f}")
            print(f"   Expenses: ${record.expenses:,.2f}")
            print(f"   Net Profit: ${record.net_profit:,.2f}")
            
        if accounts:
            print(f"\n🏦 SAMPLE ACCOUNTS (first 5):")
            for i, account in enumerate(accounts[:5]):
                print(f"   {i+1}. {account.name} ({account.account_type}) - ID: {account.account_id}")
                if account.parent_account_id:
                    print(f"      Parent: {account.parent_account_id}")
        
        if account_values:
            print(f"\n💵 SAMPLE ACCOUNT VALUES (first 5):")
            for i, av in enumerate(account_values[:5]):
                print(f"   {i+1}. Account {av.account_id}: ${av.value:,.2f}")
        
        # Validate data consistency
        print(f"\n✅ DATA VALIDATION:")
        validate_parser_output(financial_records, accounts, account_values, "QuickBooks")
        
    except Exception as e:
        print(f"❌ Error debugging QuickBooks parser: {e}")
        logger.exception("QuickBooks parser debug error")


def debug_rootfi_parser():
    """Debug Rootfi parser with detailed logging."""
    print("\n" + "=" * 80)
    print("🔍 DEBUGGING ROOTFI PARSER")
    print("=" * 80)
    
    try:
        from app.parsers.rootfi_parser import RootfiParser, parse_rootfi_file
        
        # Check if Rootfi data file exists
        rootfi_file = "data_set_2.json"
        try:
            with open(rootfi_file, 'r') as f:
                rootfi_data = json.load(f)
            print(f"✅ Successfully loaded Rootfi file: {rootfi_file}")
            print(f"📊 File size: {len(json.dumps(rootfi_data))} characters")
            print(f"📊 Number of periods: {len(rootfi_data.get('data', []))}")
        except FileNotFoundError:
            print(f"❌ Rootfi file not found: {rootfi_file}")
            return
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in Rootfi file: {e}")
            return
        
        # Initialize parser with debug logging
        parser = RootfiParser()
        print(f"🔧 Initialized Rootfi parser")
        
        # Show sample data structure
        if rootfi_data.get('data') and len(rootfi_data['data']) > 0:
            sample_record = rootfi_data['data'][0]
            print(f"\n📋 SAMPLE ROOTFI RECORD STRUCTURE:")
            print(f"   Rootfi ID: {sample_record.get('rootfi_id')}")
            print(f"   Period: {sample_record.get('period_start')} to {sample_record.get('period_end')}")
            print(f"   Currency: {sample_record.get('currency_id')}")
            print(f"   Revenue categories: {len(sample_record.get('revenue', []))}")
            print(f"   Operating expense categories: {len(sample_record.get('operating_expenses', []))}")
            print(f"   Gross profit: {sample_record.get('gross_profit')}")
            print(f"   Net profit: {sample_record.get('net_profit')}")
        
        # Parse data with detailed debugging
        print(f"\n📋 PARSING ROOTFI DATA...")
        financial_records, accounts, account_values = parser.parse_data(rootfi_data)
        
        # Display parsing results
        print(f"\n📈 ROOTFI PARSING RESULTS:")
        print(f"   Financial Records: {len(financial_records)}")
        print(f"   Accounts: {len(accounts)}")
        print(f"   Account Values: {len(account_values)}")
        
        # Show sample data
        if financial_records:
            print(f"\n💰 SAMPLE FINANCIAL RECORD:")
            record = financial_records[0]
            print(f"   Source: {record.source}")
            print(f"   Period: {record.period_start} to {record.period_end}")
            print(f"   Currency: {record.currency}")
            print(f"   Revenue: ${record.revenue:,.2f}")
            print(f"   Expenses: ${record.expenses:,.2f}")
            print(f"   Net Profit: ${record.net_profit:,.2f}")
            print(f"   Raw Data Keys: {list(record.raw_data.keys()) if record.raw_data else 'None'}")
            
        if accounts:
            print(f"\n🏦 SAMPLE ACCOUNTS (first 5):")
            for i, account in enumerate(accounts[:5]):
                print(f"   {i+1}. {account.name} ({account.account_type}) - ID: {account.account_id}")
                if account.parent_account_id:
                    print(f"      Parent: {account.parent_account_id}")
        
        if account_values:
            print(f"\n💵 SAMPLE ACCOUNT VALUES (first 5):")
            for i, av in enumerate(account_values[:5]):
                print(f"   {i+1}. Account {av.account_id}: ${av.value:,.2f}")
        
        # Show account hierarchy
        print(f"\n🌳 ACCOUNT HIERARCHY ANALYSIS:")
        analyze_account_hierarchy(accounts)
        
        # Validate data consistency
        print(f"\n✅ DATA VALIDATION:")
        validate_parser_output(financial_records, accounts, account_values, "Rootfi")
        
    except Exception as e:
        print(f"❌ Error debugging Rootfi parser: {e}")
        logger.exception("Rootfi parser debug error")


def analyze_account_hierarchy(accounts):
    """Analyze and display account hierarchy structure."""
    # Group accounts by parent
    hierarchy = {}
    root_accounts = []
    
    for account in accounts:
        if account.parent_account_id is None:
            root_accounts.append(account)
        else:
            if account.parent_account_id not in hierarchy:
                hierarchy[account.parent_account_id] = []
            hierarchy[account.parent_account_id].append(account)
    
    print(f"   Root accounts: {len(root_accounts)}")
    print(f"   Accounts with children: {len(hierarchy)}")
    
    # Show hierarchy depth
    max_depth = 0
    for root in root_accounts:
        depth = calculate_hierarchy_depth(root.account_id, hierarchy, 0)
        max_depth = max(max_depth, depth)
    
    print(f"   Maximum hierarchy depth: {max_depth}")
    
    # Show sample hierarchy
    if root_accounts:
        print(f"   Sample hierarchy:")
        display_hierarchy(root_accounts[0], hierarchy, "      ", 0)


def calculate_hierarchy_depth(account_id: str, hierarchy: Dict, current_depth: int) -> int:
    """Calculate the maximum depth of account hierarchy."""
    if account_id not in hierarchy:
        return current_depth
    
    max_child_depth = current_depth
    for child in hierarchy[account_id]:
        child_depth = calculate_hierarchy_depth(child.account_id, hierarchy, current_depth + 1)
        max_child_depth = max(max_child_depth, child_depth)
    
    return max_child_depth


def display_hierarchy(account, hierarchy: Dict, indent: str, level: int):
    """Display account hierarchy tree."""
    if level > 3:  # Limit display depth
        return
        
    print(f"{indent}├─ {account.name} ({account.account_type})")
    
    if account.account_id in hierarchy:
        for child in hierarchy[account.account_id][:2]:  # Limit to 2 children per level
            display_hierarchy(child, hierarchy, indent + "   ", level + 1)
        
        if len(hierarchy[account.account_id]) > 2:
            print(f"{indent}   └─ ... and {len(hierarchy[account.account_id]) - 2} more")


def validate_parser_output(financial_records, accounts, account_values, parser_name: str):
    """Validate parser output for consistency and correctness."""
    validation_results = []
    
    # Check if we have data
    if not financial_records:
        validation_results.append("❌ No financial records generated")
    else:
        validation_results.append(f"✅ Generated {len(financial_records)} financial records")
    
    if not accounts:
        validation_results.append("❌ No accounts extracted")
    else:
        validation_results.append(f"✅ Extracted {len(accounts)} accounts")
    
    if not account_values:
        validation_results.append("❌ No account values generated")
    else:
        validation_results.append(f"✅ Generated {len(account_values)} account values")
    
    # Validate financial record consistency
    if financial_records:
        for i, record in enumerate(financial_records[:3]):  # Check first 3 records
            try:
                # Check net profit calculation
                expected_profit = record.revenue - record.expenses
                if abs(record.net_profit - expected_profit) > Decimal('0.01'):
                    validation_results.append(f"❌ Record {i+1}: Net profit calculation error")
                else:
                    validation_results.append(f"✅ Record {i+1}: Net profit calculation correct")
                
                # Check date consistency
                if record.period_end <= record.period_start:
                    validation_results.append(f"❌ Record {i+1}: Invalid date range")
                else:
                    validation_results.append(f"✅ Record {i+1}: Valid date range")
                    
            except Exception as e:
                validation_results.append(f"❌ Record {i+1}: Validation error - {e}")
    
    # Validate account relationships
    if accounts:
        account_ids = {acc.account_id for acc in accounts}
        orphaned_accounts = 0
        
        for account in accounts:
            if account.parent_account_id and account.parent_account_id not in account_ids:
                orphaned_accounts += 1
        
        if orphaned_accounts > 0:
            validation_results.append(f"❌ {orphaned_accounts} accounts have invalid parent references")
        else:
            validation_results.append("✅ All account parent references are valid")
    
    # Validate account values
    if account_values and accounts and financial_records:
        record_ids = {f"qb_{rec.period_start.strftime('%Y%m%d')}_{rec.period_end.strftime('%Y%m%d')}" if parser_name == "QuickBooks" 
                     else f"rootfi_{rec.period_start.strftime('%Y%m%d')}_{rec.period_end.strftime('%Y%m%d')}" 
                     for rec in financial_records}
        
        invalid_references = 0
        for av in account_values[:10]:  # Check first 10
            if av.account_id not in account_ids:
                invalid_references += 1
        
        if invalid_references > 0:
            validation_results.append(f"❌ {invalid_references} account values have invalid account references")
        else:
            validation_results.append("✅ Account value references are valid")
    
    # Print validation results
    for result in validation_results:
        print(f"   {result}")


def compare_parsers():
    """Compare output from both parsers."""
    print("\n" + "=" * 80)
    print("🔄 COMPARING PARSER OUTPUTS")
    print("=" * 80)
    
    try:
        from app.parsers.quickbooks_parser import parse_quickbooks_file
        from app.parsers.rootfi_parser import parse_rootfi_file
        
        # Parse both files
        qb_records, qb_accounts, qb_values = [], [], []
        rootfi_records, rootfi_accounts, rootfi_values = [], [], []
        
        try:
            qb_records, qb_accounts, qb_values = parse_quickbooks_file("data_set_1.json")
            print("✅ QuickBooks parsing successful")
        except Exception as e:
            print(f"❌ QuickBooks parsing failed: {e}")
        
        try:
            rootfi_records, rootfi_accounts, rootfi_values = parse_rootfi_file("data_set_2.json")
            print("✅ Rootfi parsing successful")
        except Exception as e:
            print(f"❌ Rootfi parsing failed: {e}")
        
        # Compare results
        print(f"\n📊 COMPARISON SUMMARY:")
        print(f"   QuickBooks: {len(qb_records)} records, {len(qb_accounts)} accounts, {len(qb_values)} values")
        print(f"   Rootfi:     {len(rootfi_records)} records, {len(rootfi_accounts)} accounts, {len(rootfi_values)} values")
        
        # Compare data structures
        if qb_records and rootfi_records:
            print(f"\n🔍 DATA STRUCTURE COMPARISON:")
            qb_record = qb_records[0]
            rootfi_record = rootfi_records[0]
            
            print(f"   QuickBooks record fields: {list(qb_record.__dict__.keys())}")
            print(f"   Rootfi record fields:     {list(rootfi_record.__dict__.keys())}")
            
            # Check field compatibility
            qb_fields = set(qb_record.__dict__.keys())
            rootfi_fields = set(rootfi_record.__dict__.keys())
            common_fields = qb_fields.intersection(rootfi_fields)
            
            print(f"   Common fields: {len(common_fields)}/{len(qb_fields.union(rootfi_fields))}")
            print(f"   Compatible: {'✅' if len(common_fields) >= 6 else '❌'}")
        
    except Exception as e:
        print(f"❌ Error comparing parsers: {e}")
        logger.exception("Parser comparison error")


def main():
    """Main debug function."""
    print("🚀 FINANCIAL DATA PARSER DEBUGGING TOOL")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Debug individual parsers
    debug_quickbooks_parser()
    debug_rootfi_parser()
    
    # Compare parsers
    compare_parsers()
    
    print("\n" + "=" * 80)
    print("✅ DEBUGGING COMPLETE")
    print("📄 Detailed logs saved to: parser_debug.log")
    print("=" * 80)


if __name__ == "__main__":
    main()