# ShelfSense Current Changes

## Completed Feature: Per-Item Custom Notification Timings & Demo-Day Guardrail
- **Status**: Completed, verified with Gradle (`BUILD SUCCESSFUL in 50s`), and committed to git (`07f1f53`).
- **Key Deliverables**:
  - `customAlertDaysBefore: Int?` added to `Product` and `ScanResult` entities.
  - Room database upgraded to v4 (`AppDatabase.kt`).
  - `NotificationHelper.kt` created for Android O+ notifications and instant Demo-Day developer test triggers.
  - `ExpiryLogic.kt` & `ExpiryAlertWorker.kt` updated for custom threshold vs default 2-day reminder window.
  - `ProductDetailDialog.kt` equipped with interactive timing selector chips and `onLongClick` live tray notification trigger.
  - `InventoryScreen.kt` updated with notification timing picker in `AddEditProductDialog` and `🔔 {X}D ALERT` badges on `InventoryProductCard`.
