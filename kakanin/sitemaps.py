from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import AboutPage, ContactInfo, Feedback, Kakanin


class KakaninSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Kakanin.objects.filter(is_available=True)

    def location(self, obj):
        return reverse("shop")


class UserProfileSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # User profile page requires authentication but expose URL for completeness
        return ["user_profile"]

    def location(self, item):
        return reverse(item)


class AboutPageSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        pages = list(AboutPage.objects.all())
        return pages or ["about"]

    def location(self, item):
        if hasattr(item, "pk"):
            return reverse("about")
        return reverse(item)

    def lastmod(self, item):
        if hasattr(item, "updated_at"):
            return item.updated_at
        return None


class ContactInfoSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        contacts = list(ContactInfo.objects.all())
        return contacts or ["contact"]

    def location(self, item):
        if hasattr(item, "pk"):
            return reverse("contact")
        return reverse(item)

    def lastmod(self, item):
        if hasattr(item, "updated_at"):
            return item.updated_at
        return None


class FeedbackSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return ["submit_feedback"]

    def location(self, item):
        return reverse(item)


class StaticPageSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return [
            "home",
            "shop",
            "about",
            "contact",
            "login",
            "signup",
        ]

    def location(self, item):
        return reverse(item)
