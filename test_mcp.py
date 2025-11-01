#!/usr/bin/env python3
"""
Test script for MCP system functionality
Run this to test your MCP integration
"""

import asyncio
import sys
from pprint import pprint

# Add current directory to path
sys.path.append('.')

async def test_mcp_system():
    """Test MCP system initialization and tool discovery"""
    print("🧪 Testing MCP System...")
    print("=" * 50)
    
    try:
        # Test imports
        print("1️⃣ Testing imports...")
        from mcp.server import MCPGateway
        from mcp.config import config
        from main import create_supabase_client
        print("✅ All imports successful")
        
        # Test configuration
        print(f"\n2️⃣ Configuration:")
        print(f"   Environment: {config.environment}")
        print(f"   Sandbox enabled: {config.sandbox_enabled}")
        print(f"   Trust domains: {len(config.trust_official_domains)} domains")
        
        # Test Supabase connection
        print(f"\n3️⃣ Testing Supabase connection...")
        try:
            supabase = create_supabase_client()
            print("✅ Supabase client created")
        except Exception as e:
            print(f"❌ Supabase connection failed: {e}")
            print("   Make sure SUPABASE_URL and SUPABASE_SERVICE_KEY are set")
            return
        
        # Test MCP Gateway initialization
        print(f"\n4️⃣ Initializing MCP Gateway...")
        gateway = MCPGateway(supabase)
        await gateway.initialize()
        print("✅ MCP Gateway initialized")
        
        # Test tool discovery
        print(f"\n5️⃣ Discovering tools...")
        tools = gateway.registry.list_tools()
        mcps = gateway.registry.list_mcps()
        
        print(f"   Found {len(mcps)} MCPs")
        print(f"   Found {len(tools)} tools total")
        
        # List MCPs
        print(f"\n📦 Available MCPs:")
        for mcp in mcps:
            print(f"   • {mcp.name} ({mcp.trust_level.value}) - {mcp.status.value}")
        
        # List some tools
        print(f"\n🛠️ Available Tools (showing first 10):")
        for tool in tools[:10]:
            print(f"   • {tool.name} - {tool.description[:50]}...")
        
        if len(tools) > 10:
            print(f"   ... and {len(tools) - 10} more tools")
        
        # Test a simple tool call
        print(f"\n6️⃣ Testing tool calls...")
        
        # Try business tool
        try:
            result = await gateway.registry.call_tool("calculate_roi", {
                "investment": 10000,
                "return_amount": 12000,
                "time_period_months": 12
            })
            print("✅ calculate_roi test:")
            pprint(result)
        except Exception as e:
            print(f"❌ calculate_roi failed: {e}")
        
        print(f"\n🎉 MCP System Test Complete!")
        print(f"Your MCP server is ready to use with {len(tools)} tools available!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_tool_call_api():
    """Test the actual API endpoints"""
    print(f"\n🌐 Testing API Endpoints...")
    print("=" * 30)
    
    try:
        import httpx
        
        # Test health endpoint
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get("http://localhost:8000/api/v1/mcp/health")
                if response.status_code == 200:
                    print("✅ Health endpoint working")
                    pprint(response.json())
                else:
                    print(f"❌ Health endpoint returned {response.status_code}")
            except Exception as e:
                print(f"⚠️ Server not running or health endpoint failed: {e}")
                print("   Start your server with: python main.py")
                
    except ImportError:
        print("⚠️ httpx not installed - skipping API tests")
        print("   Install with: pip install httpx")

if __name__ == "__main__":
    print("🚀 MCP System Test Script")
    print("=" * 50)
    
    # Test MCP system
    asyncio.run(test_mcp_system())
    
    # Test API endpoints
    asyncio.run(test_tool_call_api())
    
    print(f"\n📚 Next Steps:")
    print("1. Start your server: python main.py")
    print("2. Test tools: curl http://localhost:8000/api/v1/mcp/tools")
    print("3. Call a tool: curl -X POST http://localhost:8000/api/v1/mcp/call \\")
    print('   -d \'{"tool": "calculate_roi", "params": {"investment": 1000, "return_amount": 1200}}\'')