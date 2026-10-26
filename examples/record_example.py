#!/usr/bin/env python
"""
Example: Recording a login flow with Nexus.

This example demonstrates how to programmatically record a web navigation
sequence, including clicks, text input, and assertions.
"""

import asyncio
import os
from nexus import NavigationRecorder, Waypoint
from nexus.logging_util import setup_logging

# Set up logging
setup_logging(level='INFO')


async def record_example_login():
    """
    Record a typical login flow.

    This is a demonstration. In practice, you would:
    1. Start recording
    2. Perform actions (clicks, typing, navigation)
    3. Add assertions to verify behavior
    4. Stop recording and save
    """
    print('Starting Nexus Recording Example')
    print('=' * 50)

    # Create recorder
    recorder = NavigationRecorder()

    # Start recording on a login page
    print('Recording login flow...')
    try:
        await recorder.start_recording(
            'https://example.com/login',
            headless=False,  # Show browser window
        )

        # Get the recorded waypoint
        waypoint = await recorder.stop_recording()

        if waypoint:
            print()
            print('Recording Complete!')
            print('-' * 50)
            print(f'URL: {waypoint.url}')
            print(f'Actions recorded: {len(waypoint.actions)}')
            print(f'Assertions recorded: {len(waypoint.assertions)}')
            print(f'Waypoint hash: {waypoint.hash}')

            # Save waypoint to file
            waypoint_file = 'example_login_waypoint.json'
            with open(waypoint_file, 'w') as f:
                f.write(waypoint.to_json())
            print(f'Saved to: {waypoint_file}')

            return waypoint
        else:
            print('No waypoint recorded')
            return None

    except KeyboardInterrupt:
        print()
        print('Recording interrupted by user')
        return None
    except Exception as e:
        print(f'Error during recording: {e}')
        raise


async def record_with_actions():
    """
    Record a navigation with manually added actions and assertions.

    This demonstrates the API for adding actions and assertions programmatically.
    """
    from nexus.waypoint import ActionType, AssertionType

    print('Creating waypoint with manual actions...')
    print('=' * 50)

    # Create waypoint
    waypoint = Waypoint(
        url='https://example.com/checkout',
        description='E-commerce checkout flow',
    )

    # Add navigation action
    waypoint.add_action(
        ActionType.NAVIGATE,
        value='https://example.com/checkout',
    )

    # Add click action
    waypoint.add_action(
        ActionType.CLICK,
        selector='#shipping-address-checkbox',
    )

    # Add typing action
    waypoint.add_action(
        ActionType.TYPE,
        selector='#zip-code',
        value='12345',
    )

    # Add wait action
    waypoint.add_action(
        ActionType.WAIT,
        timeout=2.0,
    )

    # Add select action
    waypoint.add_action(
        ActionType.SELECT,
        selector='#shipping-method',
        value='overnight',
    )

    # Add click for submit
    waypoint.add_action(
        ActionType.CLICK,
        selector='#submit-order',
    )

    # Add assertions to verify behavior
    waypoint.add_assertion(
        AssertionType.TEXT_PRESENT,
        target='Order Confirmed',
    )

    waypoint.add_assertion(
        AssertionType.URL_MATCHES,
        target='/confirmation',
    )

    waypoint.add_assertion(
        AssertionType.ELEMENT_VISIBLE,
        target='#order-number',
    )

    # Compute hash
    waypoint.update_hash()

    print('Waypoint created successfully!')
    print('-' * 50)
    print(f'URL: {waypoint.url}')
    print(f'Description: {waypoint.description}')
    print(f'Actions: {len(waypoint.actions)}')
    for i, action in enumerate(waypoint.actions, 1):
        print(f'  {i}. {action.action_type} {action.selector or action.value or ""}')
    print(f'Assertions: {len(waypoint.assertions)}')
    for i, assertion in enumerate(waypoint.assertions, 1):
        print(f'  {i}. {assertion.assertion_type} {assertion.target}')
    print(f'Hash: {waypoint.hash}')

    # Save waypoint
    waypoint_file = 'example_checkout_waypoint.json'
    with open(waypoint_file, 'w') as f:
        f.write(waypoint.to_json())
    print(f'Saved to: {waypoint_file}')

    return waypoint


async def record_with_ipfs():
    """
    Record a navigation and upload to IPFS.

    Requires PINATA_API_KEY and PINATA_API_SECRET environment variables.
    """
    from nexus import IPFSBlockchain

    print('Recording and uploading to IPFS...')
    print('=' * 50)

    # Check for IPFS credentials
    api_key = os.getenv('PINATA_API_KEY')
    api_secret = os.getenv('PINATA_API_SECRET')

    if not api_key or not api_secret:
        print('ERROR: IPFS credentials not found')
        print('Set PINATA_API_KEY and PINATA_API_SECRET environment variables')
        return None

    try:
        # Create a waypoint
        waypoint = await record_with_actions()

        if not waypoint:
            return None

        # Initialize blockchain
        blockchain = IPFSBlockchain(api_key=api_key, api_secret=api_secret)

        # Store waypoint on IPFS
        print()
        print('Uploading to IPFS...')
        ipfs_hash = blockchain.store_waypoint(
            waypoint,
            description='Example checkout flow',
        )

        print(f'Successfully uploaded to IPFS!')
        print(f'IPFS Hash: {ipfs_hash}')
        print()
        print('To replay this waypoint:')
        print(f'  nexus replay {ipfs_hash}')

        return ipfs_hash

    except Exception as e:
        print(f'Error: {e}')
        return None


async def main():
    """Run the examples."""
    import sys

    if len(sys.argv) > 1:
        example = sys.argv[1]
    else:
        example = 'manual'

    if example == 'manual':
        await record_with_actions()
    elif example == 'ipfs':
        await record_with_ipfs()
    elif example == 'interactive':
        await record_example_login()
    else:
        print('Usage: python record_example.py [manual|ipfs|interactive]')


if __name__ == '__main__':
    asyncio.run(main())
