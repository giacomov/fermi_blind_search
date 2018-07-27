from fermi_blind_search.database import Database
from fermi_blind_search.configuration import get_config
import pytest

def read_config_file():
   config_path = "/home/suli_students/suli_jamie/config_test.txt"
   configuration = get_config(config_path)
   return configuration

def test_setup():
    configuration = read_config_file()
    db = Database(configuration)
    db.create_tables()

def test_analysis_row_with_missing_col():
    configuration = read_config_file()
    db = Database(configuration)
    analysis_to_add = {"duration": 1.2, "counts": 4, "outfile": "out.txt", "logfile": "log.txt"}
    with pytest.raises(KeyError):
        db.add_analysis(analysis_to_add)
    # do something to confirm that we get a failed assertion?
    # need to add other tests when other cols are missing?

# def test_analysis_row_with_wrong_type_float():
#     configuration = read_config_file()
#     db = Database(configuration)
#     analysis_to_add = {"met_start": "string", "duration": 1.2, "counts": 4, "outfile": "out.txt", "logfile": "log.txt"}
#     with pytest.raises(Exception):
#         db.add_analysis(analysis_to_add)
#     # do something to confirm we get a failed assertion
#
# def test_analysis_row_with_wrong_type_int():
#     configuration = read_config_file()
#     db = Database(configuration)
#     analysis_to_add = {"met_start": 1.2, "duration": 1.2, "counts": "string", "outfile": "out.txt",
#                        "logfile": "log.txt"}
#     # TODO: figure out how to do type checking
#
# def test_analysis_row_with_wrong_type_string():
#     configuration = read_config_file()
#     db = Database(configuration)
#     analysis_to_add = {"met_start": 1.2, "duration": 1.2, "counts": 4, "outfile": 1, "logfile": "log.txt"}
#     with pytest.raises(Exception):
#         db.add_analysis(analysis_to_add)
#     # do something to confirm we get a failed assertion

def test_result_row_with_missing_col():
    configuration = read_config_file()
    db = Database(configuration)
    result_to_add = {"interval": 4.7, "ra": 2.0, "dec": 9.2}
    with pytest.raises(KeyError):
        db.add_candidate(result_to_add)
    # do something to confirm that we get a failed assertion?

# def test_result_row_with_wrong_type_float():
#     configuration = read_config_file()
#     db = Database(configuration)
#     result_to_add = {"met_start": "string", "interval": 4.7, "ra": 2.0, "dec": 9.2}
#     with pytest.raises(Exception):
#         db.add_candidate(result_to_add)
#     # do something to confirm that we get a failed assertion?

def test_add_same_analysis_twice():
    configuration = read_config_file()
    db = Database(configuration)
    analysis_to_add = {"met_start": 45.1, "duration": 1.2, "counts": 4, "outfile": "out.txt", "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)
    with pytest.raises(Exception):
        db.add_analysis(analysis_to_add)

def test_add_same_result_twice():
    configuration = read_config_file()
    db = Database(configuration)
    result_to_add = {"met_start": 4.8, "interval": 4.7, "ra": 2.0, "dec": 9.2, "email": False}
    db.add_candidate(result_to_add)
    with pytest.raises(Exception):
        db.add_candidate(result_to_add)

def test_get_results():
    configuration = read_config_file()
    db = Database(configuration)
    result_to_add = {"met_start": 120.9, "interval": 4.7, "ra": 2.0, "dec": 9.2, "email": False}
    result_to_add2 = {"met_start": 125.1, "interval": 5.2, "ra": 3.0, "dec": 10.2, "email": True}
    result_to_add3 = {"met_start": 135.1, "interval": 9.2, "ra": 3.0, "dec": 10.2, "email": False}
    db.add_candidate(result_to_add)
    db.add_candidate(result_to_add2)
    db.add_candidate(result_to_add3)
    search_vals = {"met_start": 123, "interval": 5, "ra": 2.5, "dec": 10}
    results = db.get_results(search_vals)
    results_list = []
    for row in results:
        results_list.append({"met_start": row.met_start, "interval": row.interval, "ra": row.ra, "dec": row.dec,
                             "email": row.email})

    assert len(results_list) == 2, "incorrect number of results"
    assert (result_to_add in results_list) and (result_to_add2 in results_list) and \
           (result_to_add3 not in results_list), "intended results not in list"

def test_get_analyses():
    configuration = read_config_file()
    db = Database(configuration)
    analysis_to_add = {"met_start": 145.1, "duration": 100.2, "counts": 45, "outfile": "out.txt", "logfile": "log.txt"}
    analysis_to_add2 = {"met_start": 150.1, "duration": 95.0, "counts": 70, "outfile": "out.txt", "logfile": "log.txt"}
    analysis_to_add3 = {"met_start": 5.1, "duration": 95.0, "counts": 70, "outfile": "out.txt", "logfile": "log.txt"}

    db.add_analysis(analysis_to_add)
    db.add_analysis(analysis_to_add2)
    db.add_analysis(analysis_to_add3)
    results = db.get_analysis_between_times(130, 270)
    results_list = []
    for row in results:
        results_list.append({"met_start": row.met_start, "duration": row.duration, "counts": row.counts,
                             "outfile": row.outfile, "logfile": row.logfile})
    assert len(results_list) == 2, "incorrect number of results"
    assert (analysis_to_add in results_list) and (analysis_to_add2 in results_list) and \
           (analysis_to_add3 not in results_list)

def test_get_results_to_email():
    configuration = read_config_file()
    db = Database(configuration)
    result_to_add = {"met_start": 120.9, "interval": 4.7, "ra": 2.0, "dec": 9.2, "email": False}
    result_to_add2 = {"met_start": 125.1, "interval": 5.2, "ra": 3.0, "dec": 10.2, "email": True}
    result_to_add3 = {"met_start": 135.1, "interval": 9.2, "ra": 3.0, "dec": 10.2, "email": False}
    result_to_add4 = {"met_start": 4.8, "interval": 4.7, "ra": 2.0, "dec": 9.2, "email": False}
    # db.add_candidate(result_to_add)
    # db.add_candidate(result_to_add2)
    # db.add_candidate(result_to_add3)

    results = db.get_results_to_email()
    assert len(results) == 3
    results_list = []
    for row in results:
        results_list.append({"met_start": row.met_start, "interval": row.interval, "ra": row.ra, "dec": row.dec,
                             "email": row.email})
    assert len(results_list) == 3
    assert (result_to_add in results_list) and (result_to_add3 in results_list) and (result_to_add2 not in results_list)


def test_change_email():
    configuration = read_config_file()
    db = Database(configuration)
    result_to_add = {"met_start": 120.9, "interval": 4.7, "ra": 2.0, "dec": 9.2, "email": False}
    result_to_add2 = {"met_start": 125.1, "interval": 5.2, "ra": 3.0, "dec": 10.2, "email": True}
    result_to_add3 = {"met_start": 135.1, "interval": 9.2, "ra": 3.0, "dec": 10.2, "email": False}
    # db.add_candidate(result_to_add)
    # db.add_candidate(result_to_add2)
    # db.add_candidate(result_to_add3)

    results = db.get_results_to_email()
    assert len(results) == 3
    results_list = []
    row_to_change = None
    for row in results:
        results_list.append({"met_start": row.met_start, "interval": row.interval, "ra": row.ra, "dec": row.dec,
                             "email": row.email})
        if not row.email:
            row_to_change = row

    assert (result_to_add in results_list) and (result_to_add3 in results_list) and (result_to_add2 not in results_list)

    db.update_result_email(row_to_change, email_val=True)
    results = db.get_results_to_email()
    assert row_to_change not in results


def test_cleanup():
    configuration = read_config_file()
    db = Database(configuration)
    db.delete_analysis_table()
    db.delete_results_table()
