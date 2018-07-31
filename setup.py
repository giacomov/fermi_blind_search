from setuptools import setup

import glob

data_files = ['data/grid.fits', 'data/logging.yaml']

# Add all ROI data files
data_files.extend(glob.glob('fermi_blind_search/data/ROIBackgroundEstimator_data/*.npz'))

setup(
    name='fermi_blind_search',
    version='1.0',
    packages=['scripts',
              'fermi_blind_search',
              'fermi_blind_search.bkge',
              'fermi_blind_search.batch',
              'fermi_blind_search.grid_creation',
              'fermi_blind_search.fits_handling'],
    author='giacomov',
    author_email='giacomov@stanford.edu',
    description='',
    scripts=glob.glob('scripts/*.py'),

    package_data={
              'fermi_blind_search': data_files,
           },
    include_package_data=True,
    install_requires=[
            'numpy >= 1.6',
            'scipy >=0.18',
            'astropy>=1.3.3',
            'matplotlib',
            'numexpr',
            'pyyaml',
            'fitsio',
            'sqlalchemy',
            'pymysql',
            'sshtunnel'
        ]
)
