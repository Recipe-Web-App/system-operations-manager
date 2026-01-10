"""Kong Konnect API client."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from system_operations_manager.integrations.konnect.exceptions import (
    KonnectAPIError,
    KonnectAuthError,
    KonnectConnectionError,
    KonnectNotFoundError,
)
from system_operations_manager.integrations.konnect.models import (
    ControlPlane,
    ControlPlaneListResponse,
    DataPlaneCertificate,
)

if TYPE_CHECKING:
    from system_operations_manager.integrations.konnect.config import KonnectConfig

logger = structlog.get_logger()


class KonnectClient:
    """HTTP client for Kong Konnect API.

    This client provides methods to interact with the Konnect API for
    managing control planes and data plane certificates.

    Example:
        ```python
        from system_operations_manager.integrations.konnect import (
            KonnectClient,
            KonnectConfig,
        )

        config = KonnectConfig.load()
        with KonnectClient(config) as client:
            control_planes = client.list_control_planes()
            for cp in control_planes:
                print(cp.name)
        ```
    """

    def __init__(self, config: KonnectConfig) -> None:
        """Initialize Konnect client.

        Args:
            config: Konnect configuration with token and region.
        """
        self.config = config
        self._client = httpx.Client(
            base_url=config.api_url,
            timeout=httpx.Timeout(30.0),
            headers={
                "Authorization": f"Bearer {config.token.get_secret_value()}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        logger.info(
            "Konnect client initialized",
            region=config.region.value,
            api_url=config.api_url,
        )

    def __enter__(self) -> KonnectClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    @staticmethod
    def _is_uuid(value: str) -> bool:
        """Check if a string looks like a UUID.

        Args:
            value: String to check.

        Returns:
            True if the string matches UUID format.
        """
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        return bool(uuid_pattern.match(value))

    @retry(
        retry=retry_if_exception_type(KonnectConnectionError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an HTTP request to Konnect API.

        Args:
            method: HTTP method.
            endpoint: API endpoint.
            **kwargs: Additional arguments for httpx.

        Returns:
            Response JSON data.

        Raises:
            KonnectConnectionError: On connection failure.
            KonnectAuthError: On authentication failure.
            KonnectNotFoundError: On 404 response.
            KonnectAPIError: On other API errors.
        """
        try:
            response = self._client.request(method, endpoint, **kwargs)
        except httpx.ConnectError as e:
            logger.error(
                "Konnect connection error",
                endpoint=endpoint,
                error=str(e),
            )
            raise KonnectConnectionError(
                f"Failed to connect to Konnect API: {e}",
                details=str(e),
            ) from e
        except httpx.TimeoutException as e:
            logger.error(
                "Konnect timeout",
                endpoint=endpoint,
                error=str(e),
            )
            raise KonnectConnectionError(
                "Request to Konnect API timed out",
                details=str(e),
            ) from e

        # Handle errors
        if response.status_code == 401:
            raise KonnectAuthError(
                "Invalid Konnect API token",
                details="Check your token and try 'ops kong konnect login' again",
            )
        if response.status_code == 403:
            raise KonnectAuthError(
                "Access denied",
                details="Your token may not have sufficient permissions",
            )
        if response.status_code == 404:
            raise KonnectNotFoundError(
                "Resource not found",
                status_code=404,
            )
        if response.status_code >= 400:
            try:
                error_data = response.json()
                message = error_data.get("message", response.text)
            except Exception:
                message = response.text
            raise KonnectAPIError(
                f"Konnect API error: {message}",
                status_code=response.status_code,
                details=response.text,
            )

        # Return JSON for successful responses
        if response.status_code == 204:
            return {}
        return response.json()  # type: ignore[no-any-return]

    def validate_token(self) -> bool:
        """Validate the API token by making a test request.

        Returns:
            True if token is valid.

        Raises:
            KonnectAuthError: If token is invalid.
        """
        try:
            # List control planes as a validation check
            self._request("GET", "/v2/control-planes", params={"page[size]": 1})
            return True
        except KonnectAuthError:
            raise
        except KonnectAPIError:
            # Other API errors mean the token worked but something else failed
            return True

    def list_control_planes(self) -> list[ControlPlane]:
        """List all control planes.

        Returns:
            List of control planes.
        """
        logger.debug("Listing control planes")
        data = self._request("GET", "/v2/control-planes")
        response = ControlPlaneListResponse.from_api_response(data)
        logger.info("Listed control planes", count=len(response.data))
        return response.data

    def get_control_plane(self, control_plane_id: str) -> ControlPlane:
        """Get a control plane by ID.

        Args:
            control_plane_id: Control plane ID.

        Returns:
            Control plane details.
        """
        logger.debug("Getting control plane", id=control_plane_id)
        data = self._request("GET", f"/v2/control-planes/{control_plane_id}")
        return ControlPlane.from_api_response(data)

    def get_control_plane_by_name(self, name: str) -> ControlPlane | None:
        """Get a control plane by name.

        Args:
            name: Control plane name.

        Returns:
            Control plane if found, None otherwise.
        """
        control_planes = self.list_control_planes()
        for cp in control_planes:
            if cp.name == name:
                return cp
        return None

    def find_control_plane(self, name_or_id: str) -> ControlPlane:
        """Find a control plane by name or ID.

        Args:
            name_or_id: Control plane name or ID.

        Returns:
            Control plane.

        Raises:
            KonnectNotFoundError: If control plane not found.
        """
        # Try by ID first if it looks like a UUID
        if self._is_uuid(name_or_id):
            try:
                return self.get_control_plane(name_or_id)
            except KonnectNotFoundError:
                pass

        # Try by name
        cp = self.get_control_plane_by_name(name_or_id)
        if cp:
            return cp

        raise KonnectNotFoundError(
            f"Control plane '{name_or_id}' not found",
            status_code=404,
            details="Check the control plane name or ID and try again",
        )

    def list_dp_certificates(self, control_plane_id: str) -> list[DataPlaneCertificate]:
        """List data plane certificates for a control plane.

        Args:
            control_plane_id: Control plane ID.

        Returns:
            List of certificates.
        """
        logger.debug("Listing DP certificates", control_plane_id=control_plane_id)
        data = self._request("GET", f"/v2/control-planes/{control_plane_id}/dp-client-certificates")
        certs = [DataPlaneCertificate.from_api_response(cert) for cert in data.get("data", [])]
        logger.info("Listed DP certificates", count=len(certs))
        return certs

    def create_dp_certificate(self, control_plane_id: str) -> DataPlaneCertificate:
        """Create a new data plane certificate.

        Generates a self-signed certificate locally and registers it with Konnect.

        Args:
            control_plane_id: Control plane ID.

        Returns:
            Created certificate with cert and key.
        """
        logger.info("Creating DP certificate", control_plane_id=control_plane_id)

        # Generate certificate and key
        cert_pem, key_pem = self._generate_certificate()

        # Register certificate with Konnect
        data = self._request(
            "POST",
            f"/v2/control-planes/{control_plane_id}/dp-client-certificates",
            json={"cert": cert_pem},
        )

        # Return certificate with both cert and key
        cert = DataPlaneCertificate.from_api_response(data)
        # Add the private key (not returned by API, we generated it locally)
        cert.key = key_pem
        logger.info("Created DP certificate", id=cert.id)
        return cert

    @staticmethod
    def _generate_certificate() -> tuple[str, str]:
        """Generate a self-signed certificate for data plane authentication.

        Returns:
            Tuple of (certificate_pem, private_key_pem).
        """
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.x509.oid import NameOID
        except ImportError as e:
            raise RuntimeError(
                "cryptography package not installed. Install with: pip install cryptography"
            ) from e

        import datetime

        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Create self-signed certificate
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, "kong-dp"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Kong Data Plane"),
            ]
        )

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.UTC))
            .not_valid_after(
                datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365 * 10)
            )
            .sign(private_key, hashes.SHA256())
        )

        # Serialize to PEM format
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        return cert_pem, key_pem

    def get_dp_certificate(
        self, control_plane_id: str, certificate_id: str
    ) -> DataPlaneCertificate:
        """Get a specific data plane certificate.

        Args:
            control_plane_id: Control plane ID.
            certificate_id: Certificate ID.

        Returns:
            Certificate details.
        """
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/dp-client-certificates/{certificate_id}",
        )
        return DataPlaneCertificate.from_api_response(data)
