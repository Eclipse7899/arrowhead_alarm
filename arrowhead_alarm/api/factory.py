"""Factory functions for creating an instance of the client."""
from arrowhead_alarm.api.eci_client import EciClient
from arrowhead_alarm.types import LoginCredentials


def create_eci_tcp_client(
        host: str, port: int, username: str | None = None, password: str | None = None
) -> EciClient:
    """Create an EciClient instance.

    Args:
        host: Hostname or IP address of the Arrowhead alarm panel.
        port: TCP port number of the Arrowhead alarm panel.
        username: Username for authentication.
        password: Password for authentication.

    Returns:
        An instance of EciClient.

    """
    if username and password:
        creds = LoginCredentials(username, password)
    else:
        creds = None
    return EciClient(host, port, creds)
