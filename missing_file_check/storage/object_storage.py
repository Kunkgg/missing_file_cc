"""
Object storage interface for uploading reports.

Provides abstract interface for object storage operations.
Concrete implementations should be provided for specific storage backends
(Aliyun OSS, AWS S3, MinIO, company internal storage, etc.)
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class ObjectStorage(ABC):
    """
    Abstract base class for object storage operations.

    Defines the interface for uploading files and directories to object storage.
    Concrete implementations should handle authentication, connection, and
    actual upload logic for specific storage backends.
    """

    @abstractmethod
    def upload_file(
        self, local_path: Path, remote_path: str, content_type: Optional[str] = None
    ) -> str:
        """
        Upload a single file to object storage.

        Args:
            local_path: Local file path to upload
            remote_path: Remote path/key in object storage
            content_type: Optional MIME type (e.g., "text/html", "application/json")

        Returns:
            Public URL to access the uploaded file

        Raises:
            ObjectStorageError: If upload fails
        """
        pass

    @abstractmethod
    def upload_directory(
        self, local_dir: Path, remote_prefix: str, recursive: bool = True
    ) -> list:
        """
        Upload a directory and its contents to object storage.

        Args:
            local_dir: Local directory path to upload
            remote_prefix: Remote path prefix in object storage
            recursive: If True, upload subdirectories recursively

        Returns:
            List of public URLs for uploaded files

        Raises:
            ObjectStorageError: If upload fails
        """
        pass

    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete a file from object storage.

        Args:
            remote_path: Remote path/key to delete

        Returns:
            True if deleted successfully, False if not found

        Raises:
            ObjectStorageError: If deletion fails
        """
        pass

    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if a file exists in object storage.

        Args:
            remote_path: Remote path/key to check

        Returns:
            True if file exists, False otherwise

        Raises:
            ObjectStorageError: If check fails
        """
        pass


class ObjectStorageError(Exception):
    """Exception raised for object storage operations."""

    pass


class PlaceholderObjectStorage(ObjectStorage):
    """
    Placeholder implementation for development/testing.

    Does not actually upload to remote storage, but simulates
    the interface and returns mock URLs.
    """

    def __init__(self, base_url: str = "https://storage.example.com"):
        """
        Initialize placeholder storage.

        Args:
            base_url: Base URL for generated mock URLs
        """
        self.base_url = base_url.rstrip("/")

    def upload_file(
        self, local_path: Path, remote_path: str, content_type: Optional[str] = None
    ) -> str:
        """
        Simulate file upload.

        Args:
            local_path: Local file path
            remote_path: Remote path
            content_type: Optional MIME type

        Returns:
            Mock URL
        """
        if not local_path.exists():
            raise ObjectStorageError(f"Local file not found: {local_path}")

        # Generate mock URL
        mock_url = f"{self.base_url}/{remote_path.lstrip('/')}"

        print(f"[PlaceholderStorage] Would upload: {local_path} -> {mock_url}")
        print(f"[PlaceholderStorage] Content-Type: {content_type or 'auto-detect'}")

        return mock_url

    def upload_directory(
        self, local_dir: Path, remote_prefix: str, recursive: bool = True
    ) -> list:
        """
        Simulate directory upload.

        Args:
            local_dir: Local directory path
            remote_prefix: Remote path prefix
            recursive: Upload recursively

        Returns:
            List of mock URLs
        """
        if not local_dir.is_dir():
            raise ObjectStorageError(f"Local directory not found: {local_dir}")

        mock_urls = []
        pattern = "**/*" if recursive else "*"

        for local_file in local_dir.glob(pattern):
            if local_file.is_file():
                relative_path = local_file.relative_to(local_dir)
                remote_path = f"{remote_prefix.rstrip('/')}/{relative_path}"
                mock_url = f"{self.base_url}/{remote_path.lstrip('/')}"
                mock_urls.append(mock_url)

                print(f"[PlaceholderStorage] Would upload: {local_file} -> {mock_url}")

        return mock_urls

    def delete_file(self, remote_path: str) -> bool:
        """Simulate file deletion."""
        print(f"[PlaceholderStorage] Would delete: {remote_path}")
        return True

    def file_exists(self, remote_path: str) -> bool:
        """Simulate existence check."""
        print(f"[PlaceholderStorage] Would check existence: {remote_path}")
        return False  # Always return False for placeholder


# Example concrete implementation template (commented out)
# class AliyunOSSStorage(ObjectStorage):
#     """Aliyun OSS implementation."""
#
#     def __init__(self, access_key_id: str, access_key_secret: str,
#                  endpoint: str, bucket_name: str):
#         import oss2
#         auth = oss2.Auth(access_key_id, access_key_secret)
#         self.bucket = oss2.Bucket(auth, endpoint, bucket_name)
#
#     def upload_file(self, local_path: Path, remote_path: str,
#                     content_type: Optional[str] = None) -> str:
#         headers = {}
#         if content_type:
#             headers['Content-Type'] = content_type
#
#         self.bucket.put_object_from_file(
#             remote_path, str(local_path), headers=headers
#         )
#         return f"https://{self.bucket.bucket_name}.{self.bucket.endpoint}/{remote_path}"
#
#     def upload_directory(self, local_dir: Path, remote_prefix: str,
#                         recursive: bool = True) -> list:
#         urls = []
#         pattern = "**/*" if recursive else "*"
#         for local_file in local_dir.glob(pattern):
#             if local_file.is_file():
#                 relative_path = local_file.relative_to(local_dir)
#                 remote_path = f"{remote_prefix}/{relative_path}"
#                 url = self.upload_file(local_file, remote_path)
#                 urls.append(url)
#         return urls
#
#     def delete_file(self, remote_path: str) -> bool:
#         try:
#             self.bucket.delete_object(remote_path)
#             return True
#         except Exception:
#             return False
#
#     def file_exists(self, remote_path: str) -> bool:
#         return self.bucket.object_exists(remote_path)
