#!/usr/bin/env python3
"""
MCP CLI - Command Line Interface for MCP Management
Easily manage external MCPs using configuration files
"""

import asyncio
import sys
import argparse
import json
from pathlib import Path
from pprint import pprint

# Add current directory to path
sys.path.append('.')

async def main():
    parser = argparse.ArgumentParser(description='MCP Configuration Management CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available MCPs')
    list_parser.add_argument('--category', choices=['official', 'community', 'all'], 
                           default='all', help='Filter by category')
    list_parser.add_argument('--enabled-only', action='store_true', 
                           help='Show only enabled MCPs')
    
    # Load command
    load_parser = subparsers.add_parser('load', help='Load MCPs from config files')
    load_parser.add_argument('--config', choices=['official', 'community', 'all'], 
                           default='all', help='Which config to load')
    load_parser.add_argument('--dry-run', action='store_true', 
                           help='Show what would be loaded without actually loading')
    
    # Enable command
    enable_parser = subparsers.add_parser('enable', help='Enable a specific MCP')
    enable_parser.add_argument('name', help='MCP name to enable')
    enable_parser.add_argument('--config', help='Specific config file to modify')
    
    # Disable command
    disable_parser = subparsers.add_parser('disable', help='Disable a specific MCP')
    disable_parser.add_argument('name', help='MCP name to disable')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show MCP system status')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add new MCP to config')
    add_parser.add_argument('url', help='GitHub URL of the MCP')
    add_parser.add_argument('name', help='Name for the MCP')
    add_parser.add_argument('--config', choices=['official', 'community'], 
                          default='community', help='Which config to add to')
    add_parser.add_argument('--description', help='Description of the MCP')
    add_parser.add_argument('--enabled', action='store_true', help='Enable immediately')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        # Import MCP components
        import sys
        import importlib
        
        # Import main first to initialize properly
        main_module = importlib.import_module('main')
        create_supabase_client = main_module.create_supabase_client
        
        # Import MCP config loader
        config_loader_module = importlib.import_module('mcp.config_loader')
        MCPConfigLoader = config_loader_module.MCPConfigLoader
        
        # Initialize components
        supabase = create_supabase_client()
        loader = MCPConfigLoader(supabase)
        
        if args.command == 'list':
            await cmd_list(loader, args)
        elif args.command == 'load':
            await cmd_load(loader, args)
        elif args.command == 'enable':
            await cmd_enable(loader, args)
        elif args.command == 'disable':
            await cmd_disable(loader, args)
        elif args.command == 'status':
            await cmd_status(loader, args)
        elif args.command == 'add':
            await cmd_add(loader, args)
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the project directory")
    except Exception as e:
        print(f"❌ Error: {e}")

async def cmd_list(loader: 'MCPConfigLoader', args):
    """List available MCPs"""
    print("📋 Available MCPs:")
    print("=" * 50)
    
    mcps = loader.list_available_mcps()
    
    for category, mcp_list in mcps.items():
        if args.category != 'all' and category != args.category:
            continue
            
        if not mcp_list:
            continue
            
        print(f"\n🏷️  {category.upper()} MCPs:")
        print("-" * 30)
        
        for mcp in mcp_list:
            if args.enabled_only and not mcp['enabled']:
                continue
                
            status = "✅ ENABLED" if mcp['enabled'] else "⏸️  DISABLED"
            print(f"{status} {mcp['name']}")
            print(f"   📝 {mcp['description']}")
            print(f"   🔗 {mcp['url']}")
            
            if mcp['env_required']:
                print(f"   🔐 Requires: {', '.join(mcp['env_required'])}")
                
            if mcp['tags']:
                print(f"   🏷️  Tags: {', '.join(mcp['tags'])}")
                
            print()

async def cmd_load(loader: 'MCPConfigLoader', args):
    """Load MCPs from configuration"""
    if args.dry_run:
        print("🧪 DRY RUN - Showing what would be loaded:")
        print("=" * 50)
        
        mcps = loader.list_available_mcps()
        for category, mcp_list in mcps.items():
            for mcp in mcp_list:
                if mcp['enabled']:
                    print(f"Would load: {mcp['name']} ({category})")
        return
    
    print("🔄 Loading MCPs from configuration...")
    print("=" * 50)
    
    if args.config in ['official', 'all']:
        print("Loading official MCPs...")
        await loader.load_config_file("external_config_official.json")
        
    if args.config in ['community', 'all']:
        print("Loading community MCPs...")
        await loader.load_config_file("external_config_github_public.json")
    
    print("✅ MCP loading completed!")

async def cmd_enable(loader: 'MCPConfigLoader', args):
    """Enable a specific MCP"""
    print(f"🔄 Enabling MCP: {args.name}")
    
    success = await loader.enable_mcp(args.name, args.config)
    
    if success:
        print(f"✅ Successfully enabled: {args.name}")
    else:
        print(f"❌ Failed to enable: {args.name}")

async def cmd_disable(loader: 'MCPConfigLoader', args):
    """Disable a specific MCP"""
    print(f"🔄 Disabling MCP: {args.name}")
    
    success = await loader.disable_mcp(args.name)
    
    if success:
        print(f"✅ Successfully disabled: {args.name}")
    else:
        print(f"❌ Failed to disable: {args.name}")

async def cmd_status(loader: 'MCPConfigLoader', args):
    """Show MCP system status"""
    print("📊 MCP System Status:")
    print("=" * 50)
    
    try:
        # Get database stats
        result = loader.supabase.table('mcps').select('trust_level, status, count(*)').execute()
        
        print("Database MCPs:")
        for row in result.data:
            print(f"  {row['trust_level']}: {row['count']} ({row['status']})")
        
        # Get recent activity
        activity = loader.supabase.table('mcp_audit_logs')\
            .select('*')\
            .order('timestamp', desc=True)\
            .limit(5)\
            .execute()
        
        if activity.data:
            print(f"\nRecent Activity:")
            for log in activity.data:
                print(f"  {log['timestamp']}: {log['action']} - {log['tool_name']}")
                
    except Exception as e:
        print(f"❌ Failed to get status: {e}")

async def cmd_add(loader: 'MCPConfigLoader', args):
    """Add new MCP to configuration"""
    print(f"➕ Adding MCP: {args.name}")
    
    config_file = f"external_config_{args.config}.json"
    config_path = Path(__file__).parent / "mcp" / "config" / config_file
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Create new MCP entry
        new_mcp = {
            "url": args.url,
            "name": args.name,
            "description": args.description or f"MCP server: {args.name}",
            "enabled": args.enabled,
            "auto_approve": args.config == 'official',
            "security_scan": args.config == 'community',
            "sandbox": args.config == 'community',
            "tags": ["custom", "added-via-cli"],
            "capabilities": []
        }
        
        if args.config == 'community':
            new_mcp["max_risk_score"] = 30
        
        # Add to config
        mcp_key = args.name.replace('-', '_').replace(' ', '_').lower()
        config['mcps'][mcp_key] = new_mcp
        
        # Save config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Added {args.name} to {config_file}")
        
        if args.enabled:
            await loader.enable_mcp(args.name)
            print(f"✅ Enabled {args.name}")
            
    except Exception as e:
        print(f"❌ Failed to add MCP: {e}")

if __name__ == "__main__":
    print("🚀 MCP Configuration CLI")
    print("=" * 50)
    asyncio.run(main())