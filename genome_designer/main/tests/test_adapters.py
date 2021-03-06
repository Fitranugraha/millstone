"""
Tests for adapters.py
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase

from main.adapters import adapt_model_to_frontend
from main.models import Chromosome
from main.models import Project
from main.models import ReferenceGenome
from main.models import Variant
from main.models import VariantAlternate

class TestAdapters(TestCase):

    def setUp(self):
        """Override.
        """
        TEST_USERNAME = 'testuser'
        TEST_PASSWORD = 'password'
        TEST_EMAIL = 'test@example.com'
        user = User.objects.create_user(TEST_USERNAME, password=TEST_PASSWORD,
                email=TEST_EMAIL)

        TEST_PROJECT_NAME = 'recoli'
        test_project = Project.objects.create(
            title=TEST_PROJECT_NAME,
            owner=user.get_profile())

        REF_GENOME_1_LABEL = 'mg1655'
        self.ref_genome_1 = ReferenceGenome.objects.create(
            label=REF_GENOME_1_LABEL, project=test_project)

        self.chromosome = Chromosome.objects.create(
            reference_genome=self.ref_genome_1,
            label='Chromosome',
            num_bases=9001)

    def test_adapters__one_level(self):
        """Test adapting to a single level.
        """
        fe_ref_genomes = json.loads(adapt_model_to_frontend(
                ReferenceGenome, {'id': self.ref_genome_1.id}))

        self.assertTrue('field_config' in fe_ref_genomes)
        self.assertTrue('obj_list' in fe_ref_genomes)
        self.assertEqual(1, len(fe_ref_genomes['obj_list']))
        ref_genome_1_fe = fe_ref_genomes['obj_list'][0]
        for field in ReferenceGenome.get_field_order():
            self.assertTrue(field['field'] in ref_genome_1_fe)
        self.assertTrue('href' in ref_genome_1_fe)
