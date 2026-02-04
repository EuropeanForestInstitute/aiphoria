import datetime
import sys
import time

# Logs
global_log_level = "info"

# Performance logs
use_log_perf = False
global_perf_logs = []
global_perf_log_index = 0


class bcolors(object):
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def log(msg: str, level: str = "info", show_timestamp: bool = False):
    """
    Log message with custom text.

    :param msg: Custom text to show
    :param level: Log level "info" (stdout) / "debug" (stderr)
    :param show_timestamp: True to show timestamp in message
    :return:
    """
    color = bcolors.OKGREEN

    prefix = ""
    target = sys.stdout
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if level == "info":
        prefix = "INFO {}: " if show_timestamp else "INFO: "
        target = sys.stdout
        color = bcolors.OKGREEN

    if level == 'error':
        prefix = "ERROR: {}" if show_timestamp else "ERROR: "
        target = sys.stdout
        color = bcolors.FAIL

    if level == "debug":
        prefix = "DEBUG {}: " if show_timestamp else "INFO: "
        target = sys.stderr
        color = bcolors.FAIL

    if show_timestamp:
        prefix = prefix.format(timestamp)

    if not len(msg):
        prefix = ""

    text = prefix + msg
    print(color + text + bcolors.ENDC, file=target)
    target.flush()


def start_log_perf(name: str):
    if not use_log_perf:
        return

    global global_perf_logs
    global global_perf_log_index
    entry = [name, time.perf_counter()]
    global_perf_logs.append(entry)


def stop_log_perf():
    if not use_log_perf:
        return

    global global_perf_logs
    global global_perf_log_index
    time_in_secs = time.perf_counter() - global_perf_logs[global_perf_log_index][1]
    global_perf_logs[global_perf_log_index][1] = time_in_secs
    global_perf_log_index += 1
    return time_in_secs


def get_all_log_perf():
    for entry in global_perf_logs:
        yield entry


def show_log_perf_summary(title: str):
    if not use_log_perf:
        return

    target = sys.stderr
    target.flush()
    print("SUMMARY: {}".format(title), file=target)
    total_in_secs = sum([entry[1] for entry in global_perf_logs])
    for entry in global_perf_logs:
        name = entry[0]
        time_in_secs = entry[1]
        share = (time_in_secs / total_in_secs) * 100
        print("\t{}: {:.2f}s ({:.1f}%)".format(name, time_in_secs, share), file=target)
    target.flush()


def clear_log_perf():
    global global_perf_logs
    global global_perf_log_index
    global_perf_logs = []
    global_perf_log_index = 0
