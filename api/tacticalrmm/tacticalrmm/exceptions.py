class NatsDown(Exception):
    """
    Raised when a connection to NATS cannot be established.
    """

    def __str__(self) -> str:
        return "Unable to connect to NATS"
