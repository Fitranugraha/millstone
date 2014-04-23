"""
Tests for xhr_handlers.py.
"""

import json
import os
import re
import StringIO

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.core.urlresolvers import reverse
from django.http.request import HttpRequest
from django.test import Client
from django.test import TestCase

from main.models import AlignmentGroup
from main.models import Dataset
from main.models import ExperimentSample
from main.models import Project
from main.models import ReferenceGenome
from main.models import Variant
from main.models import VariantAlternate
from main.models import VariantCallerCommonData
from main.models import VariantEvidence
from main.testing_util import create_common_entities
from main.testing_util import TEST_EMAIL
from main.testing_util import TEST_PASSWORD
from main.testing_util import TEST_USERNAME
from main.xhr_handlers import samples_upload_through_browser_sample_data
from main.xhr_handlers import upload_single_sample
from main.xhr_handlers import VARIANT_LIST_RESPONSE_KEY__ERROR
from main.xhr_handlers import VARIANT_LIST_RESPONSE_KEY__LIST
from main.xhr_handlers import VARIANT_LIST_RESPONSE_KEY__TOTAL
from main.xhr_handlers import VARIANT_LIST_RESPONSE_KEY__SET_LIST
from main.xhr_handlers import VARIANT_LIST_RESPONSE_KEY__KEY_MAP
from variants.dynamic_snp_filter_key_map import update_filter_key_map
from utils.import_util import _create_sample_and_placeholder_dataset
from utils.import_util import SAMPLE_BROWSER_UPLOAD_KEY__READ_1
from utils.import_util import SAMPLE_BROWSER_UPLOAD_KEY__READ_2
from utils.import_util import SAMPLE_BROWSER_UPLOAD_KEY__SAMPLE_NAME
from settings import PWD as GD_ROOT
from variants.melted_variant_schema import MELTED_SCHEMA_KEY__POSITION


TEST_DIR = os.path.join(GD_ROOT, 'test_data', 'genbank_aligned')
TEST_ANNOTATED_VCF = os.path.join(TEST_DIR, 'bwa_align_annotated.vcf')

STATUS_CODE__NOT_FOUND = 404
STATUS_CODE__NOT_LOGGED_IN = 302
STATUS_CODE__SUCCESS = 200


class TestGetVariantList(TestCase):

    url = reverse('main.xhr_handlers.get_variant_list')

    def setUp(self):
        # Useful models.
        user = User.objects.create_user(TEST_USERNAME, password=TEST_PASSWORD,
                email=TEST_EMAIL)
        self.project = Project.objects.create(owner=user.get_profile(),
                title='Test Project')
        self.ref_genome = ReferenceGenome.objects.create(project=self.project,
                label='refgenome', num_chromosomes=1, num_bases=1000)
        self.sample_obj_1 = ExperimentSample.objects.create(
                project=self.project, label='fake sample')

        # Make sure the reference genome has the required vcf keys.
        update_filter_key_map(self.ref_genome, TEST_ANNOTATED_VCF)
        self.vcf_dataset = Dataset.objects.create(
                label='test_data_set',
                type=Dataset.TYPE.VCF_FREEBAYES,
                filesystem_location=TEST_ANNOTATED_VCF)


        # Fake web browser client used to make requests.
        self.client = Client()
        self.client.login(username=TEST_USERNAME, password=TEST_PASSWORD)


    def test__logged_out(self):
        """Test that logged out fails.
        """
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(STATUS_CODE__NOT_LOGGED_IN, response.status_code)


    def test__missing_params(self):
        response = self.client.get(self.url)
        self.assertEqual(STATUS_CODE__NOT_FOUND, response.status_code)


    def test__basic_function(self):
        """Basic test.
        """
        alignment_group = AlignmentGroup.objects.create(
            label='Alignment 1',
            reference_genome=self.ref_genome,
            aligner=AlignmentGroup.ALIGNER.BWA)

        TOTAL_NUM_VARIANTS = 10
        for pos in range(TOTAL_NUM_VARIANTS):
            # We need all these models for testing because this is what the
            # materialized view create requires to return non-null results.
            variant = Variant.objects.create(
                    type=Variant.TYPE.TRANSITION,
                    reference_genome=self.ref_genome,
                    chromosome='chrom',
                    position=pos,
                    ref_value='A')

            VariantAlternate.objects.create(
                variant=variant,
                alt_value='G')

            common_data_obj = VariantCallerCommonData.objects.create(
                variant=variant,
                source_dataset=self.vcf_dataset,
                alignment_group=alignment_group)

            VariantEvidence.objects.create(
                experiment_sample=self.sample_obj_1,
                variant_caller_common_data=common_data_obj)

        # Sanity check that the Variants were actually created.
        self.assertEqual(TOTAL_NUM_VARIANTS, Variant.objects.filter(
                reference_genome=self.ref_genome,).count())

        request_data = {
            'refGenomeUid': self.ref_genome.uid,
            'projectUid': self.project.uid
        }
        response = self.client.get(self.url, request_data)

        self.assertEqual(STATUS_CODE__SUCCESS, response.status_code)

        response_data = json.loads(response.content)

        # Make sure expected keys in response.
        EXPECTED_RESPONSE_KEYS = set([
            VARIANT_LIST_RESPONSE_KEY__LIST,
            VARIANT_LIST_RESPONSE_KEY__TOTAL,
            VARIANT_LIST_RESPONSE_KEY__SET_LIST,
            VARIANT_LIST_RESPONSE_KEY__KEY_MAP,
        ])
        self.assertEqual(EXPECTED_RESPONSE_KEYS, set(response_data.keys()),
                "Missing keys %s\nGot keys %s" % (
                        str(EXPECTED_RESPONSE_KEYS -
                                set(response_data.keys())),
                        str(set(response_data.keys()))))

        self.assertEqual(TOTAL_NUM_VARIANTS,
                response_data[VARIANT_LIST_RESPONSE_KEY__TOTAL])

        # Check total variants returned is correct.
        variant_data_obj = json.loads(response_data[
                VARIANT_LIST_RESPONSE_KEY__LIST])
        variant_obj_list = variant_data_obj['obj_list']
        self.assertTrue(TOTAL_NUM_VARIANTS, len(variant_obj_list))

        # Check positions are correct.
        def _get_position_from_frontend_object(fe_obj):
            return int(re.match('([0-9]+)', str(fe_obj[
                    MELTED_SCHEMA_KEY__POSITION])).group(1))
        variant_position_set = set([_get_position_from_frontend_object(obj)
                for obj in variant_obj_list])
        self.assertEqual(set(range(TOTAL_NUM_VARIANTS)), variant_position_set)


    def test_does_not_throw_500_on_server_error(self):
        """For user input errors, get_variant_list should not throw a 500 error.

        This test might fail if the dev leaves the debugging clause
        "except FakeException" in the code.
        """
        request_data = {
            'refGenomeUid': self.ref_genome.uid,
            'projectUid': self.project.uid
        }
        response = self.client.get(self.url, request_data)
        self.assertEqual(STATUS_CODE__SUCCESS, response.status_code)
        response_data = json.loads(response.content)
        self.assertTrue(VARIANT_LIST_RESPONSE_KEY__ERROR in response_data)

        # Make sure FakeException is not imported
        with self.assertRaises(ImportError):
            # Don't leave FakeException as import.
            from main.xhr_handlers import FakeException


class TestModifyVariantInSetMembership(TestCase):
    """Tests for the modify_variant_in_set_membership() xhr endpoint.
    """

    def test_add__variants_specified(self):
        """Tests adding a specific list.
        """
        # TODO: Implement.
        pass

    def test_add__all_matching_filter(self):
        """Test adding all matching filter.
        """
        # TODO: Implement.
        pass


class TestUploadSingleSample(TestCase):

    def setUp(self):
        """Override.
        """
        self.common_entities = create_common_entities()

    def test_upload_single_sample(self):
        project = self.common_entities['project']
        request = HttpRequest()
        request.POST = {
            'projectUid': project.uid
        }
        request.method = 'POST'
        request.user = self.common_entities['user']
        authenticate(username=TEST_USERNAME, password=TEST_PASSWORD)
        self.assertTrue(request.user.is_authenticated())

        EXPERIMENT_SAMPLE_LABEL = 'my sample'
        request.POST['sampleLabel'] = EXPERIMENT_SAMPLE_LABEL

        request.FILES['fastq1'] = UploadedFile(
                file=StringIO.StringIO(),
                name='read1.fq')
        request.FILES['fastq2'] = UploadedFile(
                file=StringIO.StringIO(),
                name='read2.fq')

        response = upload_single_sample(request)
        self.assertEqual(STATUS_CODE__SUCCESS, response.status_code)
        self.assertFalse('error' in json.loads(response.content))

        sample = ExperimentSample.objects.get(label=EXPERIMENT_SAMPLE_LABEL)
        self.assertTrue(sample)

        datasets = sample.dataset_set.all()
        self.assertEqual(2, len(datasets))
        for dataset in datasets:
            self.assertEqual(Dataset.STATUS.READY, dataset.status)


class TestSamplesUploadThroughBrowserSampleData(TestCase):

    def setUp(self):
        """Override.
        """
        self.common_entities = create_common_entities()

    def test_upload_file(self):
        project = self.common_entities['project']
        request = HttpRequest()
        request.POST = {
            'projectUid': project.uid
        }
        request.method = 'POST'
        request.user = self.common_entities['user']
        authenticate(username=TEST_USERNAME, password=TEST_PASSWORD)
        self.assertTrue(request.user.is_authenticated())

        # Fake having uploaded a template.
        row_data = {
            SAMPLE_BROWSER_UPLOAD_KEY__SAMPLE_NAME: 'red',
            SAMPLE_BROWSER_UPLOAD_KEY__READ_1: 'red1.fq',
            SAMPLE_BROWSER_UPLOAD_KEY__READ_2: 'red2.fq'
        }
        _create_sample_and_placeholder_dataset(project, row_data)
        datasets = Dataset.objects.all()
        self.assertEqual(2, len(datasets))
        for dataset in datasets:
            self.assertEqual(Dataset.STATUS.AWAITING_UPLOAD, dataset.status)

        def _upload_file_and_check_response(name):
            # Add mock file to request.
            mock_uploaded_file = UploadedFile(
                    file=StringIO.StringIO(),
                    name=name)
            request.FILES = {
                'file': mock_uploaded_file
            }
            response = samples_upload_through_browser_sample_data(request)
            self.assertEqual(STATUS_CODE__SUCCESS, response.status_code)
            self.assertFalse('error' in json.loads(response.content))

        _upload_file_and_check_response('red1.fq')
        _upload_file_and_check_response('red2.fq')

        datasets = Dataset.objects.all()
        self.assertEqual(2, len(datasets))
        for dataset in datasets:
            self.assertEqual(Dataset.STATUS.READY, dataset.status)
