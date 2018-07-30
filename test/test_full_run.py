import subprocess
import os
import shutil
import time

from fermi_blind_search.which import which
from fermi_blind_search.database import Database
from fermi_blind_search.configuration import get_config
from ltf_real_time import rerun_analysis

_config_path = "/home/suli_students/suli_jamie/test_real_time/config.txt"

def test_setup():
    configuration = get_config(_config_path)

    # make sure we start with an empty database
    db = Database(configuration)
    db.create_tables()
    db.delete_results_table()
    db.delete_analysis_table()


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
    time.sleep(60)
    while len(subprocess.check_output("qstat")) > 0:
        time.sleep(5)

    # farm jobs have completed, check the results

    # read in results file and check that the second line matches what it should be
    write_path = os.path.join(configuration.get("Real time", "base_path"),
                              str(most_recent_event - 43200.0) + "_43200.0", "out.txt")

    results = []
    with open(write_path) as f:
        results = f.read().split("\n")

    assert results[1] == \
           "LTF010432.25-832140.64 16.1343688965 -83.361289978 410205293.043 410217452.222 9 1.0184731220185956e-07"

    db.delete_analysis_table()
    db.delete_results_table()
    shutil.rmtree(configuration.get("Real time", "base_path"))


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

    while len(subprocess.check_output("qstat")) > 0:
        time.sleep(5)

    # farm jobs have completed, check the results

    write_path = os.path.join(configuration.get("Real time", "base_path"),
                              str(most_recent_event - 43200.0) + "_43200.0", "out.txt")
    results = []
    with open(write_path) as f:
        results = f.read().split("\n")
    db.delete_analysis_table()
    db.delete_results_table()
    shutil.rmtree(configuration.get("Real time", "base_path"))

    assert results[1] == \
           "LTF010432.25-832140.64 16.1343688965 -83.361289978 410205293.043 410217452.222 9 1.0184731220185956e-07"


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
    while len(subprocess.check_output("qstat")) > 0:
        time.sleep(5)

    # farm jobs have completed, check the results
    write_dir = os.path.join(configuration.get("Real time", "base_path"),
                              str(most_recent_event - 43200.0) + "_43200.0")
    ls = os.listdir(write_dir)

    db.delete_analysis_table()
    db.delete_results_table()
    shutil.rmtree(configuration.get("Real time", "base_path"))

    assert len(ls) == 1


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

    # analyses not to rerun

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

    while len(subprocess.check_output("qstat")) > 0:
        time.sleep(5)

    # farm jobs have completed, check the results
    base_dir = configuration.get("Real time", "base_path")
    assert len(os.listdir(os.path.join(base_dir, "410139803.0_40000.0"))) == 1
    assert len(os.listdir(os.path.join(base_dir, "410141803.0_40000.0"))) == 1
    assert len(os.listdir(os.path.join(base_dir, "410183003.0_40200.0"))) == 1

    results = ''
    with open(os.path.join(base_dir, "410097703.0_43200.0/out.txt")) as f:
        results = f.read()

    assert results == \
           "# name ra dec tstarts tstops counts probabilities"


    results = []
    with open(os.path.join(base_dir, "410097703.0_43200.0/out.txt")) as f:
        results = f.read().split("\n")

    assert results[1] == \
           "LTF003738.54-043812.88 9.41058921814 -4.63691186905 410146516.288,410157957.022,410158188.93 410157946.008,410158181.858,410181087.077 3,22,24 0.4415005372786246,6.762756319877049e-27,0.021202409309007006"

    results = []
    with open(os.path.join(base_dir, "410183003.0_40000.0/out.txt")) as f:
        results = f.read().split("\n")

    assert results[1] == \
           "LTF222917.20-570319.91 337.321655273 -57.0555305481 410214484.059 410214503.816 3 5.196131451719908e-06"

    results = []
    with open(os.path.join(base_dir, "410184003.0_43200.0/out.txt")) as f:
        results = f.read().split("\n")

    assert results[1] == \
           "LTF010432.25-832140.64 16.1343688965 -83.361289978 410205293.043 410217452.222 9 1.0184731220185956e-07"

    db.delete_analysis_table()
    db.delete_results_table()
    shutil.rmtree(configuration.get("Real time", "base_path"))