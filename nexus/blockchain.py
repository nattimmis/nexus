"""
IPFS blockchain integration for Nexus waypoint storage.

Uses Pinata API for reliable IPFS pinning and retrieval.
Waypoints are stored immutably on IPFS with hash verification.
"""

import os
from typing import Optional
import requests
from nexus.waypoint import Waypoint
from nexus.logging_util import get_logger

logger = get_logger(__name__)


class IPFSBlockchain:
    """
    Manages IPFS storage and retrieval of waypoints via Pinata API.

    Attributes:
        pinata_key: Pinata API key (from env: PINATA_API_KEY).
        pinata_secret: Pinata API secret (from env: PINATA_API_SECRET).
        gateway: IPFS gateway URL for retrieval.
    """

    PINATA_API_URL = 'https://api.pinata.cloud'
    PINATA_GATEWAY = 'https://gateway.pinata.cloud/ipfs'

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        gateway: Optional[str] = None,
    ) -> None:
        """
        Initialize IPFS blockchain interface.

        Args:
            api_key: Pinata API key. Defaults to PINATA_API_KEY env var.
            api_secret: Pinata API secret. Defaults to PINATA_API_SECRET env var.
            gateway: IPFS gateway URL. Defaults to Pinata public gateway.

        Raises:
            ValueError: If API credentials are not provided or found in env.
        """
        self.pinata_key = api_key or os.getenv('PINATA_API_KEY')
        self.pinata_secret = api_secret or os.getenv('PINATA_API_SECRET')
        self.gateway = gateway or self.PINATA_GATEWAY

        if not self.pinata_key or not self.pinata_secret:
            raise ValueError(
                'Pinata API credentials required. '
                'Set PINATA_API_KEY and PINATA_API_SECRET environment variables.'
            )

        logger.info(f'Initialized IPFS blockchain with gateway: {self.gateway}')

    def _get_headers(self) -> dict:
        """
        Get HTTP headers for Pinata API requests.

        Returns:
            Headers dict with authentication.
        """
        return {
            'pinata_api_key': self.pinata_key,
            'pinata_secret_api_key': self.pinata_secret,
            'Content-Type': 'application/json',
        }

    def store_waypoint(
        self,
        waypoint: Waypoint,
        description: str = '',
    ) -> str:
        """
        Store a waypoint on IPFS via Pinata API.

        Args:
            waypoint: Waypoint instance to store.
            description: Optional description for the pinned content.

        Returns:
            IPFS hash (CID) of the stored waypoint.

        Raises:
            requests.RequestException: If IPFS upload fails.
        """
        waypoint.update_hash()
        json_content = waypoint.to_json()

        # Prepare JSON data for Pinata
        metadata = {
            'name': f'nexus-waypoint-{waypoint.hash[:8]}',
            'keyvalues': {
                'waypoint_hash': waypoint.hash,
                'url': waypoint.url,
                'description': description,
            },
        }

        files = {
            'file': ('waypoint.json', json_content, 'application/json'),
        }

        data = {
            'pinataMetadata': metadata,
        }

        try:
            response = requests.post(
                f'{self.PINATA_API_URL}/pinning/pinFileToIPFS',
                files=files,
                data=data,
                headers=self._get_headers(),
                timeout=30,
            )
            response.raise_for_status()

            result = response.json()
            ipfs_hash = result.get('IpfsHash')

            if not ipfs_hash:
                raise ValueError('No IPFS hash returned from Pinata')

            waypoint.ipfs_hash = ipfs_hash
            logger.info(f'Stored waypoint on IPFS: {ipfs_hash}')
            return ipfs_hash

        except requests.RequestException as e:
            logger.error(f'Failed to store waypoint on IPFS: {e}')
            raise

    def retrieve_waypoint(self, ipfs_hash: str) -> Waypoint:
        """
        Retrieve a waypoint from IPFS via gateway.

        Args:
            ipfs_hash: IPFS hash (CID) of the waypoint.

        Returns:
            Retrieved Waypoint instance.

        Raises:
            requests.RequestException: If IPFS retrieval fails.
            ValueError: If waypoint data is invalid or hash verification fails.
        """
        try:
            url = f'{self.gateway}/{ipfs_hash}'
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            json_content = response.text
            waypoint = Waypoint.from_json(json_content)

            logger.info(f'Retrieved waypoint from IPFS: {ipfs_hash}')
            return waypoint

        except requests.RequestException as e:
            logger.error(f'Failed to retrieve waypoint from IPFS: {e}')
            raise
        except (ValueError, TypeError) as e:
            logger.error(f'Invalid waypoint data from IPFS: {e}')
            raise

    def verify_waypoint_integrity(
        self,
        ipfs_hash: str,
        expected_hash: str,
    ) -> bool:
        """
        Verify waypoint integrity by hash comparison.

        Args:
            ipfs_hash: IPFS hash of the waypoint.
            expected_hash: Expected SHA-256 hash of waypoint content.

        Returns:
            True if waypoint integrity is verified.

        Raises:
            requests.RequestException: If IPFS retrieval fails.
        """
        try:
            waypoint = self.retrieve_waypoint(ipfs_hash)
            is_valid = waypoint.verify_hash(expected_hash)

            if is_valid:
                logger.info(f'Waypoint integrity verified: {ipfs_hash}')
            else:
                logger.warning(f'Waypoint integrity check failed: {ipfs_hash}')

            return is_valid

        except Exception as e:
            logger.error(f'Error verifying waypoint integrity: {e}')
            return False

    def pin_waypoint(self, ipfs_hash: str) -> bool:
        """
        Ensure a waypoint remains pinned on IPFS (immortal).

        Args:
            ipfs_hash: IPFS hash to ensure is pinned.

        Returns:
            True if pinning successful.

        Raises:
            requests.RequestException: If pinning fails.
        """
        try:
            response = requests.post(
                f'{self.PINATA_API_URL}/pinning/pinByHash',
                json={'hashToPin': ipfs_hash},
                headers=self._get_headers(),
                timeout=30,
            )
            response.raise_for_status()
            logger.info(f'Waypoint pinned on IPFS: {ipfs_hash}')
            return True

        except requests.RequestException as e:
            logger.error(f'Failed to pin waypoint on IPFS: {e}')
            raise

    def unpin_waypoint(self, ipfs_hash: str) -> bool:
        """
        Unpin a waypoint from IPFS (allows garbage collection).

        Args:
            ipfs_hash: IPFS hash to unpin.

        Returns:
            True if unpinning successful.

        Raises:
            requests.RequestException: If unpinning fails.
        """
        try:
            response = requests.delete(
                f'{self.PINATA_API_URL}/pinning/unpin/{ipfs_hash}',
                headers=self._get_headers(),
                timeout=30,
            )
            response.raise_for_status()
            logger.info(f'Waypoint unpinned from IPFS: {ipfs_hash}')
            return True

        except requests.RequestException as e:
            logger.error(f'Failed to unpin waypoint from IPFS: {e}')
            raise

    def list_pins(self) -> list:
        """
        List all pinned waypoints for this account.

        Returns:
            List of pinned IPFS hashes and metadata.

        Raises:
            requests.RequestException: If API call fails.
        """
        try:
            response = requests.get(
                f'{self.PINATA_API_URL}/data/pinList',
                headers=self._get_headers(),
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            return result.get('rows', [])

        except requests.RequestException as e:
            logger.error(f'Failed to list pins from IPFS: {e}')
            raise
