# PR: Improve Error Handling for Entry Delete/Edit Endpoints

## Summary
This PR improves error handling for the `/api/entries/{entry_id}` DELETE and PATCH endpoints. Previously, when an invalid entry ID was provided, the API would return a 500 Internal Server Error. Now it properly returns a 404 Not Found error with a clear error message.

## Changes Made

### 1. API Error Handling (`food_tracker/api.py`)
- Added `HTTPException` import from FastAPI
- Wrapped `tracker.remove_entry()` call in try-except block to catch `IndexError`
- Wrapped `tracker.edit_entry()` call in try-except block to catch `IndexError`
- Convert `IndexError` exceptions to `HTTPException` with 404 status code and descriptive error message

### 2. Test Coverage (`tests/test_api.py`)
- Added `TestDeleteEntry` class with comprehensive tests:
  - Success case for deleting entries
  - 404 error for non-existent entry IDs
  - 404 error for negative entry IDs
  - Deleting specific entries when multiple exist
- Added `TestUpdateEntry` class with comprehensive tests:
  - Success case for updating entry quantity
  - 404 error for non-existent entry IDs
  - 404 error for negative entry IDs
  - Validation errors for invalid quantity values

## Benefits
- **Better API behavior**: Clients now receive appropriate HTTP status codes (404 instead of 500)
- **Improved error messages**: Clear, user-friendly error messages when entries are not found
- **Enhanced debugging**: Easier to distinguish between client errors (404) and server errors (500)
- **Better user experience**: Frontend can handle 404 errors more gracefully

## Testing
All new tests follow the existing test patterns in the codebase and use the same fixtures. The tests verify:
- Correct HTTP status codes
- Proper error message format
- Successful operations still work as expected
- Validation still works correctly

## AI Usage
This PR was created with AI assistance. The changes implement a common error handling pattern for REST APIs.
