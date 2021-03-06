"""
Tests for Django views.
"""

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import Client
from django.test import TestCase

from main.models import AlignmentGroup
from main.models import Chromosome
from main.models import Project
from main.models import ReferenceGenome
from main.models import Variant
from main.models import VariantAlternate


TEST_USERNAME = 'testusername'
TEST_PASSWORD = 'password'
TEST_EMAIL = 'test@test.com'

STATUS_CODE__SUCCESS = 200
STATUS_CODE__NOT_LOGGED_IN = 302
STATUS_CODE__NOT_FOUND = 404
STATUS_CODE__REDIRECT = 302
STATUS_CODE__SERVER_ERROR = 500


class TestViews(TestCase):

    def setUp(self):
        # Test models.
        user = User.objects.create_user(TEST_USERNAME, password=TEST_PASSWORD,
                email=TEST_EMAIL)
        self.test_project = Project.objects.create(owner=user.get_profile(),
                title='Test Project')
        self.ref_genome = ReferenceGenome.objects.create(
                project=self.test_project, label='refgenome')

        self.chromosome = Chromosome.objects.create(
            reference_genome=self.ref_genome,
            label='Chromosome',
            num_bases=9001)

        alignment_group = AlignmentGroup.objects.create(
                label='Alignment 1',
                reference_genome=self.ref_genome,
                aligner=AlignmentGroup.ALIGNER.BWA)
        variant = Variant.objects.create(
                type=Variant.TYPE.TRANSITION,
                reference_genome=self.ref_genome,
                chromosome=self.chromosome,
                position=10,
                ref_value='A')

        VariantAlternate.objects.create(
                variant=variant,
                alt_value='G')

        # Urls that do not require the user to be logged in.
        self.no_login_required_urls = [
                reverse('main.views.home_view'),
        ]

        # Urls that require the user to be logged in, but do not try any
        # particular entity.
        self.non_specific_login_required_urls = [
                reverse('main.views.project_list_view'),
                reverse('main.views.project_create_view'),
        ]

        # Urls for a specific entity.
        self.specific_entity_urls = [
                # Tab base views.
                reverse('main.views.project_view',
                        args=(self.test_project.uid,)),
                reverse('main.views.tab_root_analyze',
                        args=(self.test_project.uid,)),

                # Project-specific views
                reverse('main.views.project_view',
                        args=(self.test_project.uid,)),

                # Reference genomes
                reverse('main.views.reference_genome_list_view',
                        args=(self.test_project.uid,)),
                reverse('main.views.reference_genome_view',
                        args=(self.test_project.uid, self.ref_genome.uid)),

                # Alignments
                reverse('main.views.alignment_list_view',
                        args=(self.test_project.uid,)),
                reverse('main.views.alignment_create_view',
                        args=(self.test_project.uid,)),
                reverse('main.views.alignment_view',
                        args=(self.test_project.uid, alignment_group.uid)),

                # Variant sets
                reverse('main.views.variant_set_list_view',
                        args=(self.test_project.uid,)),

                # Samples
                reverse('main.views.sample_list_view',
                        args=(self.test_project.uid,)),
        ]

        # The fake web browser client used to make requests.
        self.client = Client()

    def assert_url_response(self, url, expected_status_code):
        """Helper method that calls a URL and compares the response status
        code to expected_status_code.
        """
        response = self.client.get(url)
        self.assertEqual(expected_status_code, response.status_code,
                ("Simple url test failed for %s with status code %d. " +
                        "Expected status code %d.") % (
                                url, response.status_code, expected_status_code))

    def test_views__logged_out(self):
        """Tests calling the views without a logged in user.
        """
        login_error_urls = (self.non_specific_login_required_urls +
                self.specific_entity_urls)
        for url in login_error_urls:
            self.assert_url_response(url, STATUS_CODE__NOT_LOGGED_IN)

        success_urls = self.no_login_required_urls
        for url in success_urls:
            self.assert_url_response(url, STATUS_CODE__SUCCESS)


    def test_views__logged_in_owner(self):
        """Tests calling views with the owner logged in.
        """
        self.client.login(username=TEST_USERNAME, password=TEST_PASSWORD)
        all_urls = (self.no_login_required_urls +
                self.non_specific_login_required_urls +
                self.specific_entity_urls)
        for url in all_urls:
            self.assert_url_response(url, STATUS_CODE__SUCCESS)


    def test_views__logged_in_non_owner(self):
        """Tests calling views with the non-owner logged in.
        """
        OTHER_USERNAME = 'justtest'
        OTHER_PASSWORD = 'other_password'
        OTHER_EMAIL = 'justtest@me.com'
        User.objects.create_user(
                OTHER_USERNAME, password=OTHER_PASSWORD, email=OTHER_EMAIL)
        self.client.login(username=OTHER_USERNAME, password=OTHER_PASSWORD)

        error_urls = self.specific_entity_urls
        for url in error_urls:
            self.assert_url_response(url, STATUS_CODE__NOT_FOUND)

        success_urls = (self.non_specific_login_required_urls +
                self.no_login_required_urls)
        for url in success_urls:
            self.assert_url_response(url, STATUS_CODE__SUCCESS)

    def test_compile_jbrowse_and_redirect(self):
        """Tests the JBrowse redirect handler.
        """
        self.client.login(username=TEST_USERNAME, password=TEST_PASSWORD)

        # If invalid ids, then 404.
        url = ('/redirect_jbrowse?data=/jbrowse/gd_data/projects/167e93/' +
                'ref_genomes/ad561ec6/jbrowse')
        self.assert_url_response(url, STATUS_CODE__NOT_FOUND)

        # If valid ids, then successful redirect.
        url = ('/redirect_jbrowse?data=/jbrowse/gd_data/projects/%s/ref_genomes/%s/jbrowse' % (
                    self.test_project.uid, self.ref_genome.uid))
        self.assert_url_response(url, STATUS_CODE__REDIRECT)

        # Incorrect. Note the "http://localhost" incorrectly injected.
        url = ('/redirect_jbrowse?data=http://localhost/jbrowse/gd_data/'
                'projects/16167e93/ref_genomes/ad561ec6/jbrowse')
        with self.assertRaises(AssertionError):
            self.client.get(url)
