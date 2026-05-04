#!/usr/bin/env python3
"""
Quick Start Script for Commercial Auto Fraud Detection Pipeline
This script helps you verify your setup and get started quickly.
"""

import os
import sys
import subprocess
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")


def print_step(number, text):
    """Print a step number and description."""
    print(f"\n{'='*70}")
    print(f"STEP {number}: {text}")
    print('='*70)


def check_python_version():
    """Check if Python version is 3.10 or higher."""
    print_step(1, "Checking Python Version")
    
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("❌ Error: Python 3.10 or higher is required")
        print("   Please upgrade Python and try again")
        return False
    
    print("✅ Python version is compatible")
    return True


def check_env_file():
    """Check if .env file exists and has API key."""
    print_step(2, "Checking Environment Configuration")
    
    env_file = Path(".env")
    
    if not env_file.exists():
        print("⚠️  Warning: .env file not found")
        print("   Creating .env file with template...")
        
        with open(env_file, "w") as f:
            f.write("GEMINI_API_KEY=your_gemini_api_key_here\n")
            f.write("REDIS_URL=redis://localhost:6379/0\n")
            f.write("\n# A2A Remote URLs\n")
            f.write("ENRICHMENT_A2A_URL=http://localhost:8002\n")
            f.write("ANALYZER_A2A_URL=http://localhost:8003\n")
            f.write("REPORT_A2A_URL=http://localhost:8004\n")
        
        print("✅ Created .env file")
        print("\n⚠️  IMPORTANT: Edit .env and add your Gemini API key!")
        print("   Get your API key from: https://aistudio.google.com/app/apikey")
        return False
    
    # Check if API key is set
    with open(env_file, "r") as f:
        content = f.read()
    
    if "your_gemini_api_key_here" in content or "GEMINI_API_KEY=" not in content:
        print("⚠️  Warning: Gemini API key not configured in .env")
        print("   Please edit .env and add your API key")
        print("   Get your API key from: https://aistudio.google.com/app/apikey")
        return False
    
    print("✅ Environment configuration found")
    return True


def check_dependencies():
    """Check if required dependencies are installed."""
    print_step(3, "Checking Dependencies")
    
    try:
        import google.adk
        print("✅ google-adk installed")
    except ImportError:
        print("❌ google-adk not installed")
        return False
    
    try:
        import fastapi
        print("✅ fastapi installed")
    except ImportError:
        print("❌ fastapi not installed")
        return False
    
    try:
        import pydantic
        print("✅ pydantic installed")
    except ImportError:
        print("❌ pydantic not installed")
        return False
    
    print("\n✅ All required dependencies are installed")
    return True


def check_sample_data():
    """Check if sample data file exists."""
    print_step(4, "Checking Sample Data")
    
    sample_file = Path("weekly_auto_claims.json")
    
    if not sample_file.exists():
        print("❌ Error: weekly_auto_claims.json not found")
        print("   This file should be in the project root directory")
        return False
    
    print("✅ Sample data file found")
    return True


def install_dependencies():
    """Offer to install dependencies."""
    print("\n" + "="*70)
    print("Would you like to install dependencies now? (y/n): ", end="")
    response = input().strip().lower()
    
    if response != 'y':
        print("\nPlease install dependencies manually:")
        print("  Option 1 (uv):  uv sync")
        print("  Option 2 (pip): pip install -e .")
        return False
    
    print("\nInstalling dependencies...")
    
    # Try uv first
    try:
        result = subprocess.run(["uv", "sync"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Dependencies installed successfully with uv")
            return True
    except FileNotFoundError:
        pass
    
    # Fall back to pip
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Dependencies installed successfully with pip")
            return True
        else:
            print(f"❌ Installation failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return False


def print_next_steps(all_checks_passed):
    """Print next steps based on check results."""
    print_header("SETUP STATUS")
    
    if all_checks_passed:
        print("🎉 All checks passed! You're ready to run the system.\n")
        print("Next steps:")
        print("  1. Start all services:")
        print("     python main.py")
        print("\n  2. In another terminal, run the test:")
        print("     python test_pipeline.py")
        print("\n  3. Open the dashboard:")
        print("     http://localhost:8001/dashboard")
        print("\n  4. Read the documentation:")
        print("     - README.md for detailed information")
        print("     - SETUP.md for troubleshooting")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.\n")
        print("Common fixes:")
        print("  1. Install dependencies:")
        print("     uv sync  (or)  pip install -e .")
        print("\n  2. Configure your API key in .env:")
        print("     GEMINI_API_KEY=your_actual_key_here")
        print("\n  3. Get your API key from:")
        print("     https://aistudio.google.com/app/apikey")
        print("\nAfter fixing, run this script again: python quickstart.py")


def main():
    """Run all checks and provide guidance."""
    print_header("COMMERCIAL AUTO FRAUD DETECTION - QUICK START")
    
    print("This script will verify your setup and help you get started.\n")
    
    checks = []
    
    # Run all checks
    checks.append(("Python Version", check_python_version()))
    checks.append(("Environment Config", check_env_file()))
    checks.append(("Sample Data", check_sample_data()))
    checks.append(("Dependencies", check_dependencies()))
    
    # If dependencies check failed, offer to install
    if not checks[-1][1]:
        if install_dependencies():
            checks[-1] = ("Dependencies", True)
    
    # Print summary
    all_passed = all(result for _, result in checks)
    print_next_steps(all_passed)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
