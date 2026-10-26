"""
Tests for Nexus blockchain (IPFS) module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from nexus.blockchain import IPFSBlockchain
from nexus.waypoint import Waypoint, ActionType, AssertionType


class TestIPFSBlockchain:
    """Tests for IPFSBlockchain class."""

    def test_blockchain_initialization_with_env_vars(self):
        """Test blockchain initialization with environment variables."""
        with patch.dict(
            'os.environ',
            {
                'PINATA_API_KEY': 'test_key',
                'PINATA_API_SECRET': 'test_secret',
            },
        ):
            blockchain = IPFSBlockchain()
            assert blockchain.pinata_key == 'test_key'
            assert blockchain.pinata_secret == 'test_secret'

    def test_blockchain_initialization_with_params(self):
        """Test blockchain initialization with parameters."""
        blockchain = IPFSBlockchain(
            api_key='param_key',
            api_secret='param_secret',
        )
        assert blockchain.pinata_key == 'param_key'
        assert blockchain.pinata_secret == 'param_secret'

    def test_blockchain_initialization_missing_credentials(self):
        """Test blockchain initialization fails without credentials."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError):
                IPFSBlockchain()

    def test_blockchain_get_headers(self):
        """Test HTTP headers generation."""
        blockchain = IPFSBlockchain(
            api_key='test_key',
            api_secret='test_secret',
        )
        headers = blockchain._get_headers()

        assert headers['pinata_api_key'] == 'test_key'
        assert headers['pinata_secret_api_key'] == 'test_secret'
        assert headers['Content-Type'] == 'application/json'

    @patch('requests.post')
    def test_store_waypoint_success(self, mock_post):
        """Test successful waypoint storage on IPFS."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {'IpfsHash': 'QmTest123'}
        mock_post.return_value = mock_response

        blockchain = IPFSBlockchain(
            api_key='test_key',
            api_secret='test_secret',
        )

        waypoint = Waypoint(url='https://example.com')
        waypoint.add_action(ActionType.CLICK, selector='#button')

        ipfs_hash = blockchain.store_waypoint(waypoint)

        assert ipfs_hash == 'QmTest123'
        assert waypoint.ipfs_hash == 'QmTest123'
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_store_waypoint_api_error(self, mock_post):
        """Test waypoint storage fails on API error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception('API Error')
        mock_post.return_value = mock_response

        blockchain = IPFSBlockchain(
            api_key='test_key',
            api_secret='test_secret',
        )

        waypoint = Waypoint(url='https://example.com')

        with pytest.raises(Exception):
            blockchain.store_waypoint(waypoint)

    @patch('requests.get')
    def test_retrieve_waypoint_success(self, mock_get):
        """Test successful waypoint retrieval from IPFS."""
        waypoint_json = """{
  "url": "https://example.com",
  "actions": [
    {
      "action_type": "click",
      "selector": "#button",
      "value": null,
      "timeout": 10.0,
      "timestamp": "2024-01-01T00:00:00"
    }
  ],
  "assertions": [],
  "description": "",
  "version": "1.0",
  "created_at": "2024-01-01T00:00:00"
}"""

        mock_response = Mock()
        mock_response.text = waypoint_json
        mock_get.return_value = mock_response

        blockchain = IPFSBlockchain(
            api_key='test_key',
            api_secret='test_secret',
        )

        waypoint = blockchain.retrieve_waypoint('QmTest123')

        assert waypoint.url == 'https://example.com'
        assert len(waypoint.actions) == 1
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_retrieve_waypoint_network_error(self, mock_get):
        """Test waypoint retrieval fails on network error."""
        mock_get.side_effect = Exception('Network Error')

        blockchain = IPFSBlockchain(
            api_key='test_key',
            api_secret='test_secret',
        )

        with pytest.raises(Exception):
            blockchain.retrieve_waypoint('QmTest123')

    def test_verify_waypoint_integrity_success(self):
        """Test successful waypoint integrity verification."""
        waypoint = Waypoint(url='https://example.com')
        waypoint.add_action(ActionType.CLICK, selector='#button')

        correct_hash = waypoint.compute_hash()

        blockchain = IPFSBlockchain(
            api_key='test_key',
            api_secret='test_secret',
        )

        with patch.object(blockchain, 'retrieve_waypoint', return_value=waypoint):
            is_valid = blockchain.verify_waypoint_integrity(
                'QmTest123',
                correct_hash,
            )
            assert is_valid is True

    def test_verify_waypoint_integrity_failure(self):
        """Test failed waypoint integrity verification."""
        waypoint = Waypoint(url='https://example.com')
        waypoint.add_action(ActionType.CLICK, selector='#button')

        blockchain = IPFSBlockchain(
            api_key='test_key',
            api_secret='test_secret',
        )

        with patch.object(blockchain, 'retrieve_waypoint', return_value=waypoint):
            is_valid = blockchain.verify_waypoint_integrity(
                'QmTest123',
                'wrong_hash_123',
            )
            assert is_valid is False

    @patch('requests.post')
    def test_pin_waypoint_success(self, mock_post):
        """Test successful waypoint pinning."""
        mock_response = Mock()
        mock_post.return_value = mock_response

        blockchain = IPFSBlockchain(
            api_key='test_key',
            api_secret='test_secret',
        )

        result = blockchain.pin_waypoint('QmTest123')

        assert result is True
        mock_post.assert_called_once()

    @patch('requests.delete')
    def test_unpin_waypoint_success(self, mock_delete):
        """Test successful waypoint unpinning."""
        mock_response = Mock()
        mock_delete.return_value = mock_response

        blockchain = IPFSBlockchain(
            api_key='test_key',
            api_secret='test_secret',
        )

        result = blockchain.unpin_waypoint('QmTest123')

        assert result is True
        mock_delete.assert_called_once()

    @patch('requests.get')
    def test_list_pins_success(self, mock_get):
        """Test listing pinned waypoints."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'rows': [
                {
                    'IpfsHash': 'QmTest123',
                    'name': 'waypoint-1',
                    'size': 512,
                },
            ]
        }
        mock_get.return_value = mock_response

        blockchain = IPFSBlockchain(
            api_key='test_key',
            api_secret='test_secret',
        )

        pins = blockchain.list_pins()

        assert len(pins) == 1
        assert pins[0]['IpfsHash'] == 'QmTest123'
        mock_get.assert_called_once()
