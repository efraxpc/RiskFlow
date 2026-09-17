"""Closed vocabularies shared by the RiskFlow domain."""

from enum import StrEnum


class WorkflowState(StrEnum):
    """Every durable state available to the workflow."""

    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    RISK_ASSESSED = "RISK_ASSESSED"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    INVENTORY_RESERVED = "INVENTORY_RESERVED"
    PAYMENT_COMPLETED = "PAYMENT_COMPLETED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    COMPENSATED = "COMPENSATED"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendedAction(StrEnum):
    AUTO_APPROVE = "auto_approve"
    HUMAN_REVIEW = "human_review"
    PRIORITY_REVIEW = "priority_review"


class OrderScenario(StrEnum):
    NORMAL = "normal"
    SUSPICIOUS = "suspicious"
    CRITICAL = "critical"
    PAYMENT_FAILURE = "payment_failure"
    REPEATED_RETRY = "repeated_retry"


class RiskSignalCode(StrEnum):
    NEW_ACCOUNT = "NEW_ACCOUNT"
    ADDRESS_MISMATCH = "ADDRESS_MISMATCH"
    HIGH_ORDER_VALUE = "HIGH_ORDER_VALUE"
    HIGH_VELOCITY = "HIGH_VELOCITY"
    REGION_MISMATCH = "REGION_MISMATCH"
    EXPEDITED_SHIPPING = "EXPEDITED_SHIPPING"
