"""Factory functions for creating an instance of the client."""
from .mode_2_client import Mode2Client
from ..util import LoginCredentials


def create_mode_2_client(
        host: str, port: int, username: str | None = None, password: str | None = None
) -> Mode2Client:
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
    return Mode2Client(host, port, creds)
