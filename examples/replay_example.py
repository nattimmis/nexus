#!/usr/bin/env python
"""
Example: Replaying a recorded waypoint with Nexus.

This example demonstrates how to:
1. Load a waypoint from a JSON file
2. Retrieve a waypoint from IPFS
3. Replay a waypoint with assertion verification
"""

import asyncio
import os
import json
from pathlib import Path
from nexus import NavigationPlayback, IPFSBlockchain, Waypoint
from nexus.logging_util import setup_logging

# Set up logging
setup_logging(level='INFO')


async def replay_from_file(waypoint_file: str):
    """
    Replay a waypoint from a JSON file.

    Args:
        waypoint_file: Path to waypoint JSON file.
    """
    print('Replaying from JSON file')
    print('=' * 50)

    try:
        # Load waypoint from file
        print(f'Loading waypoint from: {waypoint_file}')
        with open(waypoint_file, 'r') as f:
            waypoint = Waypoint.from_json(f.read())

        print(f'Waypoint loaded successfully!')
        print(f'URL: {waypoint.url}')
        print(f'Actions: {len(waypoint.actions)}')
        print(f'Assertions: {len(waypoint.assertions)}')
        print()

        # Create playback engine
        playback = NavigationPlayback(strict_assertions=True)

        # Replay waypoint
        print('Starting replay...')
        print('-' * 50)
        success = await playback.replay_waypoint(waypoint, headless=False)

        print()
        if success:
            print('Replay completed successfully!')
        else:
            print('Replay completed with warnings')

        return success

    except FileNotFoundError:
        print(f'ERROR: File not found: {waypoint_file}')
        return False
    except Exception as e:
        print(f'ERROR: {e}')
        return False


async def replay_from_ipfs(ipfs_hash: str):
    """
    Replay a waypoint from IPFS.

    Args:
        ipfs_hash: IPFS hash (CID) of the waypoint.
    """
    print('Replaying from IPFS')
    print('=' * 50)

    # Check for IPFS credentials
    api_key = os.getenv('PINATA_API_KEY')
    api_secret = os.getenv('PINATA_API_SECRET')

    if not api_key or not api_secret:
        print('ERROR: IPFS credentials not found')
        print('Set PINATA_API_KEY and PINATA_API_SECRET environment variables')
        return False

    try:
        # Initialize blockchain
        blockchain = IPFSBlockchain(api_key=api_key, api_secret=api_secret)

        # Retrieve waypoint from IPFS
        print(f'Retrieving waypoint from IPFS: {ipfs_hash}')
        waypoint = blockchain.retrieve_waypoint(ipfs_hash)

        print(f'Waypoint retrieved successfully!')
        print(f'URL: {waypoint.url}')
        print(f'Actions: {len(waypoint.actions)}')
        print(f'Assertions: {len(waypoint.assertions)}')
        print()

        # Create playback engine
        playback = NavigationPlayback(strict_assertions=True)

        # Replay waypoint
        print('Starting replay...')
        print('-' * 50)
        success = await playback.replay_waypoint(waypoint, headless=False)

        print()
        if success:
            print('Replay completed successfully!')
        else:
            print('Replay completed with warnings')

        return success

    except Exception as e:
        print(f'ERROR: {e}')
        return False


async def replay_with_lenient_assertions(waypoint_file: str):
    """
    Replay a waypoint with lenient assertion mode.

    Lenient mode logs assertion failures but doesn't stop execution.

    Args:
        waypoint_file: Path to waypoint JSON file.
    """
    print('Replaying with lenient assertions')
    print('=' * 50)

    try:
        # Load waypoint from file
        print(f'Loading waypoint from: {waypoint_file}')
        with open(waypoint_file, 'r') as f:
            waypoint = Waypoint.from_json(f.read())

        print(f'Waypoint loaded successfully!')
        print()

        # Create playback engine with lenient assertions
        playback = NavigationPlayback(strict_assertions=False)

        # Replay waypoint
        print('Starting replay (lenient mode)...')
        print('-' * 50)
        success = await playback.replay_waypoint(waypoint, headless=False)

        print()
        if success:
            print('Replay completed successfully!')
        else:
            print('Replay completed with assertion warnings (non-fatal)')

        return success

    except Exception as e:
        print(f'ERROR: {e}')
        return False


async def verify_and_replay(waypoint_file: str):
    """
    Verify waypoint integrity before replaying.

    Args:
        waypoint_file: Path to waypoint JSON file.
    """
    print('Verifying waypoint integrity before replay')
    print('=' * 50)

    try:
        # Load waypoint from file
        print(f'Loading waypoint from: {waypoint_file}')
        with open(waypoint_file, 'r') as f:
            waypoint = Waypoint.from_json(f.read())

        print(f'Waypoint loaded successfully!')
        print()

        # Verify integrity
        print('Verifying waypoint integrity...')
        computed_hash = waypoint.compute_hash()
        print(f'Computed hash: {computed_hash}')
        print(f'Stored hash: {waypoint.hash}')

        if waypoint.verify_hash(waypoint.hash):
            print('Waypoint integrity verified!')
            print()

            # Proceed with replay
            print('Starting replay...')
            print('-' * 50)
            playback = NavigationPlayback(strict_assertions=True)
            success = await playback.replay_waypoint(waypoint, headless=False)

            print()
            if success:
                print('Replay completed successfully!')
            else:
                print('Replay completed with warnings')

            return success
        else:
            print('ERROR: Waypoint integrity check failed!')
            print('The waypoint may have been tampered with.')
            return False

    except Exception as e:
        print(f'ERROR: {e}')
        return False


async def batch_replay(waypoint_dir: str):
    """
    Replay all waypoints in a directory.

    Args:
        waypoint_dir: Directory containing waypoint JSON files.
    """
    print('Batch replaying waypoints')
    print('=' * 50)

    waypoint_dir = Path(waypoint_dir)

    if not waypoint_dir.exists():
        print(f'ERROR: Directory not found: {waypoint_dir}')
        return False

    # Find all JSON files
    waypoint_files = list(waypoint_dir.glob('*.json'))

    if not waypoint_files:
        print(f'No waypoint JSON files found in: {waypoint_dir}')
        return False

    print(f'Found {len(waypoint_files)} waypoint files')
    print()

    results = {}
    playback = NavigationPlayback(strict_assertions=False)

    for waypoint_file in waypoint_files:
        print(f'Replaying: {waypoint_file.name}')
        try:
            with open(waypoint_file, 'r') as f:
                waypoint = Waypoint.from_json(f.read())

            success = await playback.replay_waypoint(waypoint, headless=True)
            results[waypoint_file.name] = 'PASS' if success else 'FAIL'
            print(f'  Result: {results[waypoint_file.name]}')

        except Exception as e:
            results[waypoint_file.name] = f'ERROR: {e}'
            print(f'  Result: ERROR - {e}')

        print()

    # Summary
    print('=' * 50)
    print('Batch Replay Summary')
    print('-' * 50)
    for filename, result in results.items():
        status = 'PASS' if result == 'PASS' else 'FAIL'
        print(f'{filename}: {result}')

    return all(r == 'PASS' for r in results.values())


async def main():
    """Run the examples."""
    import sys

    if len(sys.argv) > 1:
        example = sys.argv[1]
        args = sys.argv[2:] if len(sys.argv) > 2 else []
    else:
        example = 'help'
        args = []

    if example == 'file':
        if args:
            await replay_from_file(args[0])
        else:
            print('Usage: python replay_example.py file <waypoint_file>')

    elif example == 'ipfs':
        if args:
            await replay_from_ipfs(args[0])
        else:
            print('Usage: python replay_example.py ipfs <ipfs_hash>')

    elif example == 'lenient':
        if args:
            await replay_with_lenient_assertions(args[0])
        else:
            print('Usage: python replay_example.py lenient <waypoint_file>')

    elif example == 'verify':
        if args:
            await verify_and_replay(args[0])
        else:
            print('Usage: python replay_example.py verify <waypoint_file>')

    elif example == 'batch':
        if args:
            await batch_replay(args[0])
        else:
            print('Usage: python replay_example.py batch <waypoint_directory>')

    else:
        print('Replay Examples')
        print('=' * 50)
        print('Usage: python replay_example.py <example> [args]')
        print()
        print('Examples:')
        print('  file <waypoint_file>       - Replay from JSON file')
        print('  ipfs <ipfs_hash>           - Replay from IPFS')
        print('  lenient <waypoint_file>    - Replay with lenient assertions')
        print('  verify <waypoint_file>     - Verify and replay')
        print('  batch <waypoint_directory> - Batch replay all waypoints')


if __name__ == '__main__':
    asyncio.run(main())
