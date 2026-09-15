# ShelfSense Current Changes

## Completed Bugfix: Duplicate Inventory Entries on Scan Approval
- **Status**: Fixed, compiled (`BUILD SUCCESSFUL in 1m 29s`), and committed to git (`d331535`).
- **Resolution**:
  - Removed duplicate `productRepository.addProduct(product)` from `ScanViewModel.approveScan()`.
  - Single database insertion and provenance tracking is now reliably handled by `AppEventProcessor.onScanApproved()`.
