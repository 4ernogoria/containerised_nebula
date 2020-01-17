import subprocess


def _check_output(*popenargs, **kwargs):
    if 'stdout' in kwargs:  # pragma: no cover
        raise ValueError('stdout argument not allowed, '
                         'it will be overridden.')
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, _ = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise subprocess.CalledProcessError(retcode, cmd, output=output)
    return output

# overwrite CalledProcessError due to `output`
# keyword not being available (in 2.6)
class _CalledProcessError(Exception):
    def __init__(self, returncode, cmd, output=None):
        super(_CalledProcessError, self).__init__()
        self.returncode = returncode
        self.cmd = cmd
        self.output = output

    def __str__(self):
        return "Command '{c}' returned non-zero exit status {s}"\
                .format(c=self.cmd, s=self.returncode)


if not hasattr(subprocess, 'check_output'):
    subprocess.check_output = _check_output
    subprocess.CalledProcessError = _CalledProcessError
