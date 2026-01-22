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

from system_operations_manager.integrations.kong.models.consumer import Consumer
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
