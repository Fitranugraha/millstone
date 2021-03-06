import os

from conf.global_settings import *

try:
    from conf.local_settings import *
except ImportError:
    pass

if not os.path.exists(MEDIA_ROOT):
    os.mkdir(MEDIA_ROOT)

# Use a default temp file root if none is set.
if 'TEMP_FILE_ROOT' not in locals():
    TEMP_FILE_ROOT = os.path.join(MEDIA_ROOT, 'tmp')
    if not os.path.exists(TEMP_FILE_ROOT):
        os.mkdir(TEMP_FILE_ROOT)

# Set the binaries here in case TOOLS_DIR is modified in local_settings.py
# TODO(gleb): What if users want to override specific binaries? Probably
# want a tools_settings.py.

SAMTOOLS_BINARY = '%s/samtools/samtools' % TOOLS_DIR

BGZIP_BINARY = '%s/tabix/bgzip' % TOOLS_DIR

FASTQC_BINARY = '%s/fastqc/fastqc' % TOOLS_DIR

VCFUNIQ_BINARY = '%s/freebayes/vcfuniq' % TOOLS_DIR

VCFSTREAMSORT_BINARY = '%s/freebayes/vcfstreamsort' % TOOLS_DIR

DELLY_BIN = '%s/delly/src/delly' % TOOLS_DIR

LUMPY_EXPRESS_BINARY = '%s/lumpy/lumpyexpress' % TOOLS_DIR

LUMPY_SCRIPTS_DIR = '%s/lumpy/scripts' % TOOLS_DIR

LUMPY_PAIREND_DISTRO_BIN = '%s/lumpy/scripts/pairend_distro.py' % TOOLS_DIR

LUMPY_EXTRACT_SPLIT_READS_BWA_MEM = (
        '%s/lumpy/scripts/extractSplitReads_BwaMem' % TOOLS_DIR)

# Merging lumpy vcfs

LUMPY_L_SORT_BINARY = os.path.join(LUMPY_SCRIPTS_DIR, 'l_sort.py')

LUMPY_L_MERGE_BINARY = os.path.join(LUMPY_SCRIPTS_DIR, 'l_merge.py')

### vcftools

VCFTOOLS_DIR = os.path.join(TOOLS_DIR, 'vcftools')

VCF_CONCAT_BINARY = os.path.join(VCFTOOLS_DIR, 'bin', 'vcf-concat')

VCF_SORT_BINARY = os.path.join(VCFTOOLS_DIR, 'bin', 'vcf-sort')

VCFLIB_DIR = os.path.join(TOOLS_DIR, 'vcflib')

VCF_COMBINE_BINARY = os.path.join(VCFLIB_DIR, 'vcfcombine')

# The location of the JBrowse scripts (perl scripts, ugh)
JBROWSE_BIN_PATH = os.path.join(JBROWSE_ROOT, 'bin')
