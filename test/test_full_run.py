import subprocess
import os
import shutil

from fermi_blind_search.which import which
from fermi_blind_search.database import Database
from fermi_blind_search.configuration import get_config
from ltf_real_time import rerun_analysis

_config_path = "/home/suli_students/suli_jamie/config_test.txt"

# def test_setup():
#     configuration = get_config(_config_path)
#
#     db = Database(configuration)
#     db.delete_results_table()
#     db.delete_analysis_table()

# def test_call_wi_a_call():
#     rerun_analysis_path = which("ltf_rerun_analysis.py")
#     met_start = 410227203.000 - 86400
#     duration = 86400.0
#     counts = 0
#     outfile = "out.txt"
#     logfile = "log.txt"
#     config = "/home/suli_students/suli_jamie/fermi_blind_search/test/config_test.txt"
#     configuration = get_config(config)
#     db = Database(configuration)
#     db.create_tables()
#     analysis_vals = {'met_start': met_start, 'duration': duration, 'counts': counts, 'outfile': outfile,
#                      'logfile': logfile}
#     db.add_analysis(analysis_vals)
#     rerun_analysis(rerun_analysis_path, met_start, duration, counts, outfile, logfile, config)
#     db.delete_results_table()
#     db.delete_analysis_table()


def test_most_recent_not_run_before():
    real_time_path = which("ltf_real_time.py")
    print(real_time_path)
    most_recent_event = 410227203.000
    configuration = get_config(_config_path)

    db = Database(configuration)
    db.create_tables()

    cmd_line = ("%s --config %s --test_time %s" % (real_time_path, _config_path, most_recent_event))
    print(cmd_line)
    subprocess.check_call(cmd_line, shell=True)
    results = db.get_results_to_email()

    # read in results file and check that the second line matches what it should be
    write_path = os.path.join(configuration.get("Real time", "base_path"),
                              str(most_recent_event - 43200.0) + "_43200.0", "out.txt")

    results = []
    # with open(write_path) as f:
    #     results = f.read().split("\n")
    #
    # assert results[1] == \
    #        "LTF010432.25-832140.64 16.1343688965 -83.361289978 410205293.043 410217452.222 9 1.0184731220185956e-07"

    db.delete_analysis_table()
    db.delete_results_table()
    # shutil.rmtree(configuration.get("Real time", "base_path"))


def test_most_recent_has_been_run_should_rerun():
    real_time_path = which("ltf_real_time.py")
    print(real_time_path)
    most_recent_event = 410227203.000
    configuration = get_config(_config_path)

    db = Database(configuration)
    db.create_tables()

    analysis_to_add = {"met_start": 410184003.0, "duration": 43200.0, "counts": 30, "outfile": "out.txt",
                       "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)

    results = db.get_analysis_between_times(410227203.000 - 86400.0, 410227203.000 - 43200.0 - 1)
    for row in results:
        print(row)

    cmd_line = ("%s --config %s --test_time %s" % (real_time_path, _config_path, most_recent_event))

    print(cmd_line)
    subprocess.check_call(cmd_line, shell=True)
    # write_path = os.path.join(configuration.get("Real time", "base_path"),
    #                           str(most_recent_event - 43200.0) + "_43200.0", "out.txt")
    results = []
    # with open(write_path) as f:
    #     results = f.read().split("\n")
    db.delete_analysis_table()
    db.delete_results_table()
    # shutil.rmtree(configuration.get("Real time", "base_path"))

    # assert results[1] == \
    #        "LTF010432.25-832140.64 16.1343688965 -83.361289978 410205293.043 410217452.222 9 1.0184731220185956e-07"


def test_most_recent_has_been_run_should_not_rerun():
    real_time_path = which("ltf_real_time.py")
    print(real_time_path)
    most_recent_event = 410227203.000
    configuration = get_config(_config_path)

    db = Database(configuration)
    db.create_tables()

    analysis_to_add = {"met_start": 410184003.0, "duration": 43200.0, "counts": 3639487, "outfile": "out.txt",
                       "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)

    cmd_line = ("%s --config %s --test_time %s" % (real_time_path, _config_path, most_recent_event))

    print(cmd_line)
    subprocess.check_call(cmd_line, shell=True)
    # write_dir = os.path.join(configuration.get("Real time", "base_path"),
    #                           str(most_recent_event - 43200.0) + "_43200.0")
    # ls = os.listdir(write_dir)

    db.delete_analysis_table()
    db.delete_results_table()
    # shutil.rmtree(configuration.get("Real time", "base_path"))

    # assert len(ls) == 0

def test_rerun_past_analyses():
    real_time_path = which("ltf_real_time.py")
    print(real_time_path)
    most_recent_event = 410227203.000
    configuration = get_config(_config_path)

    db = Database(configuration)
    db.create_tables()

    # analyses to rerun

    # end time of analysis falls in analysis interval
    analysis_to_add = {"met_start": 410097703.0, "duration": 43200.0, "counts": 25, "outfile": "out.txt",
                       "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)

    # start and end times of analysis fall in analysis interval
    analysis_to_add = {"met_start": 410141803.0, "duration": 40200.0, "counts": 25, "outfile": "out.txt",
                       "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)

    # start time of analysis falls in analysis interval
    analysis_to_add = {"met_start": 410183003.0, "duration": 40000.0, "counts": 25, "outfile": "out.txt",
                       "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)

    # analyses not to rerun TODO: fill out with correct count numbers

    # # end time of analysis falls in analysis interval
    analysis_to_add = {"met_start": 410139803.0, "duration": 40000.0, "counts": 3576544, "outfile": "out.txt",
                       "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)

    # start and end times of analysis fall in analysis interval
    analysis_to_add = {"met_start": 410141803.0, "duration": 40000.0, "counts": 3539609, "outfile": "out.txt",
                       "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)

    # start time of analysis falls in analysis interval
    analysis_to_add = {"met_start": 410183003.0, "duration": 40200.0, "counts": 3204272, "outfile": "out.txt",
                       "logfile": "log.txt"}
    db.add_analysis(analysis_to_add)

    cmd_line = ("%s --config %s --test_time %s" % (real_time_path, _config_path, most_recent_event))

    print(cmd_line)
    subprocess.check_call(cmd_line, shell=True)
    db.delete_analysis_table()
    db.delete_results_table()