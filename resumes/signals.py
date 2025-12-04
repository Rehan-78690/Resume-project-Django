# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.utils import timezone
# from .models import Resume


# @receiver(post_save, sender=Resume)
# def update_resume_timestamps(sender, instance, **kwargs):
#     """
#     Update timestamps when resume is modified.
#     """
#     if kwargs.get('update_fields'):
#         # Only update last_edited_at if not in update_fields
#         if 'last_edited_at' not in kwargs['update_fields']:
#             instance.last_edited_at = timezone.now()
#             instance.save(update_fields=['last_edited_at'])