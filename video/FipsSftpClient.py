import paramiko
import os
import socket
from decouple import config as ENV_CONFIG
# ----------------------------
# Enforce FIPS-approved SSH algorithms
# ----------------------------

FIPS_KEX = (
    "diffie-hellman-group14-sha256",
    "diffie-hellman-group-exchange-sha256",
)

FIPS_CIPHERS = (
    "aes256-ctr",
    "aes192-ctr",
    "aes128-ctr",
)

FIPS_MACS = (
    "hmac-sha2-256",
    "hmac-sha2-512",
)

ENVIRONMENT = ENV_CONFIG("ENVIRONMENT", default="DEV")
if ENVIRONMENT == "PROD":
    KNOWN_HOSTS_PATH=r"C:\Users\Administrator\Documents\ees\video\known_hosts_prod"
else:
    KNOWN_HOSTS_PATH="./known_hosts_dev"

class FipsSftpClient:
    def __init__(self, hostname, port=22, username=None, password=None, key_filepath=None):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.key_filepath = key_filepath
        self.known_hosts_path = KNOWN_HOSTS_PATH

        self.ssh = None
        self.sftp = None

    def connect(self):
        self.ssh = paramiko.SSHClient()

        # --- Host Key Verification ---
        if self.known_hosts_path and os.path.exists(self.known_hosts_path):
            self.ssh.load_host_keys(self.known_hosts_path)
            self.ssh.set_missing_host_key_policy(paramiko.RejectPolicy())
        else:
            raise Exception("Missing known_hosts file. Cannot continue in FIPS mode.")

        # --- Apply FIPS algorithm restrictions ---
        # paramiko.Transport._preferred_kex = FIPS_KEX
        # paramiko.Transport._preferred_ciphers = FIPS_CIPHERS
        # paramiko.Transport._preferred_macs = FIPS_MACS

        # # --- Connect ---
        # if self.key_filepath:
        #     pkey = paramiko.RSAKey.from_private_key_file(self.key_filepath)
        #     self.ssh.connect(self.hostname, port=self.port, username=self.username, pkey=pkey)
        # else:
        #     self.ssh.connect(self.hostname, port=self.port, username=self.username, password=self.password)

        # self.sftp = self.ssh.open_sftp()
        sock = socket.create_connection((self.hostname, self.port))
        transport = paramiko.Transport(sock)

        sec = transport.get_security_options()

        # Determine MAC field (macs or digests)
        if hasattr(sec, "macs"):
            mac_field = "macs"
        elif hasattr(sec, "digests"):
            mac_field = "digests"
        else:
            raise Exception("No supported MAC/digest field found in Paramiko SecurityOptions")

        # ----------------------------
        # Disable Non-FIPS Algorithms
        # ----------------------------
        disabled = {
            "kex": [a for a in sec.kex if a not in FIPS_KEX],
            "ciphers": [a for a in sec.ciphers if a not in FIPS_CIPHERS],
            mac_field: [a for a in getattr(sec, mac_field) if a not in FIPS_MACS],
        }
        print("Disabled algorithms:", disabled)

        transport.disabled_algorithms = disabled

        # ----------------------------
        # Force ONLY FIPS algorithms
        # ----------------------------
        sec.kex = FIPS_KEX
        sec.ciphers = FIPS_CIPHERS
        setattr(sec, mac_field, FIPS_MACS)

        # ----------------------------
        # Begin SSH handshake
        # ----------------------------
        transport.start_client()
        # ----------------------------
        # Authenticate
        # ----------------------------
        if self.key_filepath:
            key = paramiko.RSAKey.from_private_key_file(self.key_filepath)
            transport.auth_publickey(self.username, key)
        else:
            transport.auth_password(self.username, self.password)

        # bind transport to ssh client
        self.ssh._transport = transport

        # Create SFTP session
        self.sftp = paramiko.SFTPClient.from_transport(transport)


    def upload_file(self, local_path, remote_path):
        if not self.sftp:
            raise Exception("SFTP not connected.")
        print(f"uploading to {self.hostname} as {self.username} [(remote path: {remote_path});(source local path: {local_path})]")
        self.sftp.put(local_path, remote_path)

    def listdir(self, remote_path):
        if not self.sftp:
            raise Exception("SFTP not connected.")
        return self.sftp.listdir(remote_path)

    def listdir_attr(self, remote_path):
        if not self.sftp:
            raise Exception("SFTP not connected.")
        return self.sftp.listdir_attr(remote_path)

    def download(self, remote_path, target_local_path):
        if not self.sftp:
            raise Exception("SFTP not connected.")

        try:
            print(f"downloading from {self.hostname} as {self.username} "
                  f"[(remote path: {remote_path}); (local path: {target_local_path})]")

            # Create target directory
            path, _ = os.path.split(target_local_path)
            if not os.path.isdir(path):
                os.makedirs(path, exist_ok=True)

            self.sftp.get(remote_path, target_local_path)
            print("download completed")

        except Exception as err:
            raise Exception(f"Error while downloading file from SFTP server: {err}")

    def rename(self, source_path, dest_path):
        if not self.sftp:
            raise Exception("SFTP not connected.")
        self.sftp.rename(source_path, dest_path)
        print(f"Renamed {source_path} to {dest_path}")
        
    def remove(self, remote_path):
        if not self.sftp:
            raise Exception("SFTP not connected.")
        self.sftp.remove(remote_path)
    def disconnect(self):
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()