"""Custom package exceptions."""

# standard library
from pathlib import Path


class ServiceFileNotFound(FileNotFoundError):
    """When a service file can't be found."""

    def __init__(
        self,
        pg_service_filepath: Path,
    ):
        """Initialization.

        Args:
            pg_service_filepath: path to the examined pg service file
        """
        self.message = f"Service '{pg_service_filepath}' has not been found."

        super().__init__(self.message)


class ServiceNotFound(KeyError):
    """When a service name is not found in service file sections."""

    def __init__(
        self,
        service_name: str,
        existing_service_names: list[str],
        pg_service_filepath: Path,
    ):
        """Initialization.

        Args:
            service_name: unfound service name
            existing_service_names: avaibale service names
            pg_service_filepath: path to the examined pg service file
        """
        self.message = (
            f"Service '{service_name}' has not been found in PG service file "
            f"({pg_service_filepath}). Available names: {', '.join(existing_service_names)}"
        )

        super().__init__(self.message)
