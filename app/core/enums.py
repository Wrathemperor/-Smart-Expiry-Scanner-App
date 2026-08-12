from enum import Enum

class ScanStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RESCAN_REQUEST = "RESCAN_REQUEST"

class HistoryAction(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    APPROVE = "APPROVE"
    REJECTED = "REJECTED"
    RESCAN_REQUEST = "RESCAN_REQUEST"

class NotificationType(str,Enum):
    EXPIRY="EXPIRY"
    SCAN="SCAN"
    SYSTEM="SYSTEM"
    PI_STATUS="PI_STATUS"