#!/usr/bin/env python3
"""
Advanced script to query squidgy_facebook_pages table with various filtering options.
"""

import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
import json
from typing import Optional, List, Dict, Any

# Load environment variables
load_dotenv()

class FacebookPagesChecker:
    def __init__(self):
        """Initialize the checker with Supabase client"""
        self.client = self._get_supabase_client()
    
    def _get_supabase_client(self) -> Client:
        """Create and return a Supabase client using credentials from .env"""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        
        return create_client(supabase_url, supabase_key)
    
    def get_records_by_date_range(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch records within a date range"""
        query = self.client.table('squidgy_facebook_pages').select('*')
        
        if start_date:
            query = query.gte('created_at', start_date.isoformat())
        
        if end_date:
            query = query.lte('created_at', end_date.isoformat())
        
        try:
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"Error fetching records: {e}")
            return []
    
    def get_records_by_location(self, location_id: str) -> List[Dict[str, Any]]:
        """Fetch records for a specific location"""
        try:
            response = self.client.table('squidgy_facebook_pages')\
                .select('*')\
                .eq('location_id', location_id)\
                .execute()
            return response.data
        except Exception as e:
            print(f"Error fetching records: {e}")
            return []
    
    def get_records_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Fetch records for a specific user"""
        try:
            response = self.client.table('squidgy_facebook_pages')\
                .select('*')\
                .eq('user_id', user_id)\
                .execute()
            return response.data
        except Exception as e:
            print(f"Error fetching records: {e}")
            return []
    
    def get_connected_pages(self) -> List[Dict[str, Any]]:
        """Fetch only pages that are connected to GHL"""
        try:
            response = self.client.table('squidgy_facebook_pages')\
                .select('*')\
                .eq('is_connected_to_ghl', True)\
                .execute()
            return response.data
        except Exception as e:
            print(f"Error fetching records: {e}")
            return []
    
    def get_instagram_enabled_pages(self) -> List[Dict[str, Any]]:
        """Fetch only pages with Instagram available"""
        try:
            response = self.client.table('squidgy_facebook_pages')\
                .select('*')\
                .eq('is_instagram_available', True)\
                .execute()
            return response.data
        except Exception as e:
            print(f"Error fetching records: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the Facebook pages"""
        try:
            # Get all records
            response = self.client.table('squidgy_facebook_pages').select('*').execute()
            records = response.data
            
            if not records:
                return {"total": 0}
            
            # Calculate statistics
            stats = {
                "total": len(records),
                "connected_to_ghl": sum(1 for r in records if r.get('is_connected_to_ghl')),
                "instagram_available": sum(1 for r in records if r.get('is_instagram_available')),
                "unique_locations": len(set(r.get('location_id') for r in records)),
                "unique_users": len(set(r.get('user_id') for r in records)),
                "unique_pages": len(set(r.get('page_id') for r in records)),
                "by_category": {}
            }
            
            # Count by category
            for record in records:
                category = record.get('page_category', 'Unknown')
                stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            return stats
        except Exception as e:
            print(f"Error calculating statistics: {e}")
            return {"error": str(e)}

def display_records(records: List[Dict[str, Any]], verbose: bool = False):
    """Display records in a formatted way"""
    if not records:
        print("\nNo records found.")
        return
    
    print(f"\nFound {len(records)} record(s):\n")
    print("-" * 80)
    
    for idx, record in enumerate(records, 1):
        print(f"\nRecord #{idx}:")
        print(f"  Page Name: {record.get('page_name')}")
        print(f"  Page ID: {record.get('page_id')}")
        print(f"  Location ID: {record.get('location_id')}")
        print(f"  Connected to GHL: {'Yes' if record.get('is_connected_to_ghl') else 'No'}")
        print(f"  Instagram Available: {'Yes' if record.get('is_instagram_available') else 'No'}")
        print(f"  Created: {record.get('created_at')}")
        
        if verbose:
            print(f"  ID: {record.get('id')}")
            print(f"  Firm User ID: {record.get('firm_user_id')}")
            print(f"  User ID: {record.get('user_id')}")
            print(f"  Page Category: {record.get('page_category', 'N/A')}")
            print(f"  Updated At: {record.get('updated_at')}")
            
            if record.get('connected_at'):
                print(f"  Connected At: {record.get('connected_at')}")
            
            if record.get('instagram_business_account_id'):
                print(f"  Instagram Business Account ID: {record.get('instagram_business_account_id')}")
        
        print("-" * 80)

def display_statistics(stats: Dict[str, Any]):
    """Display statistics in a formatted way"""
    print("\nFacebook Pages Statistics:")
    print("-" * 40)
    print(f"Total Pages: {stats.get('total', 0)}")
    print(f"Connected to GHL: {stats.get('connected_to_ghl', 0)}")
    print(f"Instagram Available: {stats.get('instagram_available', 0)}")
    print(f"Unique Locations: {stats.get('unique_locations', 0)}")
    print(f"Unique Users: {stats.get('unique_users', 0)}")
    print(f"Unique Pages: {stats.get('unique_pages', 0)}")
    
    if stats.get('by_category'):
        print("\nPages by Category:")
        for category, count in sorted(stats['by_category'].items()):
            print(f"  {category}: {count}")

def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(description='Check Facebook pages in Supabase database')
    parser.add_argument('--today', action='store_true', help='Show only today\'s records')
    parser.add_argument('--yesterday', action='store_true', help='Show only yesterday\'s records')
    parser.add_argument('--days', type=int, help='Show records from last N days')
    parser.add_argument('--location', type=str, help='Filter by location ID')
    parser.add_argument('--user', type=str, help='Filter by user ID')
    parser.add_argument('--connected', action='store_true', help='Show only GHL-connected pages')
    parser.add_argument('--instagram', action='store_true', help='Show only Instagram-enabled pages')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed information')
    parser.add_argument('--save', type=str, help='Save results to JSON file')
    
    args = parser.parse_args()
    
    print("Connecting to Supabase database...")
    
    try:
        checker = FacebookPagesChecker()
        print("Successfully connected to Supabase!")
        
        records = []
        
        # Handle different query options
        if args.stats:
            stats = checker.get_statistics()
            display_statistics(stats)
            return 0
        
        if args.today:
            start_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            records = checker.get_records_by_date_range(start_date=start_date)
            print(f"\nChecking for records created today ({start_date.date()})...")
        
        elif args.yesterday:
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            start_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            records = checker.get_records_by_date_range(start_date=start_date, end_date=end_date)
            print(f"\nChecking for records created yesterday ({start_date.date()})...")
        
        elif args.days:
            start_date = datetime.now(timezone.utc) - timedelta(days=args.days)
            records = checker.get_records_by_date_range(start_date=start_date)
            print(f"\nChecking for records from last {args.days} days...")
        
        elif args.location:
            records = checker.get_records_by_location(args.location)
            print(f"\nChecking for records with location ID: {args.location}")
        
        elif args.user:
            records = checker.get_records_by_user(args.user)
            print(f"\nChecking for records with user ID: {args.user}")
        
        elif args.connected:
            records = checker.get_connected_pages()
            print("\nChecking for GHL-connected pages...")
        
        elif args.instagram:
            records = checker.get_instagram_enabled_pages()
            print("\nChecking for Instagram-enabled pages...")
        
        else:
            # Default: show today's records
            start_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            records = checker.get_records_by_date_range(start_date=start_date)
            print(f"\nChecking for records created today ({start_date.date()})...")
        
        # Display results
        display_records(records, verbose=args.verbose)
        
        # Save to file if requested
        if args.save and records:
            with open(args.save, 'w') as f:
                json.dump(records, f, indent=2, default=str)
            print(f"\nRecords saved to: {args.save}")
        
    except Exception as e:
        print(f"\nError: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())