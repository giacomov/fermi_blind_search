from distutils.core import setup

import glob

setup(
    name='fermi_blind_search',
    version='1.0',
    packages=['scripts', 'fermi_blind_search', 'fermi_blind_search.bkge', 'fermi_blind_search.batch',
              'fermi_blind_search.grid_creation'],
    author='giacomov',
    author_email='giacomov@stanford.edu',
    description='',
    scripts=glob.glob('scripts/*.py'),

    package_data={
              'fermi_blind_search': ['data/grid.fits', 'data/logging.yaml'],
           },
    include_package_data=True,
)
