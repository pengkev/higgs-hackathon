from datetime import datetime
from db_actions import Voicemail
voicemails: list[Voicemail] = [
    Voicemail(1,  "+1234567890", "Alice",   "Call about project update", False, datetime.fromisoformat("2025-10-15T09:30:00+00:00"), True,  "call1.wav"),
    Voicemail(2,  "+1987654321", "Bob",     "Missed client call", True,  datetime.fromisoformat("2025-10-23T16:45:00+00:00"), True,  "call1.wav"),
    Voicemail(3,  "+1123456789", "Charlie", "Follow-up meeting reminder", False, datetime.fromisoformat("2025-10-10T14:10:00+00:00"), False, "call1.wav"),
    Voicemail(4,  "+14165557777", "Diana",  "Reminder about tomorrow’s appointment", False, datetime.fromisoformat("2025-10-22T11:05:00+00:00"), False, "call1.wav"),
    Voicemail(5,  "+16045558888", "Eve",    "Unrecognized number offering insurance", True, datetime.fromisoformat("2025-10-19T10:30:00+00:00"), True, "call1.wav"),
    Voicemail(6,  "+17789990000", "Frank",  "Customer inquiry about billing", False, datetime.fromisoformat("2025-10-25T17:40:00+00:00"), False, "call1.wav"),
    Voicemail(7,  "+12123334444", "Grace",  "Voicemail from HR regarding interview", False, datetime.fromisoformat("2025-10-13T09:15:00+00:00"), True, "call1.wav"),
    Voicemail(8,  "+13015556666", "Hank",   "Missed delivery call", False, datetime.fromisoformat("2025-10-24T08:00:00+00:00"), False, "call1.wav"),
    Voicemail(9,  "+15195557777", "Ivy",    "Feedback about your service", False, datetime.fromisoformat("2025-10-18T19:25:00+00:00"), False, "call1.wav"),
    Voicemail(10, "+17801234567", "Jack",   "Offer for limited-time promotion", True, datetime.fromisoformat("2025-10-14T12:30:00+00:00"), True, "call1.wav"),
    Voicemail(11, "+1234567890",  "Alice",  "Update on project timeline", False, datetime.fromisoformat("2025-10-22T09:00:00+00:00"), False, "call1.wav"),
    Voicemail(12, "+1987654321",  "Bob",    "Client follow-up call regarding invoice", False, datetime.fromisoformat("2025-10-11T18:40:00+00:00"), False, "call1.wav"),
    Voicemail(13, "+1234567890",  "Alice",  "Quick check-in before meeting", False, datetime.fromisoformat("2025-10-25T08:10:00+00:00"), True, "call1.wav"),
    Voicemail(14, "+17801234567", "Jack",   "Spam call offering vacation packages", True, datetime.fromisoformat("2025-10-12T21:55:00+00:00"), True, "call1.wav"),
    Voicemail(15, "+16045558888", "Eve",    "Suspicious car warranty message", True, datetime.fromisoformat("2025-10-23T19:05:00+00:00"), False, "call1.wav"),
    Voicemail(16, "+1123456789",  "Charlie","Rescheduling team sync", False, datetime.fromisoformat("2025-10-17T13:25:00+00:00"), False, "call1.wav"),
    Voicemail(17, "+17789990000", "Frank",  "Billing issue resolved confirmation", False, datetime.fromisoformat("2025-10-20T16:15:00+00:00"), False, "call1.wav"),
    Voicemail(18, "+12123334444", "Grace",  "Follow-up about onboarding documents", False, datetime.fromisoformat("2025-10-19T09:45:00+00:00"), True, "call1.wav"),
    Voicemail(19, "+14165557777", "Diana",  "Check-in about medical report", False, datetime.fromisoformat("2025-10-21T15:55:00+00:00"), False, "call1.wav"),
    Voicemail(20, "+13015556666", "Hank",   "Delivery successfully completed", False, datetime.fromisoformat("2025-10-09T08:20:00+00:00"), False, "call1.wav"),
]
