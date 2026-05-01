export const captureChecklist = `CAPTURE CHECKLIST\n\nLoop: Plan -> Search -> Act -> Capture -> Review -> Resurface\n\nBEFORE WORK\n- Define goal, metric, and timebox.\n- Run hybrid search for 3-7 hits; extract one checklist and one pitfall.\n\nDURING WORK\n- Predict the outcome; note assumptions and anomalies quickly.\n- Promote successful sequences into a reusable checklist.\n\nAFTER WORK\n- Score priority (recurrence + cost + novelty + risk).\n- Store one atomic memory with tags, refs, and next_review_at.\n- Add a single next action for resurfacing.\n\nQUALITY GATES\n- Lead with the takeaway; keep entries dense and verifiable.\n- Only capture if actionable in 60 seconds and not a duplicate.\n`;

export const captureChecklistHeading = "CAPTURE CHECKLIST";

export const getCaptureChecklist = (): string => captureChecklist;
