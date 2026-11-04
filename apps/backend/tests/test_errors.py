from cadence_ia.api.errors import _status
from cadence_ia.services.errors import NotFound, ServiceError


class PlanNotFound(NotFound):
    pass


def test_subclass_keeps_parent_status():
    assert _status(PlanNotFound("session_not_found", "x")) == 404


def test_unclassified_error_is_500():
    assert _status(ServiceError("session_not_found", "x")) == 500
