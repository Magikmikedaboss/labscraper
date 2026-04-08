# CI/CD Pipeline Guide

## Overview

The peptide scraper project now includes a comprehensive CI/CD pipeline that automates code quality checks, security scanning, and testing on every push and pull request.

## Pipeline Configuration

### Location
- **File**: `.github/workflows/ci.yml`
- **Trigger Events**: 
  - Push to `main` or `develop` branches
  - Pull requests to `main` branch

### Pipeline Jobs

#### Test Job
The main test job runs on Ubuntu latest and performs the following steps:

1. **Checkout Code**
   - Uses `actions/checkout@v4` to clone the repository

2. **Setup Python Environment**
   - Uses `actions/setup-python@v6` with Python 3.10
   - Ensures consistent Python version across all environments
   - Compatible with modern GitHub Actions runners and Node.js versions

3. **Install Dependencies**
   - Upgrades pip for latest features
   - Checks for lock file (`requirements/requirements-lock.txt`) and uses it if present for reproducible installs
   - Falls back to `requirements.txt` if no lock file exists
   - Installs development tools: `pytest`, `pytest-cov`, `ruff`, `bandit`, `safety`

4. **Code Quality Checks**
   - **Linting**: Runs `ruff check .` to catch syntax errors, style violations, and potential bugs
   - **Security Scanning**: 
     - `bandit -r utils/ tools/ -ll` - Static security analysis
     - `safety check --json` - Dependency vulnerability scanning

5. **Testing**
   - **Unit Tests**: Runs `pytest tests/ -v --cov=utils --cov=tools --cov-report=term-missing`
   - **Coverage Check**: Enforces minimum 70% code coverage with `pytest --cov=utils --cov=tools --cov-fail-under=70`

## Quality Gates

### Code Quality
- **Ruff Linting**: Catches syntax errors, style violations, and potential bugs
- **Security Analysis**: Bandit identifies security vulnerabilities in Python code
- **Dependency Security**: Safety checks for known vulnerabilities in dependencies

### Test Coverage
- **Minimum Coverage**: 70% code coverage required
- **Coverage Reporting**: Detailed coverage reports with missing lines highlighted
- **Test Execution**: All tests must pass for pipeline to succeed

## Benefits

### Automated Quality Assurance
- **Consistent Code Quality**: Every commit is linted and checked
- **Security First**: Automated security scanning prevents vulnerabilities
- **Test Coverage**: Ensures adequate test coverage is maintained

### Developer Experience
- **Fast Feedback**: Issues caught immediately on push/PR
- **Clear Standards**: Automated enforcement of coding standards
- **Reduced Manual Work**: No need to manually run quality checks

### Project Reliability
- **Regression Prevention**: Tests catch breaking changes
- **Security Posture**: Regular security scanning
- **Code Maintainability**: Consistent code style and quality

## Local Development

### Running Pipeline Locally
You can run the same checks locally before pushing:

```bash
# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov ruff bandit safety

# Run linting
ruff check .

# Run security checks
bandit -r utils/ tools/ -ll
safety check --json

# Run tests with coverage
pytest tests/ -v --cov=utils --cov=tools --cov-report=term-missing

# Check coverage threshold
pytest --cov=utils --cov=tools --cov-fail-under=70
```

### Pre-commit Hooks (Optional)
For even faster feedback, you can set up pre-commit hooks:

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.8
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
EOF

# Install hooks
pre-commit install
```

## Pipeline Maintenance

### Adding New Checks
To add additional quality checks, modify the `.github/workflows/ci.yml` file:

```yaml
- name: New Quality Check
  run: your-quality-check-command
```

### Updating Dependencies
When adding new dependencies to `requirements.txt`, ensure they're compatible with the CI environment:

```bash
# Test locally with Python 3.10
python3.10 -m venv test-env
source test-env/bin/activate  # On Windows: test-env\Scripts\activate
pip install -r requirements.txt
```

### Coverage Thresholds
The coverage threshold can be adjusted in the pipeline:

```yaml
- name: Check coverage threshold
  run: |
    pytest --cov=utils --cov=tools --cov-fail-under=80  # Change 70 to desired percentage
```

## Troubleshooting

### Common Issues

1. **Linting Failures**
   - Fix style violations reported by ruff
   - Use `ruff check --fix .` to auto-fix some issues

2. **Security Scan Failures**
   - Review bandit output for security issues
   - Update vulnerable dependencies identified by safety

3. **Test Failures**
   - Check test output for specific failure reasons
   - Ensure tests pass locally before pushing

4. **Coverage Failures**
   - Add tests for uncovered code
   - Review coverage reports to identify gaps

### Getting Help

- **Pipeline Logs**: Check GitHub Actions tab for detailed logs
- **Local Testing**: Run the same commands locally to debug issues
- **Documentation**: Refer to tool documentation:
  - [Ruff](https://docs.astral.sh/ruff/)
  - [Bandit](https://bandit.readthedocs.io/)
  - [Safety](https://pyup.io/safety/)
  - [Pytest](https://docs.pytest.org/)

## Integration with Development Workflow

### Pull Request Process
1. Create feature branch from `develop`
2. Make changes and commit
3. Push to remote (triggers pipeline)
4. Create pull request to `main`
5. Pipeline runs on PR
6. Address any pipeline failures
7. Merge when pipeline passes

### Branch Protection
Consider setting up branch protection rules in GitHub:
- Require passing CI checks before merge
- Require up-to-date branches
- Disallow force pushes to protected branches

This ensures the CI pipeline acts as a quality gate for all changes.