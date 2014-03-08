"""
Tests for sv_calling.py
"""

import os

from django.test import TestCase
from django.test.utils import override_settings
import vcf

from main.models import AlignmentGroup
from main.models import Dataset
from main.models import ExperimentSample
from main.models import ExperimentSampleToAlignment
from main.models import get_dataset_with_type
from main.models import Project
from main.models import User
from main.models import Variant
from pipeline.snv_calling import get_variant_tool_params
from pipeline.snv_calling import find_variants_with_tool
from scripts.import_util import add_dataset_to_entity
from scripts.import_util import copy_and_add_dataset_source
from scripts.import_util import copy_dataset_to_entity_data_dir
from scripts.import_util import import_reference_genome_from_local_file
from settings import PWD as GD_ROOT


TEST_FASTA  = os.path.join(GD_ROOT, 'test_data', 'sv_testing', 'small_data',
        'ref.fa')

TEST_FASTQ1 = os.path.join(GD_ROOT, 'test_data', 'sv_testing', 'small_data',
        'simLibrary.1.fq')

TEST_FASTQ2 = os.path.join(GD_ROOT, 'test_data', 'sv_testing', 'small_data',
        'simLibrary.2.fq')

TEST_SAMPLE_UID = '38d786f2'

TEST_BAM = os.path.join(GD_ROOT, 'test_data', 'sv_testing', 'small_data',
        'final.bam')

TEST_BAM_INDEX = os.path.join(GD_ROOT, 'test_data', 'sv_testing', 'small_data',
        'final.bam.bai')


class TestSVCallers(TestCase):

    def setUp(self):
        user = User.objects.create_user('test_username', password='password',
                email='test@example.com')

        # Grab a project.
        self.project = Project.objects.create(title='test project',
                owner=user.get_profile())

        # Create a ref genome.
        self.reference_genome = import_reference_genome_from_local_file(
                self.project, 'ref_genome', TEST_FASTA, 'fasta')


    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS = True,
        CELERY_ALWAYS_EAGER = True, BROKER_BACKEND = 'memory')
    def test_call_svs(self):
        """Test running the pipeline that finds structural variants.

        This test doesn't check the accuracy of the SV-calling. The test is
        intended just to run the pipeline and make sure there are no errors.
        """
        # Create a new alignment group.
        alignment_group = AlignmentGroup.objects.create(
                label='test alignment', reference_genome=self.reference_genome)

        # Create a sample.
        sample_1 = ExperimentSample.objects.create(
                uid=TEST_SAMPLE_UID,
                project=self.project,
                label='sample1')
        ### Add the raw reads
        copy_and_add_dataset_source(sample_1, Dataset.TYPE.FASTQ1,
                Dataset.TYPE.FASTQ1, TEST_FASTQ1)
        copy_and_add_dataset_source(sample_1, Dataset.TYPE.FASTQ2,
                Dataset.TYPE.FASTQ2, TEST_FASTQ2)

        # Create relationship between alignment and sample.
        sample_alignment = ExperimentSampleToAlignment.objects.create(
                alignment_group=alignment_group,
                experiment_sample=sample_1)
        ### Add alignment data. NOTE: Stored in sample model dir.
        copy_dest = copy_dataset_to_entity_data_dir(sample_1, TEST_BAM)
        copy_dataset_to_entity_data_dir(sample_1, TEST_BAM_INDEX)
        add_dataset_to_entity(sample_alignment, Dataset.TYPE.BWA_ALIGN,
                Dataset.TYPE.BWA_ALIGN, copy_dest)

        # Make sure there are no variants before.
        self.assertEqual(0, len(Variant.objects.filter(
                reference_genome=self.reference_genome)))

        # Run the pipeline.
        for variant_params in get_variant_tool_params()[1:3]:  # pindel & delly
            find_variants_with_tool(alignment_group, variant_params, project=self.project)

        # Check that the alignment group has a freebayes vcf dataset associated
        # with it.
        vcf_dataset = get_dataset_with_type(alignment_group,
                Dataset.TYPE.VCF_PINDEL)
        self.assertIsNotNone(vcf_dataset)

        # Make sure the .vcf file actually exists.
        self.assertTrue(os.path.exists(vcf_dataset.get_absolute_location()))

        # Make sure the vcf is valid by reading it using pyvcf.
        with open(vcf_dataset.get_absolute_location()) as vcf_fh:
            try:
                reader = vcf.Reader(vcf_fh)
                reader.next()
            except:
                self.fail("Not valid vcf")

        # Grab the resulting variants.
        variants = Variant.objects.filter(reference_genome=self.reference_genome)

        # Check that we have one structural variant deletion.
        self.assertEqual(1, len(variants))
        self.assertEqual(13120, variants[0].position)
        self.assertEqual('DELETION', variants[0].type)

