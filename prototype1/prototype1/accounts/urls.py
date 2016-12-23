
from django.conf.urls import url, include
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static
from django.contrib import admin
from userena import views as userena_views
from prototype1.accounts.form import SignupFormExtra

admin.autodiscover()

urlpatterns = [

    # Override the signup form with our own, which includes a
    # first and last name and group selection.
    url(r'^signup/$',
        userena_views.signup,
     {'signup_form': SignupFormExtra}),

    url(r'^', include('userena.urls')),
    url(r'^messages/', include('userena.contrib.umessages.urls')),
    # url(r'^$', 'profiles.views.promo', name='promo'),
    # url(r'^i18n/', include('django.conf.urls.i18n')),
]

# Add media and static files
urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
