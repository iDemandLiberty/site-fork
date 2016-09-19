import logging
import importlib
from pathlib import Path
from django.test import TestCase, override_settings, modify_settings
from django.http import Http404
from django.contrib.flatpages.models import FlatPage
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from machina.test.factories import create_forum
from machina.test.factories import create_topic
from machina.test.factories import PostFactory
from machina.test.factories import UserFactory
from agcs.urls import handler404, sitemaps
from contact.forms import ContactForm
from landing.urls import urlpatterns as landing_urls


@override_settings(
    FIXTURE_DIRS = [
        str(Path(__file__).resolve()
            .parent.parent.joinpath('agcs','fixtures')),
	]
)
class LandingViewsTest(TestCase):
    fixtures = [
        'services.json',
        'dev_flatpages.json',
        'dev_sites.json'
    ]

    def setUp(self):
        self.u1 = UserFactory.create()
        self.top_level_forum = create_forum()
        self.topic = create_topic(forum=self.top_level_forum, poster=self.u1)
        self.post = PostFactory.create(topic=self.topic, poster=self.u1)
        self.topic_pk = self.topic.pk

    def assertStatusOK(self, url):
        self.assertEqual(200,
            self.client.get(url,
                follow=True
            ).status_code,
            msg='url: %s' % url
        )


    def test_get_landing_pages(self):
        for url in landing_urls:
            self.assertStatusOK(reverse(url.name))

    def test_get_manifest(self):
        self.assertStatusOK(reverse('chrome_manifest'))

    def test_get_site_map(self):
        self.assertStatusOK('/sitemap.xml')

    def test_get_flat_pages(self):
        for p in FlatPage.objects.all():
            self.assertStatusOK(p.url)

    def test_urls_from_site_map(self):
        for k in sitemaps.keys():
            try:
                self.assertGreaterEqual(len(sitemaps[k]().items()), 1)
            except AssertionError as e:
                raise AssertionError('k=%s; v=%s\n%s' % (
                    str(k),str(sitemaps[k]),str(e)
                ))

class TemplateTagsTest(TestCase):

    def test_landing_utils(self):

        with self.assertRaises(RuntimeError):
            render_to_string('test/landing_utils.html',
                context={
                    'form': ContactForm(),
                    'badpath': 'js/none.js'
                })

        with self.assertRaises(RuntimeError):
            render_to_string('test/landing_utils.html',
                context={
                    'form': ContactForm(),
                    'somedir': 'js'
                })

        render_to_string(
            'test/landing_utils.html',
            context={'form': ContactForm()}
        )



class ErrorPageViewsTest(TestCase):

    def setUp(self):
        self.logger = logging.getLogger('django.request')
        self.old_level = self.logger.getEffectiveLevel()
        self.logger.setLevel(logging.ERROR)

    def tearDown(self):
        self.logger.setLevel(self.old_level)

    def test_page_not_found(self):
        module, name = handler404.rsplit('.', 1)
        response = self.client.get('/foo/bar.baz')
        self.assertHTMLEqual(response.content.decode(),
            getattr(importlib.import_module(module), name)(
                response.request, Http404('Bad request')
            ).content.decode()
        )
