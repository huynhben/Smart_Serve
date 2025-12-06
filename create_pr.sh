#!/bin/bash
# Script to open GitHub PR creation page

echo "Opening GitHub PR creation page..."
echo ""
echo "Branch: improve-error-handling"
echo "Repository: dhruv-addanki/PM4"
echo ""

# Open the PR creation URL in the default browser
open "https://github.com/dhruv-addanki/PM4/pull/new/improve-error-handling" 2>/dev/null || \
xdg-open "https://github.com/dhruv-addanki/PM4/pull/new/improve-error-handling" 2>/dev/null || \
echo "Please visit: https://github.com/dhruv-addanki/PM4/pull/new/improve-error-handling"

echo ""
echo "PR Details to use:"
echo "Title: Improve Error Handling for Entry Delete/Edit Endpoints"
echo ""
echo "Description (copy from PR_DESCRIPTION.md or use this):"
echo "---"
cat PR_DESCRIPTION.md
echo "---"
echo ""
echo "Don't forget to add an 'AI-assisted' label or mention AI usage in the description!"

