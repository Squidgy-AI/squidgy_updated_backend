#!/bin/bash
# Setup script for MCP pre-commit validation

set -e

echo "🔧 Setting up MCP validation pre-commit hooks..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Not a git repository. Please run this from the project root."
    exit 1
fi

# Install pre-commit if not available
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit
fi

# Install the pre-commit hooks
echo "🔗 Installing pre-commit hooks..."
pre-commit install

# Test the validation script
echo "🧪 Testing MCP validation script..."
python scripts/validate_mcp_configs.py

# Run pre-commit on existing files
echo "🔍 Running pre-commit on existing MCP configs..."
pre-commit run --files mcp/config/*.json || true

echo ""
echo "✅ MCP validation setup complete!"
echo ""
echo "📋 What's been set up:"
echo "   • Pre-commit hooks for MCP config validation"
echo "   • JSON syntax checking"
echo "   • Security compliance validation"
echo "   • GitHub Actions workflow for PRs"
echo ""
echo "🚀 Usage:"
echo "   • Validate configs: python scripts/validate_mcp_configs.py"
echo "   • Approve MCP: python scripts/validate_mcp_configs.py --approve instagram-tools"
echo "   • Strict validation: python scripts/validate_mcp_configs.py --strict"
echo ""
echo "🔒 Security workflow:"
echo "   1. Add/modify MCP in config JSON"
echo "   2. Pre-commit hook validates on commit"
echo "   3. GitHub Actions validates on PR"
echo "   4. Manual approval required for community MCPs"
echo "   5. Merge only after security review"