"""
Simple Google Calendar Integration

Three functions:
1. get_current_event() - Returns string describing current event (or empty if none)
2. get_next_available_slot() - Returns string describing next available time slot
3. book_next_available() - Books a 15-min meeting at next opening, returns confirmation
"""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Get authenticated Google Calendar service."""
    creds = None
    token_file = Path(__file__).parent / 'token.json'
    creds_file = Path(__file__).parent / 'google-calendar-credentials.json'
    
    # Load existing token
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    
    # Refresh or create new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    
    return build('calendar', 'v3', credentials=creds)


def get_current_event() -> str:
    """
    Check if there's a current event happening now.
    
    Returns:
        str: Description of current event, or empty string if none
        Example: "Team Meeting (until 3:30 PM)"
                 "Client Call with John Doe (until 4:00 PM)"
                 "" (if no current event)
    """
    try:
        service = get_calendar_service()
        now = datetime.now()
        
        # Get events happening right now
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat() + 'Z',
            timeMax=(now + timedelta(minutes=1)).isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return "No current events"
        
        # Get the first current event
        event = events[0]
        title = event.get('summary', 'Busy')
        
        # Parse end time
        end_str = event['end'].get('dateTime', event['end'].get('date'))
        if 'T' in end_str:
            end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            end_formatted = end_time.strftime('%I:%M %p').lstrip('0')
            return f"{title} (until {end_formatted})"
        else:
            return f"{title} (all day event)"
            
    except Exception as e:
        return f"Error checking calendar: {e}"


def get_next_available_slot(duration_minutes: int = 30, days_ahead: int = 5) -> str:
    """
    Find the next available time slot during work hours (9 AM - 5 PM, Mon-Fri).
    
    Args:
        duration_minutes: Length of desired slot (default: 30 minutes)
        days_ahead: How many days to search (default: 5 days)
    
    Returns:
        str: Description of next available slot
        Example: "Tomorrow at 2:00 PM"
                 "Monday at 10:30 AM"
                 "Today at 4:00 PM"
                 "No available slots this week"
    """
    try:
        service = get_calendar_service()
        now = datetime.now()
        
        # Start searching from next hour
        search_start = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        # Search through each day
        for day_offset in range(days_ahead):
            check_date = search_start + timedelta(days=day_offset)
            
            # Skip weekends
            if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                continue
            
            # Set to 9 AM for this day (or current time if today)
            if day_offset == 0:
                start_of_day = search_start
            else:
                start_of_day = check_date.replace(hour=9, minute=0, second=0, microsecond=0)
            
            # End at 5 PM
            end_of_day = check_date.replace(hour=17, minute=0, second=0, microsecond=0)
            
            # Get all events for this day
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Create list of busy times
            busy_times = []
            for event in events:
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                end_str = event['end'].get('dateTime', event['end'].get('date'))
                
                if 'T' in start_str:  # Not an all-day event
                    event_start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    event_end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    busy_times.append((event_start, event_end))
            
            # Check each 30-minute slot
            current_slot = start_of_day
            while current_slot + timedelta(minutes=duration_minutes) <= end_of_day:
                slot_end = current_slot + timedelta(minutes=duration_minutes)
                
                # Check if this slot conflicts with any event
                is_free = True
                for busy_start, busy_end in busy_times:
                    # Check for overlap
                    if (current_slot < busy_end and slot_end > busy_start):
                        is_free = False
                        break
                
                if is_free:
                    # Found an available slot!
                    time_str = current_slot.strftime('%I:%M %p').lstrip('0')
                    
                    # Format day description
                    if day_offset == 0:
                        day_desc = "Today"
                    elif day_offset == 1:
                        day_desc = "Tomorrow"
                    else:
                        day_desc = current_slot.strftime('%A')  # Monday, Tuesday, etc.
                    
                    return f"{day_desc} at {time_str}"
                
                # Move to next slot
                current_slot += timedelta(minutes=30)
        
        return "No available slots in the next 5 business days"
        
    except Exception as e:
        return f"Error checking calendar: {e}"


def book_next_available(caller_name: str, caller_phone: str = "", caller_email: str = "") -> str:
    """
    Book a 15-minute meeting at the next available time slot.
    
    Args:
        caller_name: Name of the person requesting the meeting
        caller_phone: Phone number (optional)
        caller_email: Email address (optional, will be added as attendee if provided)
    
    Returns:
        str: Confirmation message with booking details
        Example: "Booked for Tomorrow at 2:00 PM"
                 "Booked for Monday at 10:30 AM"
                 "Unable to book - no available slots"
    """
    try:
        service = get_calendar_service()
        now = datetime.now()
        
        # Start searching from next hour
        search_start = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        # Search through each day (up to 5 days)
        for day_offset in range(5):
            check_date = search_start + timedelta(days=day_offset)
            
            # Skip weekends
            if check_date.weekday() >= 5:
                continue
            
            # Set to 9 AM for this day (or current time if today)
            if day_offset == 0:
                start_of_day = search_start
            else:
                start_of_day = check_date.replace(hour=9, minute=0, second=0, microsecond=0)
            
            # End at 5 PM
            end_of_day = check_date.replace(hour=17, minute=0, second=0, microsecond=0)
            
            # Get all events for this day
            events_result = service.events().list(
                calendarId='primary',
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Create list of busy times
            busy_times = []
            for event in events:
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                end_str = event['end'].get('dateTime', event['end'].get('date'))
                
                if 'T' in start_str:
                    event_start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    event_end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    busy_times.append((event_start, event_end))
            
            # Check each 30-minute slot for a 15-minute opening
            current_slot = start_of_day
            while current_slot + timedelta(minutes=15) <= end_of_day:
                slot_end = current_slot + timedelta(minutes=15)
                
                # Check if this slot conflicts with any event
                is_free = True
                for busy_start, busy_end in busy_times:
                    if (current_slot < busy_end and slot_end > busy_start):
                        is_free = False
                        break
                
                if is_free:
                    # Found an available slot - book it!
                    event_body = {
                        'summary': f'Meeting with {caller_name}',
                        'description': f'Phone: {caller_phone}\nScheduled via AI Receptionist',
                        'start': {
                            'dateTime': current_slot.isoformat(),
                            'timeZone': 'America/New_York',
                        },
                        'end': {
                            'dateTime': slot_end.isoformat(),
                            'timeZone': 'America/New_York',
                        },
                    }
                    
                    # Add attendee if email provided
                    if caller_email:
                        event_body['attendees'] = [{'email': caller_email}]
                    
                    # Create the event
                    created_event = service.events().insert(
                        calendarId='primary',
                        body=event_body,
                        sendUpdates='all' if caller_email else 'none'
                    ).execute()
                    
                    # Format confirmation message
                    time_str = current_slot.strftime('%I:%M %p').lstrip('0')
                    
                    if day_offset == 0:
                        day_desc = "Today"
                    elif day_offset == 1:
                        day_desc = "Tomorrow"
                    else:
                        day_desc = current_slot.strftime('%A')
                    
                    return f"Booked for {day_desc} at {time_str}"
                
                # Move to next slot
                current_slot += timedelta(minutes=30)
        
        return "Unable to book - no available slots in the next 5 business days"
        
    except Exception as e:
        return f"Error booking meeting: {e}"


# Test functions when run directly
if __name__ == '__main__':
    print("\n" + "="*60)
    print("CALENDAR CHECK")
    print("="*60 + "\n")
    
    # Test 1: Current event
    print("Current Event:")
    current = get_current_event()
    if current:
        print(f"  ✅ {current}")
    else:
        print("  📭 No current event")
    
    print()
    
    # Test 2: Next available slot
    print("Next Available Slot:")
    next_slot = get_next_available_slot(duration_minutes=30)
    print(f"  🕐 {next_slot}")
    
    print()
    
    # Test 3: Book next available (commented out to avoid accidentally booking)
    print("Book Next Available:")
    print("  ⚠️  Uncomment the line below to test booking")
    # result = book_next_available("Test Caller", "+1234567890", "test@example.com")
    # print(f"  📅 {result}")
    
    print("\n" + "="*60 + "\n")
