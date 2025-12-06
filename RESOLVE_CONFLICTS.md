# Resolving Merge Conflicts

If GitHub is showing conflicts, here's how to resolve them:

## Option 1: Resolve on GitHub (Easiest)

1. Go to your PR on GitHub
2. Click "Resolve conflicts" button
3. GitHub will show you the conflicting files
4. For each conflict, you'll see:
   ```
   <<<<<<< improve-error-handling
   [Your changes]
   =======
   [Main branch changes]
   >>>>>>> main
   ```

5. **For `food_tracker/api.py`:**
   - Keep your version (with the try-except blocks)
   - Remove the conflict markers
   - The final code should have:
     ```python
     @api_router.delete("/entries/{entry_id}", status_code=204)
     def delete_entry(entry_id: int, tracker: FoodTracker = Depends(get_tracker)) -> None:
         """Delete a food entry by its ID."""
         try:
             tracker.remove_entry(entry_id)
         except IndexError:
             raise HTTPException(status_code=404, detail=f"Entry with ID {entry_id} not found")
     
     @api_router.patch("/entries/{entry_id}", status_code=200)
     def update_entry(entry_id: int, payload: EditEntryPayload, tracker: FoodTracker = Depends(get_tracker)) -> Dict[str, object]:
         """Update the quantity of a food entry."""
         try:
             entry = tracker.edit_entry(entry_id, payload.quantity)
             return _serialise_entry(entry)
         except IndexError:
             raise HTTPException(status_code=404, detail=f"Entry with ID {entry_id} not found")
     ```

6. **For `tests/test_api.py`:**
   - Keep your version (with the new test classes)
   - Remove conflict markers
   - Make sure both TestDeleteEntry and TestUpdateEntry classes are included

7. Click "Mark as resolved" for each file
8. Click "Commit merge"

## Option 2: Resolve Locally (If GitHub doesn't work)

```bash
# Make sure you're on your branch
git checkout improve-error-handling

# Fetch latest changes
git fetch origin

# Try to merge main
git merge origin/main

# If conflicts appear, edit the files to resolve them
# Then:
git add food_tracker/api.py tests/test_api.py
git commit -m "Resolve merge conflicts"
git push origin improve-error-handling
```

## What to Keep

**Always keep your version** because:
- Your version has the error handling improvements
- Your version has the comprehensive tests
- Your changes are additive (they add functionality, not remove it)

## If No Real Conflicts Exist

Sometimes GitHub shows conflicts that don't actually exist. Try:
1. Refresh the PR page
2. Click "Update branch" button on GitHub
3. Or push your branch again: `git push origin improve-error-handling`

## Current Status

Your branch is up to date locally. The conflicts might be:
- A GitHub UI issue (refresh the page)
- Different base branch (check PR settings)
- Whitespace differences (GitHub is sensitive to these)

If you can share which files GitHub says have conflicts, I can help resolve them more specifically!
