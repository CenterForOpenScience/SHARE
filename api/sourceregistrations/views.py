from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from share.models import ProviderRegistration

from api.base.views import ShareViewSet
from api.deprecation import deprecate
from api.pagination import CursorPagination
from api.sourceregistrations.serializers import ProviderRegistrationSerializer


@deprecate(pls_hide=True)
class ProviderRegistrationViewSet(ShareViewSet, generics.ListCreateAPIView, generics.RetrieveAPIView):
    """View showing all registration data in the SHARE Dataset.

    ## Submit Registration.

    Create

        Method:        POST
        Body (JSON):   {
                            "data": {
                                "type": "ProviderRegistration",
                                "attributes": {
                                    "contact_name": "John Doe",
                                    "contact_email": "email@email.com",
                                    "contact_affiliation": "Organization affliation",
                                    "direct_source": true,
                                    "source_name": "Organization Name",
                                    "source_description": "Organization description.",
                                    "source_rate_limit": "(Optional) 1 request/second",
                                    "source_documentation": "(Optional)",
                                    "source_preferred_metadata_prefix": "(Optional)",
                                    "source_oai": false,
                                    "source_base_url": "(Optional)",
                                    "source_disallowed_sets": "(Optional)",
                                    "source_additional_info": "(Optional)"
                                }
                            }
                        }

        Success:       201 CREATED
    """
    pagination_class = CursorPagination
    permission_classes = (IsAuthenticated, )
    serializer_class = ProviderRegistrationSerializer

    def get_queryset(self):
        return ProviderRegistration.objects.filter(submitted_by_id=self.request.user.pk)
