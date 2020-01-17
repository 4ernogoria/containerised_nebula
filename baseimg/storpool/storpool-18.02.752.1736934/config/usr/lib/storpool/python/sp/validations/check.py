class Check(object):
    """Check object.
    Used to build dependency graphs of checks for different machine properties.
    The list of dependencies, as well as the main problem reporting function and
    its parameters, are specified upon construction.
    Problem reporting function returns pair of two lists - errors and warnings.
    If any errors occur, the check fails, otherwise is ok.
    On running the check it will automatically run ALL of its dependencies.
    If any of the dependencies fails the problem reporting function won't be
    called.
    The check is protected from running more than once, thus running it again
    won't have any effect.
    Different check states can be seen in the Check.State class.
    """

    class State(object):
        """Keeps different state constants for the Check."""
        NOT_RUN = 0
        OK = 1
        FAILED = 2
        DEPENCENCY_ERROR = 3

    def __init__(self, dependencies, run, *args, **kwargs):
        self._dependencies = dependencies
        self._errors = []
        self._warnings = []
        self._run = run
        self._run_args = args
        self._run_kwargs = kwargs
        self.state = Check.State.NOT_RUN

    def run(self):
        """Run the check and its dependencies."""
        if self.state != Check.State.NOT_RUN:
            return
        for dependency_check in self._dependencies:
            dependency_check.run()
            if dependency_check.state != Check.State.OK:
                self.state = Check.State.DEPENCENCY_ERROR
        if self.state == Check.State.DEPENCENCY_ERROR:
            return
        self._errors, self._warnings = self._run(*self._run_args, **self._run_kwargs)
        self.state = Check.State.FAILED if self._errors else Check.State.OK

    def get_all_errors(self):
        """Get all errors from the check and its dependencies."""
        if self.state == Check.State.NOT_RUN:
            return []
        dep_errors = [set(dependency.get_all_errors()) for dependency in self._dependencies]
        return list(set.union(set(self._errors), *dep_errors))

    def get_all_warnings(self):
        """Get all warnings from the check and its dependencies."""
        if self.state == Check.State.NOT_RUN:
            return []
        dep_warns = [set(dependency.get_all_warnings()) for dependency in self._dependencies]
        return list(set.union(set(self._warnings), *dep_warns))
