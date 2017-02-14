from setuptools import setup

import glob

data_files = ['data/grid.fits', 'data/logging.yaml']

# Add all ROI data files
data_files.extend(glob.glob('fermi_blind_search/data/ROIBackgroundEstimator_data/*.npz'))

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
              'fermi_blind_search': data_files,
           },
    include_package_data=True,
)
