"""
Utils for working with ReferenceGenome maker.
"""

import os
import tempfile

from django.conf import settings
from reference_genome_maker import vcf_to_genbank

from main.exceptions import ValidationException
from main.model_utils import clean_filesystem_location
from main.models import Dataset
from main.models import ReferenceGenome
from utils import generate_safe_filename_prefix_from_label
from utils.data_export_util import export_variant_set_as_vcf
from utils.data_export_util import PLACEHOLDER_SAMPLE_NAME
from utils.import_util import prepare_ref_genome_related_datasets


def generate_new_reference_genome(variant_set, new_ref_genome_params):
    """Uses reference_genome_maker code to create a new ReferenceGenome
    from the given VariantSet (applies Variants to existing ReferenceGenome.)

    Args:
        variant_set: The VariantSet from which we'll generate the new
            ReferenceGenome.
        new_ref_genome_params: Dictionary of params, including:
            * label (required): Label for the new ReferenceGenome.

    Returns:
        The new ReferenceGenome.

    Raises:
        ValidationException if we don't support this use case.
    """
    try:
        # Validate / parse params.
        assert 'label' in new_ref_genome_params
        new_ref_genome_label = new_ref_genome_params['label']

        original_ref_genome = variant_set.reference_genome

        # Create a ReferenceGenome to track the position.
        reference_genome = ReferenceGenome.objects.create(
                project=original_ref_genome.project,
                label=new_ref_genome_label,
                num_chromosomes=original_ref_genome.num_chromosomes,
                num_bases=-1 # Set this after ReferenceGenome is created.
        )

        # Location for the generated Genbank.
        filename_prefix = generate_safe_filename_prefix_from_label(
                new_ref_genome_label)
        output_root = os.path.join(reference_genome.get_model_data_dir(),
                filename_prefix)
        full_output_path = clean_filesystem_location(output_root + '.genbank')

        # Dataset to track the location.
        dataset = Dataset.objects.create(
                label=Dataset.TYPE.REFERENCE_GENOME_GENBANK,
                type=Dataset.TYPE.REFERENCE_GENOME_GENBANK,
                filesystem_location=full_output_path,
                status=Dataset.STATUS.NOT_STARTED)
        reference_genome.dataset_set.add(dataset)

        # Prepare params for calling referece_genome_maker.
        original_genbank_path = original_ref_genome.dataset_set.get(
                type=Dataset.TYPE.REFERENCE_GENOME_GENBANK).\
                        get_absolute_location()

        filename_prefix = generate_safe_filename_prefix_from_label(
                new_ref_genome_label)
        output_root = os.path.join(reference_genome.get_model_data_dir(),
                filename_prefix)

        # Create a fake, empty vcf path for now, as we're just getting
        # end-to-end to work.
        if not os.path.exists(settings.TEMP_FILE_ROOT):
            os.mkdir(settings.TEMP_FILE_ROOT)
        _, vcf_path = tempfile.mkstemp(
                suffix='_' + filename_prefix + '.vcf',
                dir=settings.TEMP_FILE_ROOT)

        export_variant_set_as_vcf(variant_set, vcf_path)

        sample_id = PLACEHOLDER_SAMPLE_NAME

        dataset.status = Dataset.STATUS.COMPUTING
        dataset.save(update_fields=['status'])

        try:
            new_ref_genome_seq_record = vcf_to_genbank.run(
                    original_genbank_path, output_root, vcf_path, sample_id)
        except Exception as e:
            dataset.status = Dataset.STATUS.FAILED
            dataset.save(update_fields=['status'])
            raise e

        reference_genome.num_bases = len(new_ref_genome_seq_record)
        reference_genome.save(update_fields=['num_bases'])
        dataset.status = Dataset.STATUS.READY
        dataset.save(update_fields=['status'])

        # Since the post_add_seq_to_ref_genome() signal couldn't run before,
        # we need to make sure to run it now.
        prepare_ref_genome_related_datasets(reference_genome, dataset)

        return reference_genome

    except Exception as e:
        raise ValidationException(str(e))