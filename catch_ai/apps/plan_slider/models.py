import uuid
from django.db import models


import uuid
from django.db import models


class PlanSlide(models.Model):

    id = models.CharField(primary_key=True, max_length=20, editable=False)

    file_url = models.URLField()

    media_type = models.CharField(
        max_length=10,
        choices=[("image", "Image"), ("video", "Video")]
    )
    order = models.IntegerField(default=0, db_index=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = "ps_" + uuid.uuid4().hex[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.id