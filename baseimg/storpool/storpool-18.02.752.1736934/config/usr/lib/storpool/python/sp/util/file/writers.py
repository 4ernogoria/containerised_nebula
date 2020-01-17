import os


def ensure_dir(dpath):
    """Makes sure directory with the given path exists."""
    if not os.path.isdir(dpath):
        os.makedirs(dpath, mode=0o755)


def write_file(fpath, content, backup_path=None):
    """Writes the given content to the given file path.
    File is created if not existent.
    The old file contents is saved to backup_path, if provided.
    """
    fpath = os.path.abspath(fpath)
    ensure_dir(os.path.dirname(fpath))
    if backup_path is not None and os.path.isfile(fpath):
        ensure_dir(os.path.dirname(backup_path))
        os.rename(fpath, backup_path)
    with open(fpath, 'w+') as fhandle:
        fhandle.write(content)


def write_file_with_backup(fpath, content, backup_path=None):
    """Writes the given content to the given file path.
    Backup path can be provided, otherwise is assigned automatically.
    """
    if backup_path is None:
        backup_path = fpath + '.old'
    write_file(fpath, content, backup_path)
