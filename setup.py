import os.path
from setuptools import find_packages, setup


def in_this_dir(basename):
    return os.path.join(os.path.dirname(__file__), basename)


def get_version():
    init_file = os.path.join(in_this_dir('nlmaps_tools'), '__init__.py')
    version_indicator = '__version__ = '
    with open(init_file) as f:
        for line in f:
            if line.startswith(version_indicator):
                version_part = line[len(version_indicator):]
                version = version_part.strip().strip("'").strip('"')
                return version
        else:
            raise RuntimeError('No version found in {}'.format(init_file))


with open(in_this_dir('README.md')) as f:
    LONG_DESCRIPTION = f.read()

with open(in_this_dir('requirements.txt')) as f:
    REQUIREMENTS = [line.strip() for line in f
                    if not line.strip().startswith('#')]

VERSION = get_version()

setup(
    name='nlmaps_tools',
    version=VERSION,
    packages=find_packages(),
    long_description=LONG_DESCRIPTION,
    include_package_data=True,
    install_requires=REQUIREMENTS,
)
