from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import UserSerializer

class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login - Kirim {username, password}, terima access + refresh token.
    """
    pass  

class MeView(APIView):
    """
    GET /api/auth/me - cek siapa user yang sedang login (butuh token)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)