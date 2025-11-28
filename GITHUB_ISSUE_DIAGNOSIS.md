# GitHub Repository Issue - Diagnostic Guide

## Problem Description

The landing page generator is failing with the error:
```
GitHub repository or path not found: https://api.github.com/repos/saltbalente/monorepo-landings/contents/landing-194499501532/index.html
```

This indicates that the system cannot publish landing pages to the configured GitHub repository.

## Quick Diagnosis

Run the diagnostic script to identify the exact issue:

```bash
python3 github_diagnostics.py
```

This will check:
- ✅ Environment variables configuration
- ✅ Repository existence
- ✅ Push permissions
- ✅ Token validity
- ✅ API access

## Common Issues and Solutions

### 1. Repository Not Found
**Error**: `Repository 'owner/repo' not found`

**Solutions**:
- Check that `GITHUB_REPO_OWNER` and `GITHUB_REPO_NAME` are correct
- Verify the repository exists on GitHub
- Ensure the repository name is spelled correctly

### 2. No Push Permissions
**Error**: `No push permissions to repository`

**Solutions**:
- The GitHub token needs `repo` or `public_repo` scope
- For private repositories, ensure the token has full `repo` access
- Check if you're a collaborator on the repository

### 3. Invalid Token
**Error**: `Authentication failed` or `Token validation failed`

**Solutions**:
- Regenerate the GitHub token
- Ensure `GITHUB_TOKEN` environment variable is set correctly
- Check token expiration date
- Verify token has required scopes

### 4. Repository Doesn't Exist
**Error**: Repository verification shows "not found"

**Solutions**:
- Create the repository on GitHub first
- Use the exact owner/name format (case-sensitive)
- For organizations, ensure you have access

## Environment Variables Required

Set these environment variables in your deployment:

```bash
export GITHUB_REPO_OWNER="your-github-username"
export GITHUB_REPO_NAME="your-repo-name"
export GITHUB_TOKEN="your-github-personal-access-token"
```

## Token Scopes Required

Your GitHub token must have these scopes:
- `repo` (for private repos) or `public_repo` (for public repos)
- `workflow` (if using GitHub Actions)

## Testing the Fix

After fixing the configuration:

1. Run diagnostics: `python3 github_diagnostics.py`
2. All checks should show ✅
3. Try the landing page generation again

## Alternative Solutions

If GitHub publishing continues to fail:

1. **Check Repository Settings**: Ensure the repository allows pushes
2. **Branch Protection**: Check if `main` branch has protection rules
3. **Organization Settings**: For org repos, check branch restrictions
4. **Token Permissions**: Regenerate token with correct scopes

## Support

If issues persist after following this guide:
1. Run the diagnostic script and share the output
2. Check the application logs for additional error details
3. Verify all environment variables are set correctly in production