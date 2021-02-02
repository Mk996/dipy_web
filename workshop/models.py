from django.conf import settings
from django.db import models


class Speakers(models.Model):
    fullname = models.CharField(max_length=300)
    department = models.CharField(max_length=300)
    university = models.CharField(max_length=300)
    avatar = models.ImageField(upload_to='speaker_images/', blank=True,
                               null=True)

    def __str__(self):
        return self.fullname

    def avatar_url(self):
        """
        Returns the URL of the image associated with this Object.
        If an image hasn't been uploaded yet, it returns a stock image
        :returns: str -- the image url
        """
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        else:
            return "{0}{1}/{2}".format(settings.STATIC_URL, 'images', 'user-1633250_640.png')


class Workshop(models.Model):
    code_name = models.CharField(max_length=200)
    start_date = models.DateTimeField(editable=True)
    end_date = models.DateTimeField(editable=True)
    registration_start_date = models.DateTimeField(editable=True)
    registration_end_date = models.DateTimeField(editable=True)
    speakers = models.ManyToManyField(Speakers, related_name="workshops")
    body_markdown = models.TextField()
    body_html = models.TextField(editable=False)
    description = models.CharField(max_length=140)
    created = models.DateTimeField(editable=False, auto_now_add=True)
    modified = models.DateTimeField(editable=False, auto_now_add=True)
    is_online = models.BooleanField(default=True)

    # def __str__(self):
    #     return f'DIPY WORKSHOP {self.year}'


class Pricing(models.Model):
    name = models.CharField(max_length=100)  # Basic / Pro / Premium
    slug = models.SlugField()
    stripe_price_id = models.CharField(max_length=50)
    price = models.DecimalField(decimal_places=2, max_digits=5)
    currency = models.CharField(max_length=50)

    def __str__(self):
        return self.name


# class Subscription(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     pricing = models.ForeignKey(Pricing, on_delete=models.CASCADE, related_name='subscriptions')
#     created = models.DateTimeField(auto_now_add=True)
#     stripe_subscription_id = models.CharField(max_length=50)
#     status = models.CharField(max_length=100)

#     def __str__(self):
#         return self.user.email

#     @property
#     def is_active(self):
#         return self.status == "active" or self.status == "trialing"


# class Course(models.Model):
#     pricing_tiers = models.ManyToManyField(Pricing, blank=True)
#     name = models.CharField(max_length=100)
#     slug = models.SlugField(unique=True)
#     thumbnail = models.ImageField(upload_to="thumbnails/")
#     description = models.TextField()

#     def __str__(self):
#         return self.name

#     def get_absolute_url(self):
#         return reverse("content:course-detail", kwargs={"slug": self.slug})


# class Video(models.Model):
#     course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='videos')
#     vimeo_id = models.CharField(max_length=50)
#     title = models.CharField(max_length=150)
#     slug = models.SlugField(unique=True)
#     description = models.TextField()
#     order = models.IntegerField(default=1)

#     class Meta:
#         ordering = ["order"]

#     def __str__(self):
#         return self.title

#     def get_absolute_url(self):
#         return reverse("content:video-detail", kwargs={
#             "video_slug": self.slug,
#             "slug": self.course.slug
#         })