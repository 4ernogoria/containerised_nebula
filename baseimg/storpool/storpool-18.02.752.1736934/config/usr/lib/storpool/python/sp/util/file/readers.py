"""Provides some file content readers and parsers."""

def lines(fpath):
    """Return a list of lines (strings) in a file."""
    with open(fpath, 'r') as fhandle:
        return fhandle.readlines()


def file_content(fpath):
    """Return the whole file contents as a single string."""
    with open(fpath, 'r') as fhandle:
        return fhandle.read()


def getdataf(fpath):
    '''fpath: str path to file
    Returns all file contens without the following \n if one appears at
    the end of the last line of the file'''
    try:
        res = file_content(fpath).rstrip('\n')
        return res if res else None
    except IOError:
        return None
