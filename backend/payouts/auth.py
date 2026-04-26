from rest_framework import authentication, exceptions
from .models import Merchant


class APIKeyAuthentication(authentication.BaseAuthentication):
    keyword = "Api-Key"

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith(f"{self.keyword} "):
            return None

        api_key = auth_header[len(f"{self.keyword} "):].strip()
        if not api_key:
            return None

        try:
            merchant = Merchant.objects.get(api_key=api_key)
        except Merchant.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API key")

        return (merchant, None)
