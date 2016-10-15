from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.serializers import ProviderRegistrationSerializer
from share.models import ProviderRegistration


class ProviderRegistrationViewSet(viewsets.ModelViewSet):
    """View showing all registration data in the SHARE Dataset.

    ## Submit Registration.

    Create

        Method:        POST
        Body (JSON):   {
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

        Success:       201 CREATED
    """
    permission_classes = (IsAuthenticated, )
    serializer_class = ProviderRegistrationSerializer

    def get_queryset(self):
        return ProviderRegistration.objects.filter(submitted_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = ProviderRegistrationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            nm_instance = serializer.save()
            return Response({'registration_id': nm_instance.id}, status=status.HTTP_201_CREATED)
        else:
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
