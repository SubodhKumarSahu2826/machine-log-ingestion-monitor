import enum


class ScenarioType(str, enum.Enum):
    """Supported simulator execution scenarios and placeholders."""
    NORMAL = "NORMAL"
    SILENT = "SILENT"
    # Placeholder failure scenarios for later phases
    NETWORK_FAILURE = "NETWORK_FAILURE"
    CONNECTOR_FAILURE = "CONNECTOR_FAILURE"
    PARSER_FAILURE = "PARSER_FAILURE"
    RECOVER_AFTER_RETRY = "RECOVER_AFTER_RETRY"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"
