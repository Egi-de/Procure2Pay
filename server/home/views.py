from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from requests_app.serializers import UserSerializer

from django.views.generic import TemplateView

User = get_user_model()


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class SPAView(TemplateView):
    template_name = 'index.html'
