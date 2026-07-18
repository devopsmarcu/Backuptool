import os
import paramiko
from typing import Optional, Callable, Tuple
from pathlib import Path


class SftpClient:
    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str = "",
        password: str = "",
        private_key_path: Optional[str] = None,
        known_hosts_path: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key_path = private_key_path
        self.known_hosts_path = known_hosts_path
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.sftp_client: Optional[paramiko.SFTPClient] = None

    def connect(self) -> bool:
        """Connect to SFTP server."""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.RejectPolicy())
            if self.known_hosts_path:
                self.ssh_client.load_host_keys(self.known_hosts_path)
            
            if self.private_key_path and os.path.exists(self.private_key_path):
                private_key = paramiko.RSAKey.from_private_key_file(self.private_key_path)
                self.ssh_client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    pkey=private_key,
                )
            else:
                self.ssh_client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                )
            
            self.sftp_client = self.ssh_client.open_sftp()
            return True
        except Exception as e:
            print(f"SFTP connection error: {e}")
            self.disconnect()
            return False

    def disconnect(self):
        """Disconnect from SFTP server."""
        if self.sftp_client:
            self.sftp_client.close()
        if self.ssh_client:
            self.ssh_client.close()

    def mkdir_p(self, remote_path: str):
        """Create directories recursively on remote server."""
        if not remote_path:
            return
        try:
            self.sftp_client.stat(remote_path)
        except IOError:
            parent_path = os.path.dirname(remote_path)
            if parent_path and parent_path != remote_path:
                self.mkdir_p(parent_path)
            self.sftp_client.mkdir(remote_path)

    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        """Upload a single file to SFTP server."""
        local_size = os.path.getsize(local_path)
        
        def callback(transferred: int, total: int):
            if progress_callback:
                progress_callback(transferred, total)
        
        self.sftp_client.put(local_path, remote_path, callback=callback)

    def download_file(
        self,
        remote_path: str,
        local_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        """Download a single file from SFTP server."""
        def callback(transferred: int, total: int):
            if progress_callback:
                progress_callback(transferred, total)
        
        self.sftp_client.get(remote_path, local_path, callback=callback)

    def check_free_space(self, remote_path: str) -> Optional[Tuple[int, int]]:
        """Check free and total space on remote server (approximate)."""
        try:
            # Try to use statvfs if available
            stat = self.sftp_client.statvfs(remote_path)
            free = stat.f_frsize * stat.f_bavail
            total = stat.f_frsize * stat.f_blocks
            return free, total
        except Exception as e:
            print(f"Could not check space: {e}")
            return None
