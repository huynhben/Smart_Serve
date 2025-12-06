# Code Review Template

This template should be used when conducting peer code reviews for pull requests. Fill out each section thoroughly.

---

## Overview

**PR Title:** [Title of the Pull Request]

**PR Author:** [Author's name]

**Reviewer:** [Your name]

**Date:** [Date of review]

**General Comment:**
[Provide a high-level summary of the PR. What does it do? What problem does it solve? What is your overall impression?]

---

## Correctness

**Does the code work for the intended purpose?**

[Evaluate whether the code achieves its stated goals and works correctly. Consider:]
- Does the code handle edge cases?
- Are there any obvious bugs or logic errors?
- Do the changes break existing functionality?
- Are error cases handled appropriately?
- Is the implementation complete?

**Specific Issues Found:**
- [List any correctness issues]
- [Include line numbers and file paths if applicable]

---

## Clarity

**Is it readable and understandable?**

[Evaluate code readability and documentation:]
- Is the code self-explanatory?
- Are variable and function names clear and descriptive?
- Are comments helpful and accurate?
- Is the code structure logical and easy to follow?
- Would a new team member understand this code?

**Specific Observations:**
- [Positive aspects]
- [Areas that could be clearer]

---

## Maintainability

**Does it follow normal coding and style conventions?**

[Evaluate code quality, consistency, and maintainability:]
- Does it follow the project's coding style?
- Is the code DRY (Don't Repeat Yourself)?
- Is it modular and well-organized?
- Are there appropriate abstractions?
- Is it testable?
- Does it add technical debt?

**Specific Observations:**
- [Style consistency]
- [Potential refactoring opportunities]
- [Code organization]

---

## AI-Specific Concerns

**If AI was used, explain what issues were found in AI-generated code and potential lessons learned about relying on AI for implementation.**

[Only fill this out if the PR indicates AI was used. Consider:]
- Are there patterns typical of AI-generated code (overly verbose, generic solutions)?
- Does the code seem to miss domain-specific nuances?
- Are there any security concerns with AI-generated code?
- What lessons can be learned about using AI tools?
- What human oversight was needed?

**Issues Found:**
- [List AI-specific issues]

**Lessons Learned:**
- [What can be learned about using AI for code generation?]
- [What verification steps were necessary?]

---

## Recommendation

**Final outcome for the PR:**

Choose one:
- [ ] ✅ **Approve/Merge as is** - The code is ready to merge
- [ ] 🔄 **Return for changes** - Needs revisions before merging
- [ ] ❌ **Close** - The PR should not be merged (explain why)

**Reasoning:**
[Provide clear justification for your recommendation. If changes are needed, prioritize them (must-fix vs. nice-to-have).]

**Required Changes:**
- [List changes that must be made before merging]

**Optional Improvements:**
- [List suggestions for future improvements]

---

## Additional Notes

[Any other observations, questions, or suggestions that don't fit in the above categories]

---

## Review Checklist

- [ ] I have reviewed all changed files
- [ ] I have tested the changes (if applicable)
- [ ] I have checked for security concerns
- [ ] I have verified tests pass (if applicable)
- [ ] I have considered backward compatibility
- [ ] I have provided constructive feedback

---

## Example Review Structure

Here's an example of how to structure your review:

### Overview
This PR adds error handling for invalid entry IDs in the delete/edit endpoints. The changes look solid overall and address a legitimate issue where 500 errors were being returned instead of 404s.

### Correctness
The code correctly catches IndexError exceptions and converts them to HTTPException with 404 status. However, I noticed that...

### Clarity
The code is well-documented and the error messages are clear. The try-except blocks make the error handling obvious.

### Maintainability
The code follows the existing patterns in the codebase. The error handling is consistent with how other endpoints might handle similar errors.

### AI-Specific Concerns
[If applicable]

### Recommendation
✅ Approve/Merge as is - Small improvement, well-tested, ready to merge.

---

**Remember:** Code reviews should be constructive and respectful. Focus on the code, not the person. Provide specific, actionable feedback.
