from djoser.serializers import UserSerializer as BaseUserSerializer
from .models import CustomUser

class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role')