"""Ed25519 authentication helper for Binance API."""

import base64
import time
from pathlib import Path
from typing import Dict, Optional
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class Ed25519Authenticator:
    """Handles Ed25519 signature authentication for Binance API."""

    def __init__(self, api_key: str, private_key_path: str, password: Optional[str] = None):
        """Initialize Ed25519 authenticator.

        Args:
            api_key: Binance API key
            private_key_path: Path to Ed25519 private key PEM file
            password: Password for encrypted private key (optional)
        """
        self.api_key = api_key
        self.private_key = self._load_private_key(private_key_path, password)

    def _load_private_key(self, key_path: str, password: Optional[str] = None) -> Ed25519PrivateKey:
        """Load Ed25519 private key from PEM file.

        Args:
            key_path: Path to private key file
            password: Optional password for encrypted key

        Returns:
            Ed25519PrivateKey instance
        """
        key_file = Path(key_path)

        if not key_file.exists():
            raise FileNotFoundError(f"Private key file not found: {key_path}")

        with open(key_file, 'rb') as f:
            password_bytes = password.encode('utf-8') if password else None
            private_key = load_pem_private_key(
                data=f.read(),
                password=password_bytes
            )

        if not isinstance(private_key, Ed25519PrivateKey):
            raise ValueError("Key file must contain an Ed25519 private key")

        return private_key

    def sign_request(self, params: Dict) -> Dict:
        """Sign request parameters with Ed25519 signature.

        Args:
            params: Request parameters to sign

        Returns:
            Parameters with signature added
        """
        # Add timestamp if not present
        if 'timestamp' not in params:
            params['timestamp'] = int(time.time() * 1000)

        # Create payload string
        payload = '&'.join([f'{param}={value}' for param, value in sorted(params.items())])

        # Sign the payload
        signature = base64.b64encode(
            self.private_key.sign(payload.encode('ASCII'))
        ).decode('ASCII')

        # Add signature to parameters
        params['signature'] = signature

        return params

    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers.

        Returns:
            Dictionary with API key header
        """
        return {
            'X-MBX-APIKEY': self.api_key
        }
