from django.core.files.storage import storages


def sticker_storage():
    """Returns the configured stickers storage backend.
    Passed as a callable to FileField(storage=) to avoid
    serialising the instance into migrations."""
    return storages["stickers"]
