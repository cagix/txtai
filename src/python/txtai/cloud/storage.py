"""
Object storage module
"""

import os

# Conditional import
try:
    from libcloud.storage.providers import get_driver, DRIVERS
    from libcloud.storage.types import ContainerDoesNotExistError, ObjectDoesNotExistError

    LIBCLOUD = True
except ImportError:
    LIBCLOUD, DRIVERS = False, None


from .base import Cloud


class ObjectStorage(Cloud):
    """
    Object storage cloud provider backed by Apache libcloud.
    """

    @staticmethod
    def isprovider(provider):
        """
        Checks if this provider is an object storage provider.

        Args:
            provider: provider name

        Returns:
            True if this is an object storage provider
        """

        return LIBCLOUD and provider and provider in DRIVERS

    def __init__(self, config):
        super().__init__(config)

        if not LIBCLOUD:
            raise ImportError('Cloud object storage is not available - install "cloud" extra to enable')

        # Get driver for provider
        driver = get_driver(config["provider"])

        # Get client connection
        self.client = driver(
            config.get("key", os.environ.get("ACCESS_KEY")),
            config.get("secret", os.environ.get("ACCESS_SECRET")),
            host=config.get("host"),
            port=config.get("port"),
            token=config.get("token"),
            region=config.get("region"),
        )

    def metadata(self, path=None):
        try:
            # If this is an archive path, check if file exists
            if self.isarchive(path):
                return self.client.get_object(self.config["container"], os.path.basename(path))

            # Otherwise check if container exists
            return self.client.get_container(self.config["container"])
        except (ContainerDoesNotExistError, ObjectDoesNotExistError):
            return None

    def load(self, path=None):
        # Download archive file
        if self.isarchive(path):
            obj = self.client.get_object(self.config["container"], os.path.basename(path))
            obj.download(path, overwrite_existing=True)

        # Download all files in container
        else:
            # Create local directory, if necessary
            os.makedirs(path, exist_ok=True)

            container = self.client.get_container(self.config["container"])
            for obj in container.list_objects():
                obj.download(os.path.join(path, obj.name), overwrite_existing=True)

        return path

    def save(self, path):
        # Get or create container
        try:
            container = self.client.get_container(self.config["container"])
        except ContainerDoesNotExistError:
            container = self.client.create_container(self.config["container"])

        # Upload files
        for f in self.listfiles(path):
            with open(f, "rb") as iterator:
                self.client.upload_object_via_stream(iterator=iterator, container=container, object_name=os.path.basename(f))
