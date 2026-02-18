from rest_framework import serializers

class AdCourtDateInputModel(serializers.Serializer):
    courtDateTitle = serializers.CharField(required=True,allow_blank=False)
    date = serializers.DateField(required=True)