import { Voicemail } from ".";

export const voicemails: Voicemail[] = [
  { id: "1",  number: "+1234567890", name: "Alice",   description: "Call about project update", spam: false, date: new Date("2025-10-15T09:30:00Z"), unread: true,  recording: "1.wav" },
  { id: "2",  number: "+1987654321", name: "Bob",     description: "Missed client call", spam: true,  date: new Date("2025-10-23T16:45:00Z"), unread: true,  recording: "2.wav" },
  { id: "3",  number: "+1123456789", name: "Charlie", description: "Follow-up meeting reminder", spam: false, date: new Date("2025-10-10T14:10:00Z"), unread: false, recording: "3.wav" },
  { id: "4",  number: "+14165557777", name: "Diana",  description: "Reminder about tomorrow’s appointment", spam: false, date: new Date("2025-10-22T11:05:00Z"), unread: false, recording: "4.wav" },
  { id: "5",  number: "+16045558888", name: "Eve",    description: "Unrecognized number offering insurance", spam: true,  date: new Date("2025-10-19T10:30:00Z"), unread: true,  recording: "5.wav" },
  { id: "6",  number: "+17789990000", name: "Frank",  description: "Customer inquiry about billing", spam: false, date: new Date("2025-10-25T17:40:00Z"), unread: false, recording: "6.wav" },
  { id: "7",  number: "+12123334444", name: "Grace",  description: "Voicemail from HR regarding interview", spam: false, date: new Date("2025-10-13T09:15:00Z"), unread: true,  recording: "7.wav" },
  { id: "8",  number: "+13015556666", name: "Hank",   description: "Missed delivery call", spam: false, date: new Date("2025-10-24T08:00:00Z"), unread: false, recording: "8.wav" },
  { id: "9",  number: "+15195557777", name: "Ivy",    description: "Feedback about your service", spam: false, date: new Date("2025-10-18T19:25:00Z"), unread: false, recording: "9.wav" },
  { id: "10", number: "+17801234567", name: "Jack",   description: "Offer for limited-time promotion", spam: true,  date: new Date("2025-10-14T12:30:00Z"), unread: true,  recording: "10.wav" },
  { id: "11", number: "+1234567890",  name: "Alice",  description: "Update on project timeline", spam: false, date: new Date("2025-10-22T09:00:00Z"), unread: false, recording: "11.wav" },
  { id: "12", number: "+1987654321",  name: "Bob",    description: "Client follow-up call regarding invoice", spam: false, date: new Date("2025-10-11T18:40:00Z"), unread: false, recording: "12.wav" },
  { id: "13", number: "+1234567890",  name: "Alice",  description: "Quick check-in before meeting", spam: false, date: new Date("2025-10-25T08:10:00Z"), unread: true,  recording: "13.wav" },
  { id: "14", number: "+17801234567", name: "Jack",   description: "Spam call offering vacation packages", spam: true,  date: new Date("2025-10-12T21:55:00Z"), unread: true,  recording: "14.wav" },
  { id: "15", number: "+16045558888", name: "Eve",    description: "Suspicious car warranty message", spam: true,  date: new Date("2025-10-23T19:05:00Z"), unread: false, recording: "15.wav" },
  { id: "16", number: "+1123456789",  name: "Charlie", description: "Rescheduling team sync", spam: false, date: new Date("2025-10-17T13:25:00Z"), unread: false, recording: "16.wav" },
  { id: "17", number: "+17789990000", name: "Frank",  description: "Billing issue resolved confirmation", spam: false, date: new Date("2025-10-20T16:15:00Z"), unread: false, recording: "17.wav" },
  { id: "18", number: "+12123334444", name: "Grace",  description: "Follow-up about onboarding documents", spam: false, date: new Date("2025-10-19T09:45:00Z"), unread: true,  recording: "18.wav" },
  { id: "19", number: "+14165557777", name: "Diana",  description: "Check-in about medical report", spam: false, date: new Date("2025-10-21T15:55:00Z"), unread: false, recording: "19.wav" },
  { id: "20", number: "+13015556666", name: "Hank",   description: "Delivery successfully completed", spam: false, date: new Date("2025-10-09T08:20:00Z"), unread: false, recording: "20.wav" },
];
