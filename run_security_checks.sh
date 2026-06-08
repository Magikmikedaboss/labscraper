#!/usr/bin/env bash

set -euo pipefail

set +e
bandit -r utils tools tests -l -f json -o bandit-report.json \
  --exclude "utils/test_*,tools/demo_*"
bandit_exit=$?
safety check --json -r requirements.txt -r requirements-lock.txt -r requirements_ui.txt > safety-report.json 2> safety-report.stderr
safety_exit=$?
set -e

if [ "$safety_exit" -ne 0 ] || [ -s safety-report.stderr ]; then
  echo "::error file=safety-report.stderr::Safety output from safety check:"
  cat safety-report.stderr
fi

if [ "$bandit_exit" -ne 0 ]; then
  echo "::warning file=bandit-report.json::Bandit found security issues. See bandit-report.json."
  python .github/scripts/summarize_security_report.py bandit-report.json bandit
fi

if [ "$safety_exit" -ne 0 ]; then
  echo "::warning file=safety-report.json::Safety found insecure packages. See safety-report.json."
  python .github/scripts/summarize_security_report.py safety-report.json safety
fi

if [ "$bandit_exit" -ne 0 ] || [ "$safety_exit" -ne 0 ]; then
  exit 1
fi