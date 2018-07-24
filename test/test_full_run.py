import subprocess
import os

from fermi_blind_search.which import which
from fermi_blind_search.database import Database
from fermi_blind_search.configuration import get_config
from ltf_real_time import rerun_analysis


def test_call_script():
    # cmd_line = "echo Hello World!"
    p = subprocess.Popen(["echo", "Hello World!"], stdout=subprocess.PIPE)
    stdout, _ = p.communicate()
    assert stdout == "Hello World!\n"

def test_call_wi_a_call():
    rerun_analysis_path = which("ltf_rerun_analysis.py")
    met_start = 410227203.000 - 86400
    duration = 86400
    counts = 0
    outfile = "out.txt"
    logfile = "log.txt"
    config = "/home/suli_students/suli_jamie/fermi_blind_search/test/config_test.txt"
    configuration = get_config(config)
    db = Database(configuration)
    db.create_tables()
    analysis_vals = {'met_start': met_start, 'duration': duration, 'counts': counts, 'outfile': outfile,
                     'logfile': logfile}
    db.add_analysis(analysis_vals)
    rerun_analysis(rerun_analysis_path, met_start, duration, counts, outfile, logfile, config)
    db.delete_results_table()
    db.delete_analysis_table()


def test_most_recent_not_run_before():
    real_time_path = which("ltf_real_time.py")
    print(real_time_path)
    most_recent_event = 410227203.000
    config_path = "/home/suli_students/suli_jamie/fermi_blind_search/test/config_test.txt"
    configuration = get_config(config_path)

    db = Database(configuration)
    db.create_tables()

    cmd_line = ("%s --config %s --test_time %s" % (real_time_path, config_path, most_recent_event))
    # cmd_line = ("ltf_real_time.py --config %s " % (config_path))
    print(cmd_line)
    subprocess.check_call(cmd_line, shell=True)
    # p = subprocess.Popen(cmd_line, stdout=subprocess.PIPE)
    # p = subprocess.Popen(cmd_line, stdout=subprocess.PIPE)
    # stout, _ = p.communicate()
    # print(stout)
    print("done yet?")
    db.delete_analysis_table()
    db.delete_results_table()
    assert 1==1
    # write_path = configuration.get("Real time", "base_path") + "/" + str(most_recent_event) + "_86400.0"
    # results_path = write_path + "/out.txt"
    # write_path = write_path + "/results"
    # print(results_path)
    # send_email_path = which("ltf_send_results_email.py")
    # # emulate the part that send the email, but write the results instead
    # email_cmd_line = ("%s --config %s --results %s --check_db --write_path %s" % (send_email_path, config_path,
    #                                                                               results_path, write_path ))
    #
    # subprocess.check_call(email_cmd_line, shell=True)
    #
    # result_files = os.listdir(write_path)
    #
    # print(len(result_files))
    # assert len(result_files) == 4