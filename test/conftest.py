import pytest
import os
from fermi_blind_search.configuration import get_config


@pytest.fixture(scope='session')
def config_file():

    config_path = os.environ['LTF_BLIND_TEST_CONFIG']
    configuration = get_config(config_path)

    return configuration