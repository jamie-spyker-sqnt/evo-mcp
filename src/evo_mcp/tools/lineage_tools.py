# SPDX-FileCopyrightText: 2026 Bentley Systems, Incorporated
#
# SPDX-License-Identifier: Apache-2.0

"""MCP tools for Evo data lineage operations.

Wraps :class:`evo.lineage.LineageServiceClient` and exposes one MCP tool per
client method. The lineage service tracks the provenance of datasets (geoscience
objects, block models, files) and the runs/jobs that produced them, following the
OpenLineage specification.
"""

import logging
import os
from uuid import UUID

from evo.common import HealthCheckType
from evo.lineage import LineageServiceClient

from evo_mcp.context import get_evo_context

logger = logging.getLogger(__name__)

# The lineage service is preview-gated. The header opts the request into preview
# functionality; "lineage-service-mvp" enables the MVP feature set. Override via
# the LINEAGE_API_PREVIEW environment variable (for example "opt-in").
DEFAULT_LINEAGE_API_PREVIEW = "lineage-service-mvp"


async def get_lineage_client() -> LineageServiceClient:
    """Build a lineage service client from the current Evo context."""
    evo_context = await get_evo_context()
    if not evo_context.connector or not evo_context.org_id:
        raise ValueError("Please ensure you are connected to an instance.")

    api_preview_header = os.getenv("LINEAGE_API_PREVIEW", DEFAULT_LINEAGE_API_PREVIEW)
    return LineageServiceClient(
        org_id=evo_context.org_id,
        connector=evo_context.connector,
        api_preview_header=api_preview_header,
    )


def register_lineage_tools(mcp):
    """Register data lineage tools with the FastMCP server."""

    @mcp.tool()
    async def get_lineage_service_health() -> dict:
        """Check the health status of the Evo lineage service.

        Returns:
            A dict with the service name and current status.
        """
        client = await get_lineage_client()
        health = await client.get_service_health(check_type=HealthCheckType.FULL)
        return {
            "service": health.service,
            "status": health.status,
        }

    @mcp.tool()
    async def build_lineage_dataset_namespace(
        service_name: str,
        workspace_id: UUID,
    ) -> dict:
        """Build a lineage dataset namespace string for the selected instance.

        Namespaces follow the Evo standard "<service_name>://<org_id>/<workspace_id>"
        and are used to uniquely identify datasets in lineage queries.

        Args:
            service_name: The Evo service that owns the dataset. One of
                "evogeoscienceobject", "evoblockmodel", or "evofile".
            workspace_id: The workspace UUID that contains the dataset.

        Returns:
            A dict containing the formatted namespace string.
        """
        client = await get_lineage_client()
        namespace = client.dataset_namespace_helper(service_name, str(workspace_id))
        return {"namespace": namespace}

    @mcp.tool()
    async def build_lineage_dataset_name(
        object_id: str,
        object_version: str,
    ) -> dict:
        """Build a lineage dataset name string following the Evo standard.

        Dataset names follow the format "<object_id>:<object_version>".

        Args:
            object_id: The ID of the object.
            object_version: The version identifier of the object.

        Returns:
            A dict containing the formatted dataset name string.
        """
        client = await get_lineage_client()
        name = client.dataset_name_helper(object_id, object_version)
        return {"name": name}

    @mcp.tool()
    async def get_dataset_lineage_graph(
        dataset_name: str,
        dataset_namespace: str,
        forward_depth: int | None = 3,
        backward_depth: int | None = 3,
    ) -> dict:
        """Retrieve the lineage graph for a dataset.

        The graph contains the datasets, runs and restricted processes connected
        to the requested dataset, showing how it was produced and consumed.

        Args:
            dataset_name: Name of the dataset (see build_lineage_dataset_name).
            dataset_namespace: Namespace of the dataset (see
                build_lineage_dataset_namespace).
            forward_depth: Forward traversal depth (downstream). Defaults to 3.
            backward_depth: Backward traversal depth (upstream). Defaults to 3.
                At least one depth parameter must be specified (non-None).

        Returns:
            The lineage graph response.
        """
        client = await get_lineage_client()
        response = await client.get_dataset_graph(
            dataset_name=dataset_name,
            dataset_namespace=dataset_namespace,
            forward_depth=forward_depth,
            backward_depth=backward_depth,
        )
        return response.model_dump(mode="json")

    @mcp.tool()
    async def get_dataset_lineage_details(
        dataset_name: str,
        dataset_namespace: str,
    ) -> dict:
        """Retrieve details for a single lineage dataset.

        Args:
            dataset_name: Name of the dataset (see build_lineage_dataset_name).
            dataset_namespace: Namespace of the dataset (see
                build_lineage_dataset_namespace).

        Returns:
            The dataset details response, including its node ID and facets.
        """
        client = await get_lineage_client()
        response = await client.get_dataset_details(
            dataset_name=dataset_name,
            dataset_namespace=dataset_namespace,
        )
        return response.model_dump(mode="json")

    @mcp.tool()
    async def get_lineage_run(run_id: UUID) -> dict:
        """Retrieve details for a lineage run.

        Args:
            run_id: The globally unique run identifier.

        Returns:
            The run details response, including job, inputs, outputs and facets.
        """
        client = await get_lineage_client()
        response = await client.get_run(run_id)
        return response.model_dump(mode="json")

    @mcp.tool()
    async def get_lineage_run_events(run_id: UUID) -> dict:
        """Retrieve all events associated with a lineage run.

        Args:
            run_id: The globally unique run identifier.

        Returns:
            The run events response containing the ordered list of run events.
        """
        client = await get_lineage_client()
        response = await client.get_run_events(run_id)
        return response.model_dump(mode="json")

    @mcp.tool()
    async def get_lineage_run_graph(
        run_id: UUID,
        forward_depth: int | None = 3,
        backward_depth: int | None = 3,
    ) -> dict:
        """Retrieve the lineage graph for a run.

        Args:
            run_id: The globally unique run identifier.
            forward_depth: Forward traversal depth (downstream). Defaults to 3.
            backward_depth: Backward traversal depth (upstream). Defaults to 3.
                At least one depth parameter must be specified (non-None).

        Returns:
            The lineage graph response.
        """
        client = await get_lineage_client()
        response = await client.get_run_graph(
            run_id,
            forward_depth=forward_depth,
            backward_depth=backward_depth,
        )
        return response.model_dump(mode="json")
