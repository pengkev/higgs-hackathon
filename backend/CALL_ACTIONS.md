# Call Actions - Forward & End Call

## Overview

The receptionist bot can now:

1. **Forward legitimate calls** to BosonAI's personal phone
2. **End spam/scam calls** automatically

## How It Works

### AI Decision Making

The BosonAI model analyzes the conversation and determines if the caller is:

- **Legitimate**: Someone who needs to speak with BosonAI
- **Spam/Scam**: Robocaller, telemarketer, or suspicious caller

### Actions

#### 1. Forward Call

When the bot determines the caller is legitimate and wants to speak with BosonAI:

```
Bot: "Let me connect you to BosonAI now."
[Call forwards to BosonAI's personal phone]
```

The bot responds with `FORWARD_CALL` command, which:

1. Sends a polite message to the caller
2. Uses Twilio API to update the call and dial BosonAI's number
3. Connects the caller directly to BosonAI

#### 2. End Call

When the bot identifies a spam/scam call:

```
Bot: "I'm sorry, but I will need to end this call. Goodbye."
[Call ends immediately]
```

The bot responds with `END_CALL` command, which:

1. Sends a polite goodbye message
2. Uses Twilio API to end the call
3. Logs the spam attempt

## Configuration

### Required Environment Variables (.env)

```bash
# Twilio credentials (for API access)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here

# BosonAI's personal phone number (E.164 format)
BOSONAI_PHONE_NUMBER=+1234567890
```

### Get Twilio Credentials

1. Log in to [Twilio Console](https://console.twilio.com/)
2. Find Account SID and Auth Token on the dashboard
3. Add them to your `.env` file

## Example Conversations

### Legitimate Call (Forwarded)

```
Bot: Hi, you've reached the office of BosonAI. How can I help you today?
Caller: Hi, this is Sarah from Acme Corp. I need to discuss the contract with BosonAI.
Bot: Thank you, Sarah. Let me connect you to BosonAI right now.
[Call forwards to BosonAI's phone: +1234567890]
```

### Spam Call (Ended)

```
Bot: Hi, you've reached the office of BosonAI. How can I help you today?
Caller: Hello, we're calling about your car's extended warranty...
Bot: I'm sorry, but that sounds like a spam call. Thank you for calling, but I will need to end this call now.
[Call ends]
```

## Logs

The server logs all actions with emojis for easy identification:

- 📞 `Forwarding call to +1234567890`
- 🚫 `Ending call (spam)`
- ✅ `Call forwarded successfully`
- ❌ `Failed to forward call`

## Testing

### Test Call Forwarding

1. Call your Twilio number
2. Introduce yourself and mention you want to speak with BosonAI
3. Bot should forward the call to BosonAI's number

### Test Spam Detection

1. Call your Twilio number
2. Mention something like "warranty", "IRS", "Microsoft support", etc.
3. Bot should end the call

## Troubleshooting

### Call Not Forwarding

- ✅ Check `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` are set correctly
- ✅ Verify `BOSONAI_PHONE_NUMBER` is in E.164 format (+1234567890)
- ✅ Check Twilio account has sufficient balance
- ✅ Review server logs for error messages

### Call Not Ending

- ✅ Same credentials check as above
- ✅ Ensure bot is properly detecting spam (check conversation history in logs)

## API Details

### Twilio API Calls

**Forward Call:**

```python
POST https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Calls/{CallSid}.json
Body: Twiml=<Response><Say>Connecting you to BosonAI now.</Say><Dial>+1234567890</Dial></Response>
```

**End Call:**

```python
POST https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Calls/{CallSid}.json
Body: Status=completed
```
