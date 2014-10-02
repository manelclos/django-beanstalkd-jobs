JOBRUN = None


def set_current_job(jobrun):
    """
    Sets the current job being executed by the process
    """
    global JOBRUN
    JOBRUN = jobrun


def get_current_job():
    """
    Gets the current job being executed by the process
    """
    global JOBRUN
    return JOBRUN
