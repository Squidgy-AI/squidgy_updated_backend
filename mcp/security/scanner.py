import os
import subprocess
import tempfile
import json
from typing import Dict, List, Any
from ..models import SecurityScanResult
from ..config import config
import logging

logger = logging.getLogger(__name__)

class SecurityScanner:
    """Security scanner for external MCP repositories"""
    
    def __init__(self):
        self.scan_timeout = config.scan_timeout
        
    async def scan_repository(self, repo_url: str, mcp_id: str) -> SecurityScanResult:
        """Perform comprehensive security scan on a repository"""
        logger.info(f"Starting security scan for {repo_url}")
        
        scan_results = {
            "static_analysis": {},
            "dependency_scan": {},
            "code_quality": {},
            "file_analysis": {}
        }
        
        vulnerabilities = []
        risk_score = 0
        
        try:
            # Create temporary directory for repo
            with tempfile.TemporaryDirectory() as temp_dir:
                # Clone repository
                await self._clone_repository(repo_url, temp_dir)
                
                # Run static analysis
                static_results = await self._run_static_analysis(temp_dir)
                scan_results["static_analysis"] = static_results
                vulnerabilities.extend(static_results.get("vulnerabilities", []))
                
                # Run dependency scan
                dep_results = await self._run_dependency_scan(temp_dir)
                scan_results["dependency_scan"] = dep_results
                vulnerabilities.extend(dep_results.get("vulnerabilities", []))
                
                # Run code quality checks
                quality_results = await self._run_code_quality_checks(temp_dir)
                scan_results["code_quality"] = quality_results
                
                # Analyze file structure
                file_results = await self._analyze_file_structure(temp_dir)
                scan_results["file_analysis"] = file_results
                
                # Calculate risk score
                risk_score = self._calculate_risk_score(scan_results, vulnerabilities)
                
        except Exception as e:
            logger.error(f"Security scan failed for {repo_url}: {e}")
            vulnerabilities.append({
                "type": "scan_error",
                "severity": "high",
                "message": f"Failed to complete security scan: {str(e)}"
            })
            risk_score = 100  # Maximum risk for scan failures
        
        passed = risk_score < 50 and len([v for v in vulnerabilities if v.get("severity") == "high"]) == 0
        
        return SecurityScanResult(
            mcp_id=mcp_id,
            risk_score=risk_score,
            vulnerabilities=vulnerabilities,
            scan_details=scan_results,
            passed=passed
        )
    
    async def _clone_repository(self, repo_url: str, temp_dir: str):
        """Clone repository to temporary directory"""
        try:
            result = subprocess.run([
                "git", "clone", "--depth", "1", repo_url, temp_dir
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise Exception(f"Git clone failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise Exception("Repository clone timed out")
    
    async def _run_static_analysis(self, repo_path: str) -> Dict[str, Any]:
        """Run Bandit static analysis"""
        results = {"vulnerabilities": [], "summary": {}}
        
        try:
            # Run bandit
            result = subprocess.run([
                "bandit", "-r", repo_path, "-f", "json"
            ], capture_output=True, text=True, timeout=120)
            
            if result.stdout:
                bandit_output = json.loads(result.stdout)
                
                for issue in bandit_output.get("results", []):
                    results["vulnerabilities"].append({
                        "type": "static_analysis",
                        "tool": "bandit",
                        "severity": issue.get("issue_severity", "medium").lower(),
                        "message": issue.get("issue_text", ""),
                        "file": issue.get("filename", ""),
                        "line": issue.get("line_number", 0),
                        "test_id": issue.get("test_id", "")
                    })
                
                results["summary"] = {
                    "total_issues": len(results["vulnerabilities"]),
                    "high_severity": len([v for v in results["vulnerabilities"] if v["severity"] == "high"]),
                    "medium_severity": len([v for v in results["vulnerabilities"] if v["severity"] == "medium"]),
                    "low_severity": len([v for v in results["vulnerabilities"] if v["severity"] == "low"])
                }
                
        except Exception as e:
            logger.warning(f"Static analysis failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def _run_dependency_scan(self, repo_path: str) -> Dict[str, Any]:
        """Run dependency vulnerability scan"""
        results = {"vulnerabilities": [], "summary": {}}
        
        try:
            # Look for requirements files
            req_files = []
            for filename in ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]:
                req_path = os.path.join(repo_path, filename)
                if os.path.exists(req_path):
                    req_files.append(req_path)
            
            for req_file in req_files:
                try:
                    # Run safety check
                    result = subprocess.run([
                        "safety", "check", "-r", req_file, "--json"
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.stdout:
                        safety_output = json.loads(result.stdout)
                        
                        for vuln in safety_output:
                            results["vulnerabilities"].append({
                                "type": "dependency",
                                "tool": "safety",
                                "severity": "high" if vuln.get("severity") else "medium",
                                "message": vuln.get("advisory", ""),
                                "package": vuln.get("package_name", ""),
                                "version": vuln.get("analyzed_version", ""),
                                "cve": vuln.get("cve", "")
                            })
                            
                except Exception as e:
                    logger.warning(f"Safety scan failed for {req_file}: {e}")
            
            results["summary"] = {
                "files_scanned": len(req_files),
                "total_vulnerabilities": len(results["vulnerabilities"])
            }
            
        except Exception as e:
            logger.warning(f"Dependency scan failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def _run_code_quality_checks(self, repo_path: str) -> Dict[str, Any]:
        """Run basic code quality checks"""
        results = {"issues": [], "metrics": {}}
        
        try:
            # Count lines of code
            total_lines = 0
            python_files = 0
            
            for root, dirs, files in os.walk(repo_path):
                for file in files:
                    if file.endswith('.py'):
                        python_files += 1
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                total_lines += len(f.readlines())
                        except:
                            pass
            
            results["metrics"] = {
                "total_python_files": python_files,
                "total_lines_of_code": total_lines,
                "avg_lines_per_file": total_lines / python_files if python_files > 0 else 0
            }
            
            # Check for suspicious patterns
            if total_lines > 10000:
                results["issues"].append({
                    "type": "code_size",
                    "severity": "medium",
                    "message": f"Large codebase ({total_lines} lines) - increases attack surface"
                })
            
        except Exception as e:
            logger.warning(f"Code quality check failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def _analyze_file_structure(self, repo_path: str) -> Dict[str, Any]:
        """Analyze repository file structure for suspicious content"""
        results = {"issues": [], "file_types": {}}
        
        try:
            suspicious_files = []
            file_types = {}
            
            for root, dirs, files in os.walk(repo_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()
                    
                    # Count file types
                    file_types[file_ext] = file_types.get(file_ext, 0) + 1
                    
                    # Check for suspicious files
                    if file.lower() in ['eval', 'exec', 'subprocess', 'shell']:
                        suspicious_files.append(file_path)
                    
                    if file_ext in ['.exe', '.dll', '.so', '.dylib']:
                        suspicious_files.append(file_path)
            
            results["file_types"] = file_types
            
            if suspicious_files:
                results["issues"].append({
                    "type": "suspicious_files",
                    "severity": "high",
                    "message": f"Found {len(suspicious_files)} suspicious files",
                    "files": suspicious_files[:10]  # Limit to first 10
                })
            
        except Exception as e:
            logger.warning(f"File structure analysis failed: {e}")
            results["error"] = str(e)
        
        return results
    
    def _calculate_risk_score(self, scan_results: Dict, vulnerabilities: List[Dict]) -> int:
        """Calculate overall risk score (0-100)"""
        base_score = 0
        
        # Static analysis vulnerabilities
        high_static = len([v for v in vulnerabilities if v.get("type") == "static_analysis" and v.get("severity") == "high"])
        medium_static = len([v for v in vulnerabilities if v.get("type") == "static_analysis" and v.get("severity") == "medium"])
        
        base_score += high_static * 25
        base_score += medium_static * 10
        
        # Dependency vulnerabilities
        dep_vulns = len([v for v in vulnerabilities if v.get("type") == "dependency"])
        base_score += dep_vulns * 15
        
        # Code quality issues
        code_issues = len(scan_results.get("code_quality", {}).get("issues", []))
        base_score += code_issues * 5
        
        # File structure issues
        file_issues = len(scan_results.get("file_analysis", {}).get("issues", []))
        base_score += file_issues * 10
        
        # Cap at 100
        return min(base_score, 100)