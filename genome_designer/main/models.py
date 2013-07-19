"""Database models.

Note on filesystem directory structure: (IN PROGRESS)

    Since we are storing data output from various bioinformatics programs, the
    models below result in the creation and maintenance of a directory
    structure for data location. In general, the strategy is to have a
    directory corresponding to a model instance when possible. Hierarchy
    is used when models can be properly nested.

    An example layout for a user's data might look like:
        /users/1234abcd/projects/1324abcd/
        /users/1234abcd/projects/1324abcd/alignments/
        /users/1234abcd/projects/1324abcd/samples/
        /users/1234abcd/projects/1324abcd/samples/1234abcd
        /users/1234abcd/projects/1324abcd/samples/5678jklm
        /users/1234abcd/projects/1324abcd/ref_genomes/
        /users/1234abcd/projects/1324abcd/variant_calls/
"""

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Model
from django.db.models.signals import post_save


###############################################################################
# Utilities
###############################################################################

def short_uuid(cls):
    """Generates a short uuid, repeating if necessary to maintain
    uniqueness.

    This is passed as the value of the default argument to any model
    with a uid field.

    NOTE: I thought I could make this a @classmethod but I don't think it's
    possible to access the instance class at the scope where model fields
    are declared.
    """
    UUID_SIZE = 8

    # Even with a short id, the probability of collision is very low,
    # but timeout just in case rather than risk locking up.
    timeout = 0
    while timeout < 1000:
        initial_long = str(uuid4())
        candidate = initial_long[:UUID_SIZE]
        if len(cls.objects.filter(uid=candidate)) == 0:
            return candidate
        else:
            timeout += 1
    raise RuntimeError, "Too many short_uuid attempts."


###############################################################################
# User-related models
###############################################################################

class UserProfile(Model):
    """A UserProfile which is separate from the django auth User.

    This references the auth.User and opens up the possibility of
    adding additional fields.
    """
    # A one-to-one mapping to the django User model.
    user = models.OneToOneField(User)


# Since the registration flow creates a django User object, we want to make
# sure that the corresponding UserProfile is also created
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        user_profile = UserProfile.objects.create(user=instance)
post_save.connect(create_user_profile, sender=User,
        dispatch_uid='gdportal.main.models')


###############################################################################
# Data wrappers
###############################################################################

class Dataset(Model):
    """A specific dataset with a location on the filesystem.

    Basically a wrapper for a file on the file system.

    This is similar to the Galaxy notion of a dataset.
    """
    pass


###############################################################################
# Project models
###############################################################################

class Project(Model):
    """A single project belonging to a user.

    A project groups together ReferenceGenomes, ExperimentSamples, and other
    data generated by tools during analysis.
    """
    pass


class ReferenceGenome(Model):
    """A reference genome relative to which alignments and analysis are
    performed.
    """
    pass


class ExperimentSample(Model):
    """Model representing data for a particular experiment sample.

    Usually this corresponds to a pair of fastq reads for a particular colony,
    after de-multiplexing.
    """
    pass


class Alignment(Model):
    """Alignment of an ExperimentSample to a ReferenceGenome.
    """
    pass


###############################################################################
# Variants (SNVs and SVs)
###############################################################################

class Variant(Model):
    """An instance of a variation relative to a reference genome.

    This might be, for example, a SNV (single nucleotide variation) or a bigger
    SV (structural variation). We are intentionally using a unified model for
    these two classes of variations as the fundamental unit of genome analysis
    is really a diff.

    TODO: See code from Gemini paper (PLOS ONE 7/18/13) for ideas.

    A variant need not necessarily be associated with a specific sample; the
    VariantToExperimentSample model handles this association.
    """
    pass


class VariantToExperimentSample(Model):
    """Model that represents the relationship between a particular Variant
    and a particular ExperimentSample.
    """
    pass


class VariantCallerCommonData(Model):
    """Model that describes data provided by a specific caller about a
    particular Variant.

    The reason for this model is that most variant callers are run for multiple
    ExperientSamples at the same time, generating some common data for each
    variant found, as well as data unique to each ExperimentSample. This model
    represents the common shared data.

    To be even more specific, the VCF format typically gives a row for each
    variant, where some of the columns describe the variant, while other
    columns have a one-to-one correspondence to the alignments provided.
    """
    pass


class VariantEvidence(Model):
    """Evidence for a particular variant occurring in a particular
    ExperimentSample.
    """
    pass


###############################################################################
# Analysis
###############################################################################

class VariantSet(Model):
    """Model for grouping together variants for analysis.

    This object can also be thought of a 'tag' for a set of variants. For
    example, we might create a VariantSet called 'c321D Designed Changes'
    to represent the set of Variants that were intended for mutation.
    """
    pass


class VariantFilter(Model):
    """Model used to save a string representation of a filter used to sift
    through Variants.
    """
    pass
