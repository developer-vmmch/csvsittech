"""
Result Allocation Service
=========================
Handles the global result pool: atomic, transactional, concurrency-safe
allocation of AutomationDummyResult records to ServiceRequestInvestigation rows.

Key rules:
  - Each investigation has its own independent global pool.
  - select_for_update(skip_locked=True) prevents concurrent duplicate allocation.
  - Allocation for all investigations in a request is atomic (all-or-nothing).
  - A result once Consumed cannot be re-allocated.
"""

from django.db import transaction


class ResultPoolExhaustedError(Exception):
    """Raised when no eligible result is available in the pool."""
    pass


class ResultAllocationService:

    @staticmethod
    @transaction.atomic
    def allocate_for_sr_investigation(sr_investigation, required_status=None):
        """
        Find and lock the first eligible unused AutomationDummyResult for an investigation.

        Args:
            sr_investigation: ServiceRequestInvestigation instance.
            required_status:  None (any), "NORMAL", "BELOW", or "ABOVE".

        Returns:
            AutomationDummyResult that was consumed.

        Raises:
            ResultPoolExhaustedError if no eligible result exists.
        """
        from apps.lab.models import AutomationDummyResult, ServiceRequestAllocation

        investigation = sr_investigation.investigation
        qs = AutomationDummyResult.objects.filter(
            investigation=investigation,
            status=AutomationDummyResult.StatusChoices.SAVED,
        )
        if required_status:
            qs = qs.filter(result_status=required_status)

        # Lock the first eligible result — skip rows already locked by concurrent transactions
        result = qs.select_for_update(skip_locked=True).order_by("id").first()

        if not result:
            raise ResultPoolExhaustedError(
                "No available %s result for investigation: %s" % (
                    required_status or "any", investigation.name
                )
            )

        # Mark as consumed
        result.status = AutomationDummyResult.StatusChoices.CONSUMED
        result.save(update_fields=["status", "updated_at"])

        # Record the allocation link
        allocated_by = (
            sr_investigation.service_request.created_by
            if sr_investigation.service_request.created_by_id
            else None
        )
        ServiceRequestAllocation.objects.create(
            sr_investigation=sr_investigation,
            dummy_result=result,
            allocated_by=allocated_by,
        )

        return result

    @staticmethod
    @transaction.atomic
    def allocate_all_for_service_request(service_request, required_status=None):
        """
        Atomically allocate results for ALL active investigations in a service request.
        Rolls back entirely if any pool is exhausted.

        Returns:
            dict: {investigation_id: AutomationDummyResult}
        """
        from apps.lab.models import ServiceRequestInvestigation

        sr_investigations = ServiceRequestInvestigation.objects.filter(
            service_request=service_request,
            is_removed=False,
        ).select_related("investigation", "service_request")

        allocations = {}
        for sri in sr_investigations:
            result = ResultAllocationService.allocate_for_sr_investigation(
                sri, required_status=required_status
            )
            allocations[sri.investigation_id] = result

        return allocations

    @staticmethod
    def get_pool_availability(investigation_ids):
        """
        Get result pool counts per investigation.

        Returns:
            dict: {investigation_id: {total, normal, below, above, consumed}}
        """
        from django.db.models import Count, Q
        from apps.lab.models import AutomationDummyResult

        qs = AutomationDummyResult.objects.filter(
            investigation_id__in=investigation_ids
        ).values("investigation_id").annotate(
            total=Count("id"),
            available=Count("id", filter=Q(status="Saved")),
            normal=Count("id", filter=Q(status="Saved", result_status="NORMAL")),
            below=Count("id", filter=Q(status="Saved", result_status="BELOW")),
            above=Count("id", filter=Q(status="Saved", result_status="ABOVE")),
            consumed=Count("id", filter=Q(status="Consumed")),
        )

        result = {}
        for row in qs:
            result[row["investigation_id"]] = {
                "total": row["total"],
                "available": row["available"],
                "normal": row["normal"],
                "below": row["below"],
                "above": row["above"],
                "consumed": row["consumed"],
            }
        return result
