from fermi_blind_search.database import Database
from fermi_blind_search.configuration import get_config

def read_config_file():
   config_path = "path to config"
   configuration = get_config(config_path)
   return configuration

def test_analysis_row_with_missing_col():
    configuration = read_config_file()
    db = Database(configuration)
    analysis_to_add = {"duration": 1.2, "counts": 4, "outfile": "out.txt", "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)
    # do something to confirm that we get a failed assertion?
    # need to add other tests when other cols are missing?

def test_analysis_row_with_wrong_type_float():
    configuration = read_config_file()
    db = Database(configuration)
    analysis_to_add = {"met_start": "string", "duration": 1.2, "counts": 4, "outfile": "out.txt", "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)
    # do something to confirm we get a failed assertion

def test_analysis_row_with_wrong_type_int():
    configuration = read_config_file()
    db = Database(configuration)
    analysis_to_add = {"met_start": 1.2, "duration": 1.2, "counts": "string", "outfile": "out.txt",
                       "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)
    # do something to confirm we get a failed assertion

def test_analysis_row_with_wrong_type_string():
    configuration = read_config_file()
    db = Database(configuration)
    analysis_to_add = {"met_start": 1.2, "duration": 1.2, "counts": 4, "outfile": 1, "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)
    # do something to confirm we get a failed assertion

def test_result_row_with_missing_col():
    configuration = read_config_file()
    db = Database(configuration)
    result_to_add = {"interval": 4.7, "ra": 2.0, "dec": 9.2}
    db.add_candidate(result_to_add)
    # do something to confirm that we get a failed assertion?

def test_result_row_with_wrong_type_float():
    configuration = read_config_file()
    db = Database(configuration)
    result_to_add = {"met_start": "string", "interval": 4.7, "ra": 2.0, "dec": 9.2}
    db.add_candidate(result_to_add)
    # do something to confirm that we get a failed assertion?

def test_add_same_analysis_twice():
    configuration = read_config_file()
    db = Database(configuration)
    analysis_to_add = {"met_start": 45.0, "duration": 1.2, "counts": 4, "outfile": "out.txt", "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)
    db.add_analysis(analysis_to_add)