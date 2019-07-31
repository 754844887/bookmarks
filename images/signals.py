from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from .models import Image



@receiver(m2m_changed, sender=Image.user_like.through)
def users_like_changed(sender, instance, **kwargs):
    Image.objects.filter(pk=instance.id).update(total_likes=instance.user_like.conut())