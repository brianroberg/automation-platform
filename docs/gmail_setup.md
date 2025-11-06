# Gmail API Setup Guide

## Prerequisites

- Google account with Gmail
- Access to Google Cloud Console

## Step-by-Step Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a Project" → "New Project"
3. Name it "Automation Platform" (or your preference)
4. Click "Create"
5. Wait for project creation to complete

### 2. Enable Gmail API

1. In the Cloud Console, navigate to "APIs & Services" → "Library"
2. Search for "Gmail API"
3. Click on "Gmail API"
4. Click "Enable"
5. Wait for API to be enabled

### 3. Configure OAuth Consent Screen

1. Navigate to "APIs & Services" → "OAuth consent screen"
2. Select "External" user type (unless you have Google Workspace)
3. Click "Create"
4. Fill in required fields:
   - **App name**: "Automation Platform"
   - **User support email**: (your email)
   - **Developer contact**: (your email)
5. Click "Save and Continue"

6. Click "Add or Remove Scopes"
7. Add these scopes:
   - `openid`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/gmail.modify`
8. Click "Update" → "Save and Continue"

9. Add your email as a test user:
   - Click "Add Users"
   - Enter your Gmail address
   - Click "Add"
10. Click "Save and Continue"

11. Review and click "Back to Dashboard"

### 4. Create OAuth Credentials

1. Navigate to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: "Desktop app"
4. Name: "Automation Platform Desktop Client"
5. Click "Create"
6. Click "Download JSON" on the popup (or download from credentials list)
7. Save the file as `config/gmail_credentials.json` in your project

### 5. First-Time Authentication

When you run the email triage workflow for the first time:

1. A browser window will open automatically
2. Sign in with your Google account
3. You may see a warning "Google hasn't verified this app"
   - Click "Advanced"
   - Click "Go to Automation Platform (unsafe)"
4. Review the permissions (basic profile + Gmail modify)
5. Click "Allow"
6. You should see "The authentication flow has completed"
7. Close the browser window
8. The token is saved to `config/gmail_token.json` for future use

## Security Notes

**Scopes Granted**:
- ✅ Basic profile info (`openid`, `userinfo.email`)
- ✅ Read, label, archive, and modify Gmail messages (`gmail.modify`)
- ✅ Underlying API access to compose/send endpoints (Google bundles this with `gmail.modify`)

**What the workflow actually does**:
- 🚫 Does **not** call message send or draft endpoints
- ✅ Only reads messages, classifies them, and applies/updates labels or read state

**Local Storage**:
- Credentials stored locally in `config/` directory
- Never committed to git (listed in `.gitignore`)
- Token automatically refreshes when expired

## Troubleshooting

### "Access blocked: This app's request is invalid"

**Cause**: OAuth consent screen configuration issue

**Solution**:
1. Ensure app is in "Testing" mode (not "Production")
2. Verify your email is added as a test user
3. Confirm both required scopes are added
4. Try clearing browser cache and retrying

### "Credentials file not found"

**Cause**: OAuth credentials not in correct location

**Solution**:
1. Download OAuth credentials JSON from Google Cloud Console
2. Rename to `gmail_credentials.json` (exact name)
3. Place in `config/` directory (not project root)
4. Verify path: `config/gmail_credentials.json`

### "Redirect URI mismatch"

**Cause**: Wrong OAuth client type

**Solution**:
1. Delete existing OAuth credential
2. Create new credential
3. Select "Desktop app" (not "Web application")

### Browser doesn't open during authentication

**Cause**: Running in headless environment (SSH, Codespaces without port forwarding)

**Solution** for GitHub Codespaces:
1. The OAuth flow will print a URL to the terminal
2. Copy the URL
3. Open it in your local browser
4. Complete authentication
5. The token will be saved automatically

### "Token refresh failed"

**Cause**: Saved token is invalid or revoked

**Solution**:
1. Delete `config/gmail_token.json`
2. Run workflow again to re-authenticate
3. Complete OAuth flow in browser

## Revoking Access

To revoke the application's access to your Gmail:

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Scroll to "Third-party apps with account access"
3. Find "Automation Platform"
4. Click "Remove Access"
5. Delete `config/gmail_token.json` from your project

## Rate Limits

Gmail API has quotas:
- **Free tier**: 1 billion quota units per day
- **Cost per operation**:
  - Read message: 5 units
  - List messages: 5 units
  - Modify message: 5 units

**For reference**: Processing 100 emails = ~1,500 units (well within free tier)

## Next Steps

After completing Gmail setup:
1. ✅ Configure MLX connection in `.env`
2. ✅ Test Phase 3 success criteria
3. ✅ Proceed to Phase 4 (Email Triage Workflow)
