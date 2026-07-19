#!/usr/bin/env bash
# Pre-push gate: run before every push to main. Mirrors the checks in
# .github/workflows/no-internal-docs.yml so a leak is caught locally,
# not just after it reaches GitHub.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

forbidden_files=$(git diff --cached --name-only 2>/dev/null | grep -E '^(CLAUDE\.md|TODOS\.md|BRANCH_PROTECTION\.md|docs/branch-protection\.md|docs/security-review-.*\.md|docs/launch/.*|docs/.*preprint.*)$' || true)
if [ -n "$forbidden_files" ]; then
  echo "BLOCKED: internal-only file(s) staged for this public repo:"
  echo "$forbidden_files"
  exit 1
fi

pattern='CEO review|office.?hours|eng.?review|devex review|CSO review|CSO threat.?model|/oss-[0-9]+-[a-z-]+|/plan-eng-review|/review finding|Reviewer Concern|viability score|WOUNDED|fundrais|investor.?outreach|Show HN draft|hype.?seed'
hits=$(git diff --cached | grep -inE "$pattern" || true)
if [ -n "$hits" ]; then
  echo "BLOCKED: internal-process language in staged changes:"
  echo "$hits"
  exit 1
fi

echo "no-internal-docs check passed."
