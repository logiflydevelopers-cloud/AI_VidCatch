from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    is_currently_active = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "message",
            "notification_type",
            "banner_type",
            "display_type",
            "is_active",
            "start_time",
            "end_time",
            "user_type",
            "priority",
            "is_currently_active",
            "created_at",
            "media"
        ]

    def get_is_currently_active(self, obj):
        return obj.is_currently_active()
    
class NotificationCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"