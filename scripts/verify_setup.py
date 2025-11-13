"""
Verify that the development environment is correctly configured for the
Trustworthy Charity Agents codelab.
"""

import sys
import os
from importlib.metadata import version, PackageNotFoundError
import subprocess


def check_python_version():
    """Verify Python version is 3.10 or higher."""
    major, minor = sys.version_info[:2]
    if major >= 3 and minor >= 10:
        print(f"✓ Python version: {major}.{minor}.{sys.version_info[2]}")
        return True
    else:
        print(f"✗ Python version: {major}.{minor} (minimum 3.10 required)")
        return False


def check_package(package_name, min_version=None):
    """Check if a package is installed."""
    try:
        installed_version = version(package_name)
        print(f"✓ {package_name}: {installed_version}")
        return True
    except PackageNotFoundError:
        print(f"✗ {package_name}: not installed")
        print(f"  Please run: pip install -r requirements.txt")
        return False


def check_env_file():
    """Check if .env file exists and contains the project ID."""
    if not os.path.exists(".env"):
        print("✗ .env file missing")
        print("  Hint: cp .env.template .env")
        return False

    with open(".env", "r") as f:
        content = f.read()
        has_project = False

        # Check for GOOGLE_CLOUD_PROJECT
        for line in content.split('\n'):
            if line.startswith('GOOGLE_CLOUD_PROJECT='):
                if 'your-project-id' not in line and line.strip() != 'GOOGLE_CLOUD_PROJECT=':
                    has_project = True
                    break

        if has_project:
            print("✓ .env file found and contains project ID")
            return True
        else:
            print("✗ .env file has placeholder project ID")
            print("  Please update GOOGLE_CLOUD_PROJECT in .env")
            return False


def check_gcloud_project():
    """Confirm that the gcloud CLI is configured with a project."""
    try:
        project = subprocess.check_output(
            ["gcloud", "config", "get-value", "project"],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        if project:
            print(f"✓ Google Cloud project configured: {project}")
            return True
        else:
            print("✗ No Google Cloud project configured")
            print("  Hint: gcloud config set project YOUR_PROJECT_ID")
            return False
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("✗ gcloud CLI not found or not configured")
        return False


def check_project_structure():
    """Check if required directories exist."""
    required_dirs = [
        'charity_advisor',
        'charity_advisor/shopping_agent',
        'charity_advisor/merchant_agent',
        'charity_advisor/credentials_provider',
        'charity_advisor/simple_agent',
        'charity_advisor/tools',
        'charity_advisor/data',
        'scripts'
    ]
    all_present = True

    print("\n✓ Checking project structure:")
    for dir_name in required_dirs:
        if os.path.isdir(dir_name):
            print(f"  ✓ {dir_name}/ directory present")
        else:
            print(f"  ✗ {dir_name}/ directory missing")
            all_present = False

    return all_present


def check_template_files():
    """Check if key template files exist."""
    required_files = [
        ('charity_advisor/data/charities.py', 'Mock charity database'),
        ('.env.template', 'Environment template'),
        ('charity_advisor/requirements.txt', 'Dependencies file'),
        ('setup.py', 'Setup script'),
        ('deploy.sh', 'Deployment script'),
        ('charity_advisor/agent.py', 'Main orchestration agent'),
        ('charity_advisor/agent_engine_app.py', 'Agent Engine wrapper')
    ]

    all_present = True
    print("\n✓ Checking template files:")

    for file_path, description in required_files:
        if os.path.exists(file_path):
            print(f"  ✓ {description} found")
        else:
            print(f"  ✗ {description} missing ({file_path})")
            all_present = False

    return all_present


def main():
    print("=" * 70)
    print("SETUP VERIFICATION")
    print("=" * 70)
    print()

    # Core checks
    checks = [
        check_python_version(),
        check_package("google-adk"),
        check_package("google-cloud-aiplatform"),
        check_package("ap2"),
        check_package("python-dotenv"),
        check_env_file(),
        check_gcloud_project(),
    ]

    # Project structure checks
    structure_ok = check_project_structure()
    files_ok = check_template_files()

    checks.extend([structure_ok, files_ok])

    print()
    print("=" * 70)

    if all(checks):
        print("✓ Setup complete! You are ready to build trustworthy agents.")
        print("=" * 70)
        return 0
    else:
        print("✗ Setup incomplete. Please fix the issues above.")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
