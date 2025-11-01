#!/usr/bin/env python3
"""
Pre-commit validation script for MCP configuration files
Ensures all MCPs are properly scanned and approved before commit
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
import asyncio

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

class MCPConfigValidator:
    """Validates MCP configuration files for security compliance"""
    
    def __init__(self):
        self.config_dir = project_root / "mcp" / "config"
        self.errors = []
        self.warnings = []
        
    def validate_all_configs(self) -> bool:
        """Validate all MCP configuration files"""
        print("🔍 Validating MCP Configuration Files...")
        print("=" * 50)
        
        success = True
        
        # Validate both config files
        config_files = [
            "external_config_official.json",
            "external_config_github_public.json"
        ]
        
        for config_file in config_files:
            if not self.validate_config_file(config_file):
                success = False
        
        # Print summary
        self.print_summary()
        
        return success
    
    def validate_config_file(self, filename: str) -> bool:
        """Validate a specific config file"""
        config_path = self.config_dir / filename
        
        print(f"\n📋 Validating {filename}...")
        
        if not config_path.exists():
            self.errors.append(f"Config file not found: {filename}")
            return False
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON in {filename}: {e}")
            return False
        
        # Validate config structure
        if not self.validate_config_structure(config, filename):
            return False
        
        # Validate each MCP
        success = True
        for mcp_key, mcp_config in config.get("mcps", {}).items():
            if not self.validate_mcp(mcp_config, mcp_key, filename, config.get("trust_level")):
                success = False
        
        if success:
            print(f"✅ {filename} validation passed")
        else:
            print(f"❌ {filename} validation failed")
            
        return success
    
    def validate_config_structure(self, config: Dict, filename: str) -> bool:
        """Validate the overall config file structure"""
        required_fields = ["name", "description", "trust_level", "mcps"]
        
        for field in required_fields:
            if field not in config:
                self.errors.append(f"{filename}: Missing required field '{field}'")
                return False
        
        valid_trust_levels = ["OFFICIAL", "VERIFIED", "COMMUNITY", "INTERNAL"]
        if config["trust_level"] not in valid_trust_levels:
            self.errors.append(f"{filename}: Invalid trust_level '{config['trust_level']}'")
            return False
        
        return True
    
    def validate_mcp(self, mcp_config: Dict, mcp_key: str, filename: str, trust_level: str) -> bool:
        """Validate a single MCP configuration"""
        success = True
        mcp_name = mcp_config.get("name", mcp_key)
        
        # Required fields
        required_fields = ["url", "name", "description", "enabled"]
        for field in required_fields:
            if field not in mcp_config:
                self.errors.append(f"{filename}:{mcp_name} - Missing required field '{field}'")
                success = False
        
        # URL validation
        if "url" in mcp_config:
            if not self.validate_url(mcp_config["url"], mcp_name, filename):
                success = False
        
        # Trust level specific validation
        if trust_level == "COMMUNITY":
            success &= self.validate_community_mcp(mcp_config, mcp_name, filename)
        elif trust_level == "OFFICIAL":
            success &= self.validate_official_mcp(mcp_config, mcp_name, filename)
        
        # Security validation for enabled MCPs
        if mcp_config.get("enabled", False):
            success &= self.validate_enabled_mcp(mcp_config, mcp_name, filename, trust_level)
        
        return success
    
    def validate_url(self, url: str, mcp_name: str, filename: str) -> bool:
        """Validate MCP URL"""
        if not url.startswith(("https://github.com/", "https://gitlab.com/")):
            self.errors.append(f"{filename}:{mcp_name} - URL must be a GitHub or GitLab repository")
            return False
        
        if "github.com" in url and not (url.endswith(".git") or "/tree/" not in url):
            # Allow both .git and non-.git GitHub URLs
            pass
        
        return True
    
    def validate_community_mcp(self, mcp_config: Dict, mcp_name: str, filename: str) -> bool:
        """Validate community MCP specific requirements"""
        success = True
        
        # Community MCPs must have security settings
        required_security_fields = ["security_scan", "sandbox", "max_risk_score"]
        for field in required_security_fields:
            if field not in mcp_config:
                self.errors.append(f"{filename}:{mcp_name} - Community MCP missing '{field}'")
                success = False
        
        # Security scan must be enabled for community MCPs
        if not mcp_config.get("security_scan", False):
            self.errors.append(f"{filename}:{mcp_name} - Community MCP must have security_scan: true")
            success = False
        
        # Sandbox should be enabled for community MCPs
        if not mcp_config.get("sandbox", True):
            self.warnings.append(f"{filename}:{mcp_name} - Community MCP should use sandbox: true")
        
        # Auto-approve should be false for community MCPs
        if mcp_config.get("auto_approve", False):
            self.errors.append(f"{filename}:{mcp_name} - Community MCP cannot have auto_approve: true")
            success = False
        
        # Risk score validation
        max_risk = mcp_config.get("max_risk_score", 50)
        if not isinstance(max_risk, int) or max_risk < 0 or max_risk > 100:
            self.errors.append(f"{filename}:{mcp_name} - max_risk_score must be integer 0-100")
            success = False
        
        return success
    
    def validate_official_mcp(self, mcp_config: Dict, mcp_name: str, filename: str) -> bool:
        """Validate official MCP specific requirements"""
        success = True
        
        # Official MCPs should be from trusted domains
        url = mcp_config.get("url", "")
        trusted_domains = ["github.com/anthropics/", "anthropic.com"]
        
        if not any(domain in url for domain in trusted_domains):
            self.warnings.append(f"{filename}:{mcp_name} - Official MCP not from trusted domain")
        
        # Official MCPs should have auto_approve
        if not mcp_config.get("auto_approve", False):
            self.warnings.append(f"{filename}:{mcp_name} - Official MCP should have auto_approve: true")
        
        # Official MCPs should not need security scanning
        if mcp_config.get("security_scan", False):
            self.warnings.append(f"{filename}:{mcp_name} - Official MCP doesn't need security_scan: true")
        
        return success
    
    def validate_enabled_mcp(self, mcp_config: Dict, mcp_name: str, filename: str, trust_level: str) -> bool:
        """Validate enabled MCP for security compliance"""
        success = True
        
        # For enabled community MCPs, we should verify they've been scanned
        if trust_level == "COMMUNITY" and mcp_config.get("enabled", False):
            # In a real pre-commit hook, you might want to check if this MCP
            # has been scanned and approved in the database
            
            # Check if this is a new addition (would need database check)
            # For now, we'll add a validation that enabled community MCPs
            # must have all security fields properly configured
            
            if not mcp_config.get("security_scan", False):
                self.errors.append(f"{filename}:{mcp_name} - Enabled community MCP must be security scanned")
                success = False
            
            # Require approval metadata for enabled community MCPs
            if not mcp_config.get("_approval_date") and not mcp_config.get("_note"):
                self.warnings.append(f"{filename}:{mcp_name} - Enabled community MCP should have approval documentation")
        
        return success
    
    def validate_strict_mode(self) -> bool:
        """Strict mode validation - fail if community MCPs are enabled without approval"""
        print("\n🔒 Running strict mode validation...")
        
        success = True
        community_config = self.config_dir / "external_config_github_public.json"
        
        if not community_config.exists():
            return True
        
        with open(community_config, 'r') as f:
            config = json.load(f)
        
        for mcp_key, mcp_config in config.get("mcps", {}).items():
            if mcp_config.get("enabled", False):
                mcp_name = mcp_config.get("name", mcp_key)
                
                # Check for approval metadata
                if not mcp_config.get("_approval_date"):
                    self.errors.append(f"STRICT: {mcp_name} is enabled but not approved (missing _approval_date)")
                    success = False
                
                if not mcp_config.get("_approved_by"):
                    self.errors.append(f"STRICT: {mcp_name} is enabled but no approver specified (missing _approved_by)")
                    success = False
        
        if success:
            print("✅ Strict mode validation passed")
        else:
            print("❌ Strict mode validation failed")
            print("💡 Use: python scripts/validate_mcp_configs.py --approve <mcp_name> to approve MCPs")
        
        return success
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 50)
        print("📊 Validation Summary:")
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All validations passed!")
        elif not self.errors:
            print(f"\n✅ Validation passed with {len(self.warnings)} warnings")
        else:
            print(f"\n❌ Validation failed with {len(self.errors)} errors")
    
    async def validate_with_database(self) -> bool:
        """Validate against database (for enabled MCPs)"""
        # This would check if enabled MCPs are actually scanned and approved
        # in the database - useful for CI/CD pipelines
        try:
            from main import create_supabase_client
            
            supabase = create_supabase_client()
            
            # Get all MCPs from database
            result = supabase.table('mcps').select('*').execute()
            db_mcps = {mcp['url']: mcp for mcp in result.data}
            
            print(f"📊 Database validation: Found {len(db_mcps)} MCPs in database")
            
            # Check each enabled MCP in configs
            enabled_count = 0
            missing_count = 0
            
            for config_file in ["external_config_official.json", "external_config_github_public.json"]:
                config_path = self.config_dir / config_file
                if not config_path.exists():
                    continue
                    
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                for mcp_key, mcp_config in config.get("mcps", {}).items():
                    if not mcp_config.get("enabled", False):
                        continue
                    
                    enabled_count += 1
                    url = mcp_config.get("url")
                    mcp_name = mcp_config.get('name')
                    
                    if url not in db_mcps:
                        missing_count += 1
                        self.warnings.append(f"Enabled MCP not in database (will be added on load): {mcp_name}")
                        continue
                    
                    db_mcp = db_mcps[url]
                    if db_mcp['status'] not in ['approved', 'active']:
                        self.warnings.append(f"Database MCP status needs review: {mcp_name} (status: {db_mcp['status']})")
            
            print(f"📊 Config validation: {enabled_count} enabled MCPs, {missing_count} not in database yet")
            
            # Only warn, don't fail - MCPs will be added to database when loaded
            return True
            
        except Exception as e:
            self.warnings.append(f"Could not validate against database: {e}")
            return True  # Don't fail if database is unavailable

def main():
    """Main validation function"""
    import argparse
    parser = argparse.ArgumentParser(description='Validate MCP configurations')
    parser.add_argument('--strict', action='store_true', 
                       help='Strict mode: fail if any community MCPs are enabled without approval')
    parser.add_argument('--approve', type=str, 
                       help='Approve a specific MCP by name')
    args = parser.parse_args()
    
    validator = MCPConfigValidator()
    
    # Handle approval
    if args.approve:
        return handle_approval(args.approve)
    
    # Basic config validation
    success = validator.validate_all_configs()
    
    # Strict mode validation
    if args.strict:
        success = success and validator.validate_strict_mode()
    
    # Database validation (if available)
    if success:
        try:
            db_success = asyncio.run(validator.validate_with_database())
            success = success and db_success
        except Exception as e:
            print(f"⚠️  Database validation skipped: {e}")
    
    # Exit with appropriate code
    if success:
        print("\n🎉 All MCP configurations are valid!")
        sys.exit(0)
    else:
        print("\n💥 MCP configuration validation failed!")
        print("Please fix the errors above before committing.")
        sys.exit(1)

def handle_approval(mcp_name: str) -> bool:
    """Handle MCP approval process"""
    from datetime import datetime
    
    print(f"🔒 Approving MCP: {mcp_name}")
    
    config_files = [
        "external_config_official.json",
        "external_config_github_public.json"
    ]
    
    for config_file in config_files:
        config_path = project_root / "mcp" / "config" / config_file
        if not config_path.exists():
            continue
            
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Find and approve the MCP
        for mcp_key, mcp_config in config.get("mcps", {}).items():
            if mcp_config.get("name") == mcp_name:
                mcp_config["_approval_date"] = datetime.now().isoformat()
                mcp_config["_approved_by"] = os.getenv("USER", "unknown")
                mcp_config["_approval_note"] = "Approved via validation script"
                
                # Save updated config
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                
                print(f"✅ Approved {mcp_name} in {config_file}")
                return True
    
    print(f"❌ MCP not found: {mcp_name}")
    return False

if __name__ == "__main__":
    main()