#!/usr/bin/env python

"""
Setup script.
"""

import os
import platform
import re
import stat
import sys
import urllib
import zipfile

# Setup Django environment.
sys.path.append(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), '../'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.conf import settings


# Retry download at least X times if disconnected.
MAX_DL_RETRY = 3

TOOLS_URLS = {
    'bwa' : {
        'Darwin': ['https://www.dropbox.com/s/13a3dm5yfi7dpb5/bwa'],
        'Linux': ['https://www.dropbox.com/s/ai55jpxgepx0j3u/bwa'],
    },
    'freebayes' : {
        # we use the following tools in the freebayes git repo (+submodules):
        # * freebayes
        # * bamleftalign
        # * vcfstreamsort (from vcflib)
        # * vcfuniq (from vcflib)
        'Darwin' : [
            'https://www.dropbox.com/s/gf2a9346ht9mf9w/bamleftalign',
            'https://www.dropbox.com/s/4zxizm39sadkrbh/freebayes',
            'https://www.dropbox.com/s/q2wcgnvg6f74jmf/vcfstreamsort',
            'https://www.dropbox.com/s/dgck2iz7mmikrwq/vcfuniq'

        ],
        'Linux' : [
            'https://www.dropbox.com/s/g5b3uuyu38esvfy/bamleftalign',
            'https://www.dropbox.com/s/4h6ijp2rrnyckc5/freebayes',
            'https://www.dropbox.com/s/6pxdpgjyop2n7vx/vcfstreamsort',
            'https://www.dropbox.com/s/kf5uxydrpbqbkg9/vcfuniq'
        ],
    },
    'snpEff': [
        'https://www.dropbox.com/s/lqxnvpf9x8ja19j/snpEff-4.2.zip'
    ],
    'samtools' : {
        'Darwin' : [
            'https://www.dropbox.com/s/yhx7ijj0goi9as4/samtools-0.1.20-darwin.zip'
        ],
        'Linux' : [
            'https://www.dropbox.com/s/bihunqakuxv2nld/samtools-0.1.20-linux.zip'
        ]
    },
    'tabix' : {
        'Darwin' : [
            'https://www.dropbox.com/s/tqfvpgy73cgdbir/tabix-0.2.4-darwin.zip'
        ],
        'Linux': [
            'https://www.dropbox.com/s/e2cwt9n0ixbuff0/tabix-0.2.4-linux.zip'
        ]
    },
    'pindel' : {
        'Darwin' : [
            'https://www.dropbox.com/s/gfvyc52rgl9e9c4/pindel-darwin.zip'
        ],
        'Linux' : [
            'https://www.dropbox.com/s/tkwfzlfgx7qhqek/pindel-linux.zip'
        ]
    },
    'vcf-concat': {
        'Darwin' : [
            'https://www.dropbox.com/s/uacjkfgnpgd5123/vcf-concat-darwin.zip'
        ],
        'Linux' : [
            'https://www.dropbox.com/s/chrc988wwz8dp2c/lumpy-0.2.11-darwin.zip'
        ]
    },
    'lumpy' : {
        'Darwin' : [
            'https://www.dropbox.com/s/chrc988wwz8dp2c/lumpy-0.2.11-darwin.zip'
        ],
        'Linux' : [
            'https://www.dropbox.com/s/dbgjw59xcum1jru/lumpy-0.2.11-linux.zip'
        ]
    },
    'fastqc' : [
        'https://www.dropbox.com/s/oqkh460vri7zuh1/fastqc_v0.11.2.zip'
    ],
    'samblaster': {
        'Darwin': [
            'https://www.dropbox.com/s/hcns1lcp1ows52w/samblaster'
        ],
        'Linux': [
            'https://www.dropbox.com/s/ia8z8ib0fxnsaft/samblaster'
        ]
    },
    'vcflib': {
        'Darwin': [
            'https://www.dropbox.com/s/efbprgj2fmgy5ck/vcflib-32be8fc-darwin.zip'
        ],
        'Linux': [
            'https://www.dropbox.com/s/8wzv39ifu3d7pts/vcflib-32be8fc-linux.zip'
        ]
    },
    'velvet': {
        'Darwin': [
            'https://www.dropbox.com/s/ff3g2j46tr8rf2w/velvet-darwin.zip'
        ],
        'Linux': [
            'https://www.dropbox.com/s/wxxcjruhjfzy5wz/velvet-linux.zip'
        ]
    }
}


# For any tools that have multiple executables that need permission changes,
# for tools whose executables aren't named after their tool
TOOLS_TO_EXECUTABLES = {
    'lumpy': ['*'], # make all executable
    'pindel': ['pindel', 'pindel2vcf'],
    'tabix': ['tabix', 'bgzip'],
    'freebayes': ['freebayes', 'vcfstreamsort', 'vcfuniq'],
    'velvet': ['velvetg', 'velveth', 'extractContigReads.pl'],
    'vcflib': ['*'],
}


def setup(arglist):
    if len(arglist) == 0:
        download_tools()
        setup_jbrowse()
    elif 'tools' in arglist:
        download_tools()
    else:
        if 'jbrowse' in arglist:
            setup_jbrowse()
            arglist.remove('jbrowse')
        download_tools(tools=arglist)


def download_tools(tools=TOOLS_URLS.keys(), tools_dir=settings.TOOLS_DIR):
    # Create tools dir if it doesn't exist.
    if not os.path.isdir(tools_dir):
        os.mkdir(tools_dir)

    sys_type = platform.system()

    # Download the required tools from our Dropbox.
    for tool in tools:

        print 'Grabbing %s from Dropbox...' % tool

        # If the tool is a dict, then it references different OSes (i.e.
        # compiled binaries). Download the correct one for your OS.
        if isinstance(TOOLS_URLS[tool],dict):
            try:
                tool_urls = TOOLS_URLS[tool][sys_type]
            except KeyError, e:
                raise(OSError(' '.join([
                    'Tool "%s" missing for your OS (%s),'
                    'OSs available are: (%s)']) % (
                        tool, sys_type, str(TOOLS_URLS[tool].keys()))))
        else:
            tool_urls = TOOLS_URLS[tool]

        # Make the directory for this tool, if it doesn't exist
        dest_dir = _get_or_create_tool_destination_dir(tool, tools_dir)

        for tool_url in tool_urls:

            # Grab last part of url after final '/' as file name
            dest_filename = re.match(r'^.*\/([^/]+)$', tool_url).group(1)

            # Get the *actual* file URL from the dropbox popup
            tool_url = _get_file_url_from_dropbox(tool_url, dest_filename)

            # If *.zip, download to a tmp file and unzip it to the right dir.
            if dest_filename.endswith('.zip'):
                tmp_path, http_msg = _try_urlretrieve(tool_url)
                print '    %s (Unzipping...)' % tmp_path
                try:
                    tool_zipped = zipfile.ZipFile(tmp_path)
                    tool_zipped.extractall(dest_dir)
                except:
                    raise(OSError('File {} missing or invalid format!'.format(
                            tool_url)))

            # Otherwise download files to the correct location.
            else:
                dest_path = os.path.join(dest_dir, dest_filename)
                try:
                    _, http_msg = _try_urlretrieve(tool_url, dest_path)
                except IOError as e:
                    print '    Error downloading %s' % tool_url
                    print '    Aborting setup. Please retry.'
                    raise e
                print '    %s' % dest_path

        _update_executable_permissions(tool, tools_dir)


def _try_urlretrieve(tool_url, dest_path=None, retry=0):
    """Allow retrying urllib.urlretrieve in case connection drops."""
    try:
        if dest_path is None:
            download_path, http_msg = urllib.urlretrieve(tool_url)
        else:
            download_path, http_msg = urllib.urlretrieve(tool_url, dest_path)

    except IOError as e:
        # attempt retry
        if retry < MAX_DL_RETRY:
            print '    Connection failed, retry #{}'.format(retry + 1)
            return _try_urlretrieve(
                    tool_url, dest_path=dest_path, retry=retry + 1)
        else:
            raise e

    # Check that the result is not an HTML error page
    HTML_DOC_STR = '<!DOCTYPE html>'
    with open(download_path) as fh:
        if fh.readline()[:len(HTML_DOC_STR)] == HTML_DOC_STR:
            raise ValueError('Binary %s missing from Dropbox.' % tool_url)

    return download_path, http_msg


def _get_or_create_tool_destination_dir(tool, tools_dir):
    dest_dir = os.path.join(tools_dir, tool)
    if not os.path.isdir(dest_dir):
        os.mkdir(dest_dir)
    return dest_dir


def _get_file_url_from_dropbox(dropbox_url, filename):
    """Dropbox now supports modifying the shareable url with a simple
    param that will allow the tool to start downloading immediately.
    """
    return dropbox_url + '?dl=1'


def _update_executable_permissions(tool, tools_dir):
    """Set executable permissions lost during zip.

    This is really hackish, but because ZipFile does not save file
    permissions, we need to make the bins executable. In cases where
    the executable name is different than the tool key in TOOL_URLS,
    use TOOLS_TO_EXECUTABLES.
    """
    # Location of tool files.
    dest_dir = _get_or_create_tool_destination_dir(tool, tools_dir)

    # Gather full paths of all files to make executable.
    if not tool in TOOLS_TO_EXECUTABLES:
        # By default, tool binary is name of the tool.
        tool_bin_paths = [os.path.join(dest_dir, tool)]
    elif '*' in TOOLS_TO_EXECUTABLES[tool]:
        # tool_bin_files = [exe for exe in os.listdir(dest_dir)]
        tool_bin_paths = []
        walk_results = [exe for exe in os.walk(dest_dir)]
        for root, dirs, files in walk_results:
            for f in files:
                tool_bin_paths.append(os.path.join(root, f))
    else:
        tool_bin_paths = [os.path.join(dest_dir, exe) for exe in
                TOOLS_TO_EXECUTABLES[tool]]

    # Set executable permissions.
    for tbp in tool_bin_paths:
        # Some packages just have .jars which don't need permissions changed.
        if os.path.exists(tbp):
            os.chmod(tbp, stat.S_IXUSR | stat.S_IWUSR | stat.S_IRUSR)


def setup_jbrowse():
    """Sets up JBrowse.
    """
    # Unlink if there was a link and then create a new link.
    try:
        os.unlink(settings.JBROWSE_DATA_SYMLINK_PATH)
    except OSError:
        # There was no symlink. That's fine.
        pass

    # Re-create the link.
    os.symlink(os.path.join(settings.PWD, settings.MEDIA_ROOT),
            settings.JBROWSE_DATA_SYMLINK_PATH)

if __name__ == '__main__':
    setup(sys.argv[1:])
