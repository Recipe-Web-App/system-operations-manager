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

from system_operations_manager.integrations.kong.models.certificate import (
    SNI,
    CACertificate,
    Certificate,
)
from system_operations_manager.integrations.kong.models.consumer import Consumer
from system_operations_manager.integrations.kong.models.enterprise import Vault
from system_operations_manager.integrations.kong.models.key import Key, KeySet
from system_operations_manager.integrations.kong.models.plugin import KongPluginEntity
from system_operations_manager.integrations.kong.models.route import Route
from system_operations_manager.integrations.kong.models.service import Service
from system_operations_manager.integrations.kong.models.upstream import Target, Upstream

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

    # =========================================================================
    # Service Management (Control Plane Admin API)
    # =========================================================================

    def list_services(
        self,
        control_plane_id: str,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[Service], str | None]:
        """List all services in a control plane.

        Args:
            control_plane_id: Control plane ID.
            tags: Filter by tags.
            limit: Maximum number of services to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of services, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        logger.debug("Listing Konnect services", control_plane_id=control_plane_id)
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/services",
            params=params,
        )
        services = [Service.model_validate(item) for item in data.get("data", [])]
        next_offset = data.get("offset")
        logger.info("Listed Konnect services", count=len(services))
        return services, next_offset

    def get_service(
        self,
        control_plane_id: str,
        service_id_or_name: str,
    ) -> Service:
        """Get a service from a control plane.

        Args:
            control_plane_id: Control plane ID.
            service_id_or_name: Service ID or name.

        Returns:
            Service details.

        Raises:
            KonnectNotFoundError: If service not found.
        """
        logger.debug(
            "Getting Konnect service",
            control_plane_id=control_plane_id,
            service=service_id_or_name,
        )
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/services/{service_id_or_name}",
        )
        return Service.model_validate(data)

    def create_service(
        self,
        control_plane_id: str,
        service: Service,
    ) -> Service:
        """Create a service in a control plane.

        Args:
            control_plane_id: Control plane ID.
            service: Service to create.

        Returns:
            Created service with ID and timestamps.
        """
        payload = service.to_create_payload()
        logger.debug(
            "Creating Konnect service",
            control_plane_id=control_plane_id,
            name=service.name,
        )
        data = self._request(
            "POST",
            f"/v2/control-planes/{control_plane_id}/core-entities/services",
            json=payload,
        )
        created = Service.model_validate(data)
        logger.info("Created Konnect service", name=created.name, id=created.id)
        return created

    def update_service(
        self,
        control_plane_id: str,
        service_id_or_name: str,
        service: Service,
    ) -> Service:
        """Update a service in a control plane.

        Args:
            control_plane_id: Control plane ID.
            service_id_or_name: Service ID or name to update.
            service: Updated service data.

        Returns:
            Updated service.
        """
        payload = service.to_create_payload()
        logger.debug(
            "Updating Konnect service",
            control_plane_id=control_plane_id,
            service=service_id_or_name,
        )
        data = self._request(
            "PATCH",
            f"/v2/control-planes/{control_plane_id}/core-entities/services/{service_id_or_name}",
            json=payload,
        )
        updated = Service.model_validate(data)
        logger.info("Updated Konnect service", name=updated.name, id=updated.id)
        return updated

    def delete_service(
        self,
        control_plane_id: str,
        service_id_or_name: str,
    ) -> None:
        """Delete a service from a control plane.

        Args:
            control_plane_id: Control plane ID.
            service_id_or_name: Service ID or name to delete.
        """
        logger.debug(
            "Deleting Konnect service",
            control_plane_id=control_plane_id,
            service=service_id_or_name,
        )
        self._request(
            "DELETE",
            f"/v2/control-planes/{control_plane_id}/core-entities/services/{service_id_or_name}",
        )
        logger.info("Deleted Konnect service", service=service_id_or_name)

    # =========================================================================
    # Route Management (Control Plane Admin API)
    # =========================================================================

    def list_routes(
        self,
        control_plane_id: str,
        *,
        service_name_or_id: str | None = None,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[Route], str | None]:
        """List routes in a control plane.

        Args:
            control_plane_id: Control plane ID.
            service_name_or_id: Filter by service (optional).
            tags: Filter by tags.
            limit: Maximum number of routes to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of routes, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        if service_name_or_id:
            endpoint = f"/v2/control-planes/{control_plane_id}/core-entities/services/{service_name_or_id}/routes"
        else:
            endpoint = f"/v2/control-planes/{control_plane_id}/core-entities/routes"

        logger.debug("Listing Konnect routes", control_plane_id=control_plane_id)
        data = self._request("GET", endpoint, params=params)
        routes = [Route.model_validate(item) for item in data.get("data", [])]
        next_offset = data.get("offset")
        logger.info("Listed Konnect routes", count=len(routes))
        return routes, next_offset

    def get_route(
        self,
        control_plane_id: str,
        route_id_or_name: str,
    ) -> Route:
        """Get a route from a control plane.

        Args:
            control_plane_id: Control plane ID.
            route_id_or_name: Route ID or name.

        Returns:
            Route details.

        Raises:
            KonnectNotFoundError: If route not found.
        """
        logger.debug(
            "Getting Konnect route",
            control_plane_id=control_plane_id,
            route=route_id_or_name,
        )
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/routes/{route_id_or_name}",
        )
        return Route.model_validate(data)

    def create_route(
        self,
        control_plane_id: str,
        route: Route,
        service_name_or_id: str | None = None,
    ) -> Route:
        """Create a route in a control plane.

        Args:
            control_plane_id: Control plane ID.
            route: Route to create.
            service_name_or_id: Service to attach route to (optional, can use route.service).

        Returns:
            Created route with ID and timestamps.
        """
        payload = route.to_create_payload()

        # If service is specified as parameter, use the nested endpoint
        if service_name_or_id:
            endpoint = f"/v2/control-planes/{control_plane_id}/core-entities/services/{service_name_or_id}/routes"
        else:
            endpoint = f"/v2/control-planes/{control_plane_id}/core-entities/routes"

        logger.debug(
            "Creating Konnect route",
            control_plane_id=control_plane_id,
            name=route.name,
        )
        data = self._request("POST", endpoint, json=payload)
        created = Route.model_validate(data)
        logger.info("Created Konnect route", name=created.name, id=created.id)
        return created

    def update_route(
        self,
        control_plane_id: str,
        route_id_or_name: str,
        route: Route,
    ) -> Route:
        """Update a route in a control plane.

        Args:
            control_plane_id: Control plane ID.
            route_id_or_name: Route ID or name to update.
            route: Updated route data.

        Returns:
            Updated route.
        """
        payload = route.to_create_payload()
        logger.debug(
            "Updating Konnect route",
            control_plane_id=control_plane_id,
            route=route_id_or_name,
        )
        data = self._request(
            "PATCH",
            f"/v2/control-planes/{control_plane_id}/core-entities/routes/{route_id_or_name}",
            json=payload,
        )
        updated = Route.model_validate(data)
        logger.info("Updated Konnect route", name=updated.name, id=updated.id)
        return updated

    def delete_route(
        self,
        control_plane_id: str,
        route_id_or_name: str,
    ) -> None:
        """Delete a route from a control plane.

        Args:
            control_plane_id: Control plane ID.
            route_id_or_name: Route ID or name to delete.
        """
        logger.debug(
            "Deleting Konnect route",
            control_plane_id=control_plane_id,
            route=route_id_or_name,
        )
        self._request(
            "DELETE",
            f"/v2/control-planes/{control_plane_id}/core-entities/routes/{route_id_or_name}",
        )
        logger.info("Deleted Konnect route", route=route_id_or_name)

    # =========================================================================
    # Consumer Management (Control Plane Admin API)
    # =========================================================================

    def list_consumers(
        self,
        control_plane_id: str,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[Consumer], str | None]:
        """List all consumers in a control plane.

        Args:
            control_plane_id: Control plane ID.
            tags: Filter by tags.
            limit: Maximum number of consumers to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of consumers, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        logger.debug("Listing Konnect consumers", control_plane_id=control_plane_id)
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/consumers",
            params=params,
        )
        consumers = [Consumer.model_validate(item) for item in data.get("data", [])]
        next_offset = data.get("offset")
        logger.info("Listed Konnect consumers", count=len(consumers))
        return consumers, next_offset

    def get_consumer(
        self,
        control_plane_id: str,
        consumer_id_or_username: str,
    ) -> Consumer:
        """Get a consumer from a control plane.

        Args:
            control_plane_id: Control plane ID.
            consumer_id_or_username: Consumer ID or username.

        Returns:
            Consumer details.

        Raises:
            KonnectNotFoundError: If consumer not found.
        """
        logger.debug(
            "Getting Konnect consumer",
            control_plane_id=control_plane_id,
            consumer=consumer_id_or_username,
        )
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/consumers/{consumer_id_or_username}",
        )
        return Consumer.model_validate(data)

    def create_consumer(
        self,
        control_plane_id: str,
        consumer: Consumer,
    ) -> Consumer:
        """Create a consumer in a control plane.

        Args:
            control_plane_id: Control plane ID.
            consumer: Consumer to create.

        Returns:
            Created consumer with ID and timestamps.
        """
        payload = consumer.to_create_payload()
        logger.debug(
            "Creating Konnect consumer",
            control_plane_id=control_plane_id,
            username=consumer.username,
        )
        data = self._request(
            "POST",
            f"/v2/control-planes/{control_plane_id}/core-entities/consumers",
            json=payload,
        )
        created = Consumer.model_validate(data)
        logger.info("Created Konnect consumer", username=created.username, id=created.id)
        return created

    def update_consumer(
        self,
        control_plane_id: str,
        consumer_id_or_username: str,
        consumer: Consumer,
    ) -> Consumer:
        """Update a consumer in a control plane.

        Args:
            control_plane_id: Control plane ID.
            consumer_id_or_username: Consumer ID or username to update.
            consumer: Updated consumer data.

        Returns:
            Updated consumer.
        """
        payload = consumer.to_create_payload()
        logger.debug(
            "Updating Konnect consumer",
            control_plane_id=control_plane_id,
            consumer=consumer_id_or_username,
        )
        data = self._request(
            "PATCH",
            f"/v2/control-planes/{control_plane_id}/core-entities/consumers/{consumer_id_or_username}",
            json=payload,
        )
        updated = Consumer.model_validate(data)
        logger.info("Updated Konnect consumer", username=updated.username, id=updated.id)
        return updated

    def delete_consumer(
        self,
        control_plane_id: str,
        consumer_id_or_username: str,
    ) -> None:
        """Delete a consumer from a control plane.

        Args:
            control_plane_id: Control plane ID.
            consumer_id_or_username: Consumer ID or username to delete.
        """
        logger.debug(
            "Deleting Konnect consumer",
            control_plane_id=control_plane_id,
            consumer=consumer_id_or_username,
        )
        self._request(
            "DELETE",
            f"/v2/control-planes/{control_plane_id}/core-entities/consumers/{consumer_id_or_username}",
        )
        logger.info("Deleted Konnect consumer", consumer=consumer_id_or_username)

    # =========================================================================
    # Plugin Management (Control Plane Admin API)
    # =========================================================================

    def list_plugins(
        self,
        control_plane_id: str,
        *,
        service_name_or_id: str | None = None,
        route_name_or_id: str | None = None,
        consumer_name_or_id: str | None = None,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[KongPluginEntity], str | None]:
        """List plugins in a control plane.

        Args:
            control_plane_id: Control plane ID.
            service_name_or_id: Filter by service (optional).
            route_name_or_id: Filter by route (optional).
            consumer_name_or_id: Filter by consumer (optional).
            tags: Filter by tags.
            limit: Maximum number of plugins to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of plugins, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        # Determine endpoint based on scope filters
        if service_name_or_id:
            endpoint = f"/v2/control-planes/{control_plane_id}/core-entities/services/{service_name_or_id}/plugins"
        elif route_name_or_id:
            endpoint = f"/v2/control-planes/{control_plane_id}/core-entities/routes/{route_name_or_id}/plugins"
        elif consumer_name_or_id:
            endpoint = f"/v2/control-planes/{control_plane_id}/core-entities/consumers/{consumer_name_or_id}/plugins"
        else:
            endpoint = f"/v2/control-planes/{control_plane_id}/core-entities/plugins"

        logger.debug("Listing Konnect plugins", control_plane_id=control_plane_id)
        data = self._request("GET", endpoint, params=params)
        plugins = [KongPluginEntity.model_validate(item) for item in data.get("data", [])]
        next_offset = data.get("offset")
        logger.info("Listed Konnect plugins", count=len(plugins))
        return plugins, next_offset

    def get_plugin(
        self,
        control_plane_id: str,
        plugin_id: str,
    ) -> KongPluginEntity:
        """Get a plugin from a control plane.

        Args:
            control_plane_id: Control plane ID.
            plugin_id: Plugin ID.

        Returns:
            Plugin details.

        Raises:
            KonnectNotFoundError: If plugin not found.
        """
        logger.debug(
            "Getting Konnect plugin",
            control_plane_id=control_plane_id,
            plugin=plugin_id,
        )
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/plugins/{plugin_id}",
        )
        return KongPluginEntity.model_validate(data)

    def create_plugin(
        self,
        control_plane_id: str,
        plugin: KongPluginEntity,
    ) -> KongPluginEntity:
        """Create a plugin in a control plane.

        Args:
            control_plane_id: Control plane ID.
            plugin: Plugin to create.

        Returns:
            Created plugin with ID and timestamps.
        """
        payload = plugin.to_create_payload()
        logger.debug(
            "Creating Konnect plugin",
            control_plane_id=control_plane_id,
            name=plugin.name,
        )
        data = self._request(
            "POST",
            f"/v2/control-planes/{control_plane_id}/core-entities/plugins",
            json=payload,
        )
        created = KongPluginEntity.model_validate(data)
        logger.info("Created Konnect plugin", name=created.name, id=created.id)
        return created

    def update_plugin(
        self,
        control_plane_id: str,
        plugin_id: str,
        plugin: KongPluginEntity,
    ) -> KongPluginEntity:
        """Update a plugin in a control plane.

        Args:
            control_plane_id: Control plane ID.
            plugin_id: Plugin ID to update.
            plugin: Updated plugin data.

        Returns:
            Updated plugin.
        """
        payload = plugin.to_create_payload()
        logger.debug(
            "Updating Konnect plugin",
            control_plane_id=control_plane_id,
            plugin=plugin_id,
        )
        data = self._request(
            "PATCH",
            f"/v2/control-planes/{control_plane_id}/core-entities/plugins/{plugin_id}",
            json=payload,
        )
        updated = KongPluginEntity.model_validate(data)
        logger.info("Updated Konnect plugin", name=updated.name, id=updated.id)
        return updated

    def delete_plugin(
        self,
        control_plane_id: str,
        plugin_id: str,
    ) -> None:
        """Delete a plugin from a control plane.

        Args:
            control_plane_id: Control plane ID.
            plugin_id: Plugin ID to delete.
        """
        logger.debug(
            "Deleting Konnect plugin",
            control_plane_id=control_plane_id,
            plugin=plugin_id,
        )
        self._request(
            "DELETE",
            f"/v2/control-planes/{control_plane_id}/core-entities/plugins/{plugin_id}",
        )
        logger.info("Deleted Konnect plugin", plugin=plugin_id)

    # =========================================================================
    # Upstream Management (Control Plane Admin API)
    # =========================================================================

    def list_upstreams(
        self,
        control_plane_id: str,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[Upstream], str | None]:
        """List all upstreams in a control plane.

        Args:
            control_plane_id: Control plane ID.
            tags: Filter by tags.
            limit: Maximum number of upstreams to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of upstreams, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        logger.debug("Listing Konnect upstreams", control_plane_id=control_plane_id)
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/upstreams",
            params=params,
        )
        upstreams = [Upstream.model_validate(item) for item in data.get("data", [])]
        next_offset = data.get("offset")
        logger.info("Listed Konnect upstreams", count=len(upstreams))
        return upstreams, next_offset

    def get_upstream(
        self,
        control_plane_id: str,
        upstream_id_or_name: str,
    ) -> Upstream:
        """Get an upstream from a control plane.

        Args:
            control_plane_id: Control plane ID.
            upstream_id_or_name: Upstream ID or name.

        Returns:
            Upstream details.

        Raises:
            KonnectNotFoundError: If upstream not found.
        """
        logger.debug(
            "Getting Konnect upstream",
            control_plane_id=control_plane_id,
            upstream=upstream_id_or_name,
        )
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/upstreams/{upstream_id_or_name}",
        )
        return Upstream.model_validate(data)

    def create_upstream(
        self,
        control_plane_id: str,
        upstream: Upstream,
    ) -> Upstream:
        """Create an upstream in a control plane.

        Args:
            control_plane_id: Control plane ID.
            upstream: Upstream to create.

        Returns:
            Created upstream with ID and timestamps.
        """
        payload = upstream.to_create_payload()
        logger.debug(
            "Creating Konnect upstream",
            control_plane_id=control_plane_id,
            name=upstream.name,
        )
        data = self._request(
            "POST",
            f"/v2/control-planes/{control_plane_id}/core-entities/upstreams",
            json=payload,
        )
        created = Upstream.model_validate(data)
        logger.info("Created Konnect upstream", name=created.name, id=created.id)
        return created

    def update_upstream(
        self,
        control_plane_id: str,
        upstream_id_or_name: str,
        upstream: Upstream,
    ) -> Upstream:
        """Update an upstream in a control plane.

        Args:
            control_plane_id: Control plane ID.
            upstream_id_or_name: Upstream ID or name to update.
            upstream: Updated upstream data.

        Returns:
            Updated upstream.
        """
        payload = upstream.to_create_payload()
        logger.debug(
            "Updating Konnect upstream",
            control_plane_id=control_plane_id,
            upstream=upstream_id_or_name,
        )
        data = self._request(
            "PATCH",
            f"/v2/control-planes/{control_plane_id}/core-entities/upstreams/{upstream_id_or_name}",
            json=payload,
        )
        updated = Upstream.model_validate(data)
        logger.info("Updated Konnect upstream", name=updated.name, id=updated.id)
        return updated

    def delete_upstream(
        self,
        control_plane_id: str,
        upstream_id_or_name: str,
    ) -> None:
        """Delete an upstream from a control plane.

        Args:
            control_plane_id: Control plane ID.
            upstream_id_or_name: Upstream ID or name to delete.
        """
        logger.debug(
            "Deleting Konnect upstream",
            control_plane_id=control_plane_id,
            upstream=upstream_id_or_name,
        )
        self._request(
            "DELETE",
            f"/v2/control-planes/{control_plane_id}/core-entities/upstreams/{upstream_id_or_name}",
        )
        logger.info("Deleted Konnect upstream", upstream=upstream_id_or_name)

    # =========================================================================
    # Target Management (Control Plane Admin API)
    # =========================================================================

    def list_targets(
        self,
        control_plane_id: str,
        upstream_id_or_name: str,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[Target], str | None]:
        """List targets for an upstream in a control plane.

        Args:
            control_plane_id: Control plane ID.
            upstream_id_or_name: Upstream ID or name.
            tags: Filter by tags.
            limit: Maximum number of targets to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of targets, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        logger.debug(
            "Listing Konnect targets",
            control_plane_id=control_plane_id,
            upstream=upstream_id_or_name,
        )
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/upstreams/{upstream_id_or_name}/targets",
            params=params,
        )
        targets = [Target.model_validate(item) for item in data.get("data", [])]
        next_offset = data.get("offset")
        logger.info("Listed Konnect targets", count=len(targets))
        return targets, next_offset

    def create_target(
        self,
        control_plane_id: str,
        upstream_id_or_name: str,
        target: Target,
    ) -> Target:
        """Create a target for an upstream in a control plane.

        Args:
            control_plane_id: Control plane ID.
            upstream_id_or_name: Upstream ID or name.
            target: Target to create.

        Returns:
            Created target with ID and timestamps.
        """
        payload = target.to_create_payload()
        logger.debug(
            "Creating Konnect target",
            control_plane_id=control_plane_id,
            upstream=upstream_id_or_name,
            target=target.target,
        )
        data = self._request(
            "POST",
            f"/v2/control-planes/{control_plane_id}/core-entities/upstreams/{upstream_id_or_name}/targets",
            json=payload,
        )
        created = Target.model_validate(data)
        logger.info("Created Konnect target", target=created.target, id=created.id)
        return created

    def delete_target(
        self,
        control_plane_id: str,
        upstream_id_or_name: str,
        target_id_or_target: str,
    ) -> None:
        """Delete a target from an upstream in a control plane.

        Args:
            control_plane_id: Control plane ID.
            upstream_id_or_name: Upstream ID or name.
            target_id_or_target: Target ID or target address to delete.
        """
        logger.debug(
            "Deleting Konnect target",
            control_plane_id=control_plane_id,
            upstream=upstream_id_or_name,
            target=target_id_or_target,
        )
        self._request(
            "DELETE",
            f"/v2/control-planes/{control_plane_id}/core-entities/upstreams/{upstream_id_or_name}/targets/{target_id_or_target}",
        )
        logger.info("Deleted Konnect target", target=target_id_or_target)

    # =========================================================================
    # Certificate Management (Control Plane Admin API)
    # =========================================================================

    def list_certificates(
        self,
        control_plane_id: str,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[Certificate], str | None]:
        """List all certificates in a control plane.

        Args:
            control_plane_id: Control plane ID.
            tags: Filter by tags.
            limit: Maximum number of certificates to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of certificates, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        logger.debug("Listing Konnect certificates", control_plane_id=control_plane_id)
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/certificates",
            params=params,
        )
        certificates = [Certificate.model_validate(item) for item in data.get("data", [])]
        next_offset = data.get("offset")
        logger.info("Listed Konnect certificates", count=len(certificates))
        return certificates, next_offset

    def get_certificate(
        self,
        control_plane_id: str,
        certificate_id: str,
    ) -> Certificate:
        """Get a certificate from a control plane.

        Args:
            control_plane_id: Control plane ID.
            certificate_id: Certificate ID.

        Returns:
            Certificate details.

        Raises:
            KonnectNotFoundError: If certificate not found.
        """
        logger.debug(
            "Getting Konnect certificate",
            control_plane_id=control_plane_id,
            certificate=certificate_id,
        )
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/certificates/{certificate_id}",
        )
        return Certificate.model_validate(data)

    def create_certificate(
        self,
        control_plane_id: str,
        certificate: Certificate,
    ) -> Certificate:
        """Create a certificate in a control plane.

        Args:
            control_plane_id: Control plane ID.
            certificate: Certificate to create.

        Returns:
            Created certificate with ID and timestamps.
        """
        payload = certificate.to_create_payload()
        logger.debug(
            "Creating Konnect certificate",
            control_plane_id=control_plane_id,
        )
        data = self._request(
            "POST",
            f"/v2/control-planes/{control_plane_id}/core-entities/certificates",
            json=payload,
        )
        created = Certificate.model_validate(data)
        logger.info("Created Konnect certificate", id=created.id)
        return created

    def update_certificate(
        self,
        control_plane_id: str,
        certificate_id: str,
        certificate: Certificate,
    ) -> Certificate:
        """Update a certificate in a control plane.

        Args:
            control_plane_id: Control plane ID.
            certificate_id: Certificate ID to update.
            certificate: Updated certificate data.

        Returns:
            Updated certificate.
        """
        payload = certificate.to_create_payload()
        logger.debug(
            "Updating Konnect certificate",
            control_plane_id=control_plane_id,
            certificate=certificate_id,
        )
        data = self._request(
            "PATCH",
            f"/v2/control-planes/{control_plane_id}/core-entities/certificates/{certificate_id}",
            json=payload,
        )
        updated = Certificate.model_validate(data)
        logger.info("Updated Konnect certificate", id=updated.id)
        return updated

    def delete_certificate(
        self,
        control_plane_id: str,
        certificate_id: str,
    ) -> None:
        """Delete a certificate from a control plane.

        Args:
            control_plane_id: Control plane ID.
            certificate_id: Certificate ID to delete.
        """
        logger.debug(
            "Deleting Konnect certificate",
            control_plane_id=control_plane_id,
            certificate=certificate_id,
        )
        self._request(
            "DELETE",
            f"/v2/control-planes/{control_plane_id}/core-entities/certificates/{certificate_id}",
        )
        logger.info("Deleted Konnect certificate", certificate=certificate_id)

    # =========================================================================
    # SNI Management (Control Plane Admin API)
    # =========================================================================

    def list_snis(
        self,
        control_plane_id: str,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[SNI], str | None]:
        """List all SNIs in a control plane.

        Args:
            control_plane_id: Control plane ID.
            tags: Filter by tags.
            limit: Maximum number of SNIs to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of SNIs, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        logger.debug("Listing Konnect SNIs", control_plane_id=control_plane_id)
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/snis",
            params=params,
        )
        snis = [SNI.model_validate(item) for item in data.get("data", [])]
        next_offset = data.get("offset")
        logger.info("Listed Konnect SNIs", count=len(snis))
        return snis, next_offset

    def get_sni(
        self,
        control_plane_id: str,
        sni_id_or_name: str,
    ) -> SNI:
        """Get an SNI from a control plane.

        Args:
            control_plane_id: Control plane ID.
            sni_id_or_name: SNI ID or name.

        Returns:
            SNI details.

        Raises:
            KonnectNotFoundError: If SNI not found.
        """
        logger.debug(
            "Getting Konnect SNI",
            control_plane_id=control_plane_id,
            sni=sni_id_or_name,
        )
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/snis/{sni_id_or_name}",
        )
        return SNI.model_validate(data)

    def create_sni(
        self,
        control_plane_id: str,
        sni: SNI,
    ) -> SNI:
        """Create an SNI in a control plane.

        Args:
            control_plane_id: Control plane ID.
            sni: SNI to create.

        Returns:
            Created SNI with ID and timestamps.
        """
        payload = sni.to_create_payload()
        logger.debug(
            "Creating Konnect SNI",
            control_plane_id=control_plane_id,
            name=sni.name,
        )
        data = self._request(
            "POST",
            f"/v2/control-planes/{control_plane_id}/core-entities/snis",
            json=payload,
        )
        created = SNI.model_validate(data)
        logger.info("Created Konnect SNI", name=created.name, id=created.id)
        return created

    def update_sni(
        self,
        control_plane_id: str,
        sni_id_or_name: str,
        sni: SNI,
    ) -> SNI:
        """Update an SNI in a control plane.

        Args:
            control_plane_id: Control plane ID.
            sni_id_or_name: SNI ID or name to update.
            sni: Updated SNI data.

        Returns:
            Updated SNI.
        """
        payload = sni.to_create_payload()
        logger.debug(
            "Updating Konnect SNI",
            control_plane_id=control_plane_id,
            sni=sni_id_or_name,
        )
        data = self._request(
            "PATCH",
            f"/v2/control-planes/{control_plane_id}/core-entities/snis/{sni_id_or_name}",
            json=payload,
        )
        updated = SNI.model_validate(data)
        logger.info("Updated Konnect SNI", name=updated.name, id=updated.id)
        return updated

    def delete_sni(
        self,
        control_plane_id: str,
        sni_id_or_name: str,
    ) -> None:
        """Delete an SNI from a control plane.

        Args:
            control_plane_id: Control plane ID.
            sni_id_or_name: SNI ID or name to delete.
        """
        logger.debug(
            "Deleting Konnect SNI",
            control_plane_id=control_plane_id,
            sni=sni_id_or_name,
        )
        self._request(
            "DELETE",
            f"/v2/control-planes/{control_plane_id}/core-entities/snis/{sni_id_or_name}",
        )
        logger.info("Deleted Konnect SNI", sni=sni_id_or_name)

    # =========================================================================
    # CA Certificate Management (Control Plane Admin API)
    # =========================================================================

    def list_ca_certificates(
        self,
        control_plane_id: str,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[CACertificate], str | None]:
        """List all CA certificates in a control plane.

        Args:
            control_plane_id: Control plane ID.
            tags: Filter by tags.
            limit: Maximum number of CA certificates to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of CA certificates, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        logger.debug("Listing Konnect CA certificates", control_plane_id=control_plane_id)
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/ca_certificates",
            params=params,
        )
        ca_certs = [CACertificate.model_validate(item) for item in data.get("data", [])]
        next_offset = data.get("offset")
        logger.info("Listed Konnect CA certificates", count=len(ca_certs))
        return ca_certs, next_offset

    def get_ca_certificate(
        self,
        control_plane_id: str,
        ca_certificate_id: str,
    ) -> CACertificate:
        """Get a CA certificate from a control plane.

        Args:
            control_plane_id: Control plane ID.
            ca_certificate_id: CA certificate ID.

        Returns:
            CA certificate details.

        Raises:
            KonnectNotFoundError: If CA certificate not found.
        """
        logger.debug(
            "Getting Konnect CA certificate",
            control_plane_id=control_plane_id,
            ca_certificate=ca_certificate_id,
        )
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/ca_certificates/{ca_certificate_id}",
        )
        return CACertificate.model_validate(data)

    def create_ca_certificate(
        self,
        control_plane_id: str,
        ca_certificate: CACertificate,
    ) -> CACertificate:
        """Create a CA certificate in a control plane.

        Args:
            control_plane_id: Control plane ID.
            ca_certificate: CA certificate to create.

        Returns:
            Created CA certificate with ID and timestamps.
        """
        payload = ca_certificate.to_create_payload()
        logger.debug(
            "Creating Konnect CA certificate",
            control_plane_id=control_plane_id,
        )
        data = self._request(
            "POST",
            f"/v2/control-planes/{control_plane_id}/core-entities/ca_certificates",
            json=payload,
        )
        created = CACertificate.model_validate(data)
        logger.info("Created Konnect CA certificate", id=created.id)
        return created

    def update_ca_certificate(
        self,
        control_plane_id: str,
        ca_certificate_id: str,
        ca_certificate: CACertificate,
    ) -> CACertificate:
        """Update a CA certificate in a control plane.

        Args:
            control_plane_id: Control plane ID.
            ca_certificate_id: CA certificate ID to update.
            ca_certificate: Updated CA certificate data.

        Returns:
            Updated CA certificate.
        """
        payload = ca_certificate.to_create_payload()
        logger.debug(
            "Updating Konnect CA certificate",
            control_plane_id=control_plane_id,
            ca_certificate=ca_certificate_id,
        )
        data = self._request(
            "PATCH",
            f"/v2/control-planes/{control_plane_id}/core-entities/ca_certificates/{ca_certificate_id}",
            json=payload,
        )
        updated = CACertificate.model_validate(data)
        logger.info("Updated Konnect CA certificate", id=updated.id)
        return updated

    def delete_ca_certificate(
        self,
        control_plane_id: str,
        ca_certificate_id: str,
    ) -> None:
        """Delete a CA certificate from a control plane.

        Args:
            control_plane_id: Control plane ID.
            ca_certificate_id: CA certificate ID to delete.
        """
        logger.debug(
            "Deleting Konnect CA certificate",
            control_plane_id=control_plane_id,
            ca_certificate=ca_certificate_id,
        )
        self._request(
            "DELETE",
            f"/v2/control-planes/{control_plane_id}/core-entities/ca_certificates/{ca_certificate_id}",
        )
        logger.info("Deleted Konnect CA certificate", ca_certificate=ca_certificate_id)

    # =========================================================================
    # Key Set Management (Control Plane Admin API)
    # =========================================================================

    def list_key_sets(
        self,
        control_plane_id: str,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[KeySet], str | None]:
        """List all key sets in a control plane.

        Args:
            control_plane_id: Control plane ID.
            tags: Filter by tags.
            limit: Maximum number of key sets to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of key sets, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        logger.debug("Listing Konnect key sets", control_plane_id=control_plane_id)
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/key-sets",
            params=params,
        )
        key_sets = [KeySet.model_validate(item) for item in data.get("data", [])]
        next_offset = data.get("offset")
        logger.info("Listed Konnect key sets", count=len(key_sets))
        return key_sets, next_offset

    def get_key_set(
        self,
        control_plane_id: str,
        key_set_id_or_name: str,
    ) -> KeySet:
        """Get a key set from a control plane.

        Args:
            control_plane_id: Control plane ID.
            key_set_id_or_name: Key set ID or name.

        Returns:
            Key set details.

        Raises:
            KonnectNotFoundError: If key set not found.
        """
        logger.debug(
            "Getting Konnect key set",
            control_plane_id=control_plane_id,
            key_set=key_set_id_or_name,
        )
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/key-sets/{key_set_id_or_name}",
        )
        return KeySet.model_validate(data)

    def create_key_set(
        self,
        control_plane_id: str,
        key_set: KeySet,
    ) -> KeySet:
        """Create a key set in a control plane.

        Args:
            control_plane_id: Control plane ID.
            key_set: Key set to create.

        Returns:
            Created key set with ID and timestamps.
        """
        payload = key_set.to_create_payload()
        logger.debug(
            "Creating Konnect key set",
            control_plane_id=control_plane_id,
            name=key_set.name,
        )
        data = self._request(
            "POST",
            f"/v2/control-planes/{control_plane_id}/core-entities/key-sets",
            json=payload,
        )
        created = KeySet.model_validate(data)
        logger.info("Created Konnect key set", name=created.name, id=created.id)
        return created

    def update_key_set(
        self,
        control_plane_id: str,
        key_set_id_or_name: str,
        key_set: KeySet,
    ) -> KeySet:
        """Update a key set in a control plane.

        Args:
            control_plane_id: Control plane ID.
            key_set_id_or_name: Key set ID or name to update.
            key_set: Updated key set data.

        Returns:
            Updated key set.
        """
        payload = key_set.to_create_payload()
        logger.debug(
            "Updating Konnect key set",
            control_plane_id=control_plane_id,
            key_set=key_set_id_or_name,
        )
        data = self._request(
            "PATCH",
            f"/v2/control-planes/{control_plane_id}/core-entities/key-sets/{key_set_id_or_name}",
            json=payload,
        )
        updated = KeySet.model_validate(data)
        logger.info("Updated Konnect key set", name=updated.name, id=updated.id)
        return updated

    def delete_key_set(
        self,
        control_plane_id: str,
        key_set_id_or_name: str,
    ) -> None:
        """Delete a key set from a control plane.

        Args:
            control_plane_id: Control plane ID.
            key_set_id_or_name: Key set ID or name to delete.
        """
        logger.debug(
            "Deleting Konnect key set",
            control_plane_id=control_plane_id,
            key_set=key_set_id_or_name,
        )
        self._request(
            "DELETE",
            f"/v2/control-planes/{control_plane_id}/core-entities/key-sets/{key_set_id_or_name}",
        )
        logger.info("Deleted Konnect key set", key_set=key_set_id_or_name)

    # =========================================================================
    # Key Management (Control Plane Admin API)
    # =========================================================================

    def list_keys(
        self,
        control_plane_id: str,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[Key], str | None]:
        """List all keys in a control plane.

        Args:
            control_plane_id: Control plane ID.
            tags: Filter by tags.
            limit: Maximum number of keys to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of keys, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        logger.debug("Listing Konnect keys", control_plane_id=control_plane_id)
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/keys",
            params=params,
        )
        keys = [Key.model_validate(item) for item in data.get("data", [])]
        next_offset = data.get("offset")
        logger.info("Listed Konnect keys", count=len(keys))
        return keys, next_offset

    def get_key(
        self,
        control_plane_id: str,
        key_id_or_name: str,
    ) -> Key:
        """Get a key from a control plane.

        Args:
            control_plane_id: Control plane ID.
            key_id_or_name: Key ID or name.

        Returns:
            Key details.

        Raises:
            KonnectNotFoundError: If key not found.
        """
        logger.debug(
            "Getting Konnect key",
            control_plane_id=control_plane_id,
            key=key_id_or_name,
        )
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/keys/{key_id_or_name}",
        )
        return Key.model_validate(data)

    def create_key(
        self,
        control_plane_id: str,
        key: Key,
    ) -> Key:
        """Create a key in a control plane.

        Args:
            control_plane_id: Control plane ID.
            key: Key to create.

        Returns:
            Created key with ID and timestamps.
        """
        payload = key.to_create_payload()
        logger.debug(
            "Creating Konnect key",
            control_plane_id=control_plane_id,
            kid=key.kid,
        )
        data = self._request(
            "POST",
            f"/v2/control-planes/{control_plane_id}/core-entities/keys",
            json=payload,
        )
        created = Key.model_validate(data)
        logger.info("Created Konnect key", kid=created.kid, id=created.id)
        return created

    def update_key(
        self,
        control_plane_id: str,
        key_id_or_name: str,
        key: Key,
    ) -> Key:
        """Update a key in a control plane.

        Args:
            control_plane_id: Control plane ID.
            key_id_or_name: Key ID or name to update.
            key: Updated key data.

        Returns:
            Updated key.
        """
        payload = key.to_create_payload()
        logger.debug(
            "Updating Konnect key",
            control_plane_id=control_plane_id,
            key=key_id_or_name,
        )
        data = self._request(
            "PATCH",
            f"/v2/control-planes/{control_plane_id}/core-entities/keys/{key_id_or_name}",
            json=payload,
        )
        updated = Key.model_validate(data)
        logger.info("Updated Konnect key", kid=updated.kid, id=updated.id)
        return updated

    def delete_key(
        self,
        control_plane_id: str,
        key_id_or_name: str,
    ) -> None:
        """Delete a key from a control plane.

        Args:
            control_plane_id: Control plane ID.
            key_id_or_name: Key ID or name to delete.
        """
        logger.debug(
            "Deleting Konnect key",
            control_plane_id=control_plane_id,
            key=key_id_or_name,
        )
        self._request(
            "DELETE",
            f"/v2/control-planes/{control_plane_id}/core-entities/keys/{key_id_or_name}",
        )
        logger.info("Deleted Konnect key", key=key_id_or_name)

    # =========================================================================
    # Vault Management (Control Plane Admin API - Enterprise)
    # =========================================================================

    def list_vaults(
        self,
        control_plane_id: str,
        *,
        tags: list[str] | None = None,
        limit: int | None = None,
        offset: str | None = None,
    ) -> tuple[list[Vault], str | None]:
        """List all vaults in a control plane.

        Note: Vaults are an Enterprise feature.

        Args:
            control_plane_id: Control plane ID.
            tags: Filter by tags.
            limit: Maximum number of vaults to return.
            offset: Pagination offset token.

        Returns:
            Tuple of (list of vaults, next offset for pagination).
        """
        params: dict[str, Any] = {}
        if tags:
            params["tags"] = ",".join(tags)
        if limit:
            params["size"] = limit
        if offset:
            params["offset"] = offset

        logger.debug("Listing Konnect vaults", control_plane_id=control_plane_id)
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/vaults",
            params=params,
        )
        vaults = [Vault.model_validate(item) for item in data.get("data", [])]
        next_offset = data.get("offset")
        logger.info("Listed Konnect vaults", count=len(vaults))
        return vaults, next_offset

    def get_vault(
        self,
        control_plane_id: str,
        vault_id_or_prefix: str,
    ) -> Vault:
        """Get a vault from a control plane.

        Note: Vaults are an Enterprise feature.

        Args:
            control_plane_id: Control plane ID.
            vault_id_or_prefix: Vault ID or prefix.

        Returns:
            Vault details.

        Raises:
            KonnectNotFoundError: If vault not found.
        """
        logger.debug(
            "Getting Konnect vault",
            control_plane_id=control_plane_id,
            vault=vault_id_or_prefix,
        )
        data = self._request(
            "GET",
            f"/v2/control-planes/{control_plane_id}/core-entities/vaults/{vault_id_or_prefix}",
        )
        return Vault.model_validate(data)

    def create_vault(
        self,
        control_plane_id: str,
        vault: Vault,
    ) -> Vault:
        """Create a vault in a control plane.

        Note: Vaults are an Enterprise feature.

        Args:
            control_plane_id: Control plane ID.
            vault: Vault to create.

        Returns:
            Created vault with ID and timestamps.
        """
        payload = vault.to_create_payload()
        logger.debug(
            "Creating Konnect vault",
            control_plane_id=control_plane_id,
            name=vault.name,
        )
        data = self._request(
            "POST",
            f"/v2/control-planes/{control_plane_id}/core-entities/vaults",
            json=payload,
        )
        created = Vault.model_validate(data)
        logger.info("Created Konnect vault", name=created.name, id=created.id)
        return created

    def update_vault(
        self,
        control_plane_id: str,
        vault_id_or_prefix: str,
        vault: Vault,
    ) -> Vault:
        """Update a vault in a control plane.

        Note: Vaults are an Enterprise feature.

        Args:
            control_plane_id: Control plane ID.
            vault_id_or_prefix: Vault ID or prefix to update.
            vault: Updated vault data.

        Returns:
            Updated vault.
        """
        payload = vault.to_create_payload()
        logger.debug(
            "Updating Konnect vault",
            control_plane_id=control_plane_id,
            vault=vault_id_or_prefix,
        )
        data = self._request(
            "PATCH",
            f"/v2/control-planes/{control_plane_id}/core-entities/vaults/{vault_id_or_prefix}",
            json=payload,
        )
        updated = Vault.model_validate(data)
        logger.info("Updated Konnect vault", name=updated.name, id=updated.id)
        return updated

    def delete_vault(
        self,
        control_plane_id: str,
        vault_id_or_prefix: str,
    ) -> None:
        """Delete a vault from a control plane.

        Note: Vaults are an Enterprise feature.

        Args:
            control_plane_id: Control plane ID.
            vault_id_or_prefix: Vault ID or prefix to delete.
        """
        logger.debug(
            "Deleting Konnect vault",
            control_plane_id=control_plane_id,
            vault=vault_id_or_prefix,
        )
        self._request(
            "DELETE",
            f"/v2/control-planes/{control_plane_id}/core-entities/vaults/{vault_id_or_prefix}",
        )
        logger.info("Deleted Konnect vault", vault=vault_id_or_prefix)
