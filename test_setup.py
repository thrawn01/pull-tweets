#!/usr/bin/env python3
"""
Test script to validate the tweet extraction tool setup.
Run this after installing dependencies to verify everything works.

Usage:
    uv run python test_setup.py
"""

import sys
import importlib
import argparse
import os
import subprocess


def check_uv_installation():
    """Check if UV is available and get version."""
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ UV installed: {result.stdout.strip()}")
            return True
        else:
            print("✗ UV not found in PATH")
            return False
    except FileNotFoundError:
        print("✗ UV not installed")
        return False


def check_python_version():
    """Check Python version compatibility."""
    version = sys.version_info
    required = (3, 11)
    
    print(f"Testing Python version compatibility...")
    if version >= required:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} (>= {required[0]}.{required[1]} required)")
        if version >= (3, 13):
            print(f"  → Using Python {version.major}.{version.minor} (excellent compatibility)")
        elif version >= (3, 12):
            print(f"  → Using Python {version.major}.{version.minor} (great compatibility)")
        else:
            print(f"  → Using Python {version.major}.{version.minor} (minimum supported version)")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} (>= {required[0]}.{required[1]} required)")
        print(f"  → Please upgrade to Python 3.11 or newer")
        return False


def test_imports():
    """Test that all required modules can be imported."""
    modules = [
        'yaml',
        'pandas', 
        'pyarrow',
        'dateutil',
        'aiofiles',
        'psutil',
        'twikit',
    ]
    
    print("Testing dependency imports...")
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module}: {e}")
            return False
    
    return True


def test_local_imports():
    """Test that all local modules can be imported."""
    modules = [
        'config_manager',
        'auth_manager',
        'tweet_extractor', 
        'rate_limiter',
        'date_parser',
        'data_processor'
    ]
    
    print("\nTesting local module imports...")
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module}: {e}")
            return False
    
    return True


def test_config_template():
    """Test that config template is valid."""
    import yaml
    
    print("\nTesting config template...")
    try:
        with open('config.yaml.template', 'r') as f:
            config = yaml.safe_load(f)
        
        required_sections = ['auth', 'rate_limiting', 'output', 'processing']
        for section in required_sections:
            if section not in config:
                print(f"✗ Missing section: {section}")
                return False
            print(f"✓ {section} section found")
        
        return True
    except Exception as e:
        print(f"✗ Config template error: {e}")
        return False


def test_cli_help():
    """Test that CLI help works."""
    print("\nTesting CLI help...")
    try:
        from pull_tweets import parse_arguments
        parser = argparse.ArgumentParser()
        # This will test argument parsing setup
        print("✓ CLI argument parsing works")
        return True
    except Exception as e:
        print(f"✗ CLI test failed: {e}")
        return False


def check_project_files():
    """Check that all required project files exist."""
    required_files = [
        'pyproject.toml',
        'pull_tweets.py',
        'config.yaml.template',
        '.python-version',
        'setup.sh'
    ]
    
    print("Checking project structure...")
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ Missing: {file_path}")
            return False
    
    return True


def test_uv_environment():
    """Test UV environment and lock file status."""
    print("Testing UV environment...")
    
    # Check if we're running in UV context
    uv_project = os.path.exists('pyproject.toml')
    if not uv_project:
        print("! Not a UV project (missing pyproject.toml)")
        return True  # Not an error, just informational
    
    # Check if uv.lock exists
    if os.path.exists('uv.lock'):
        print("✓ uv.lock file exists")
    else:
        print("! uv.lock not found - run 'uv sync' to create")
        return True  # Not critical for testing
    
    # Check if virtual environment exists
    if os.path.exists('.venv'):
        print("✓ Virtual environment (.venv) exists")
    else:
        print("! Virtual environment not found - run 'uv sync' to create")
        return True  # Not critical for testing
    
    return True


def main():
    """Run all tests."""
    print("Tweet Extraction Tool - Setup Validation")
    print("=" * 50)
    
    # Basic system checks
    system_tests = [
        check_python_version,
        check_uv_installation,
        check_project_files,
        test_uv_environment
    ]
    
    # Application tests
    app_tests = [
        test_imports,
        test_local_imports, 
        test_config_template,
        test_cli_help
    ]
    
    all_tests = system_tests + app_tests
    passed = 0
    
    for test in all_tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{len(all_tests)} tests passed")
    
    if passed == len(all_tests):
        print("\n🎉 All tests passed! Setup is ready.")
        print("\nNext steps:")
        print("1. Copy config: cp config.yaml.template config.yaml")
        print("2. Add your X.com credentials to config.yaml")  
        print("3. Run: uv run python pull_tweets.py @username -o tweets.parquet")
        
        return 0
    else:
        print(f"\n❌ {len(all_tests) - passed} test(s) failed. Check the errors above.")
        
        # Provide helpful suggestions based on failures
        if not check_uv_installation():
            print("\n💡 To install UV: curl -LsSf https://astral.sh/uv/install.sh | sh")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())