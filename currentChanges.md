# ShelfSense Current Changes

## Current Task: Per-Item Custom Notification Timings & Demo-Day Guardrail
- **Goal**: Enable users to configure custom expiration notification timings per item (e.g., 1d, 2d, 3d, 5d, 7d, 14d prior), with default mechanism (2d prior) for uncustomized items.
- **Demo-Day Guardrail**: Included `onLongClick` developer trigger on the notification timing header/chips to bypass WorkManager/Doze mode and fire an instant live notification to the tray for evaluation panels.
- **Plan**: Detailed in `custom_notification_timings_plan.md`.
- **Status**: Planning complete with Demo-Day guardrail, ready for execution upon user approval.
