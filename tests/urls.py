"""Test URLs."""

from django.urls import path


def dummy_view(request):
    """Dummy view for testing."""
    from django.http import JsonResponse

    return JsonResponse(
        {
            "tenant": {
                "id": request.tenant.id if request.tenant else None,
                "name": request.tenant.name if request.tenant else None,
                "slug": request.tenant.slug if request.tenant else None,
            }
        }
    )


urlpatterns = [
    path("test/", dummy_view, name="test_view"),
]
