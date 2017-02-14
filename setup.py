from distutils.core import setup

setup(
    name='fermi_blind_search',
    version='1.0',
    packages=['scripts', 'fermi_blind_search', 'fermi_blind_search.bkge', 'fermi_blind_search.batch',
              'fermi_blind_search.grid_creation'],
    author='giacomov',
    author_email='giacomov@stanford.edu',
    description='',
    scripts=['scripts/ltfsearch.py']
)
