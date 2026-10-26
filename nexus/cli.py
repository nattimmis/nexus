"""
Command-line interface for Nexus.

Provides CLI commands for recording, replaying, and verifying waypoints.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import click
import json
from nexus.recorder import NavigationRecorder
from nexus.playback import NavigationPlayback
from nexus.blockchain import IPFSBlockchain
from nexus.waypoint import Waypoint
from nexus.logging_util import setup_logging, get_logger

logger = get_logger(__name__)


@click.group()
@click.option(
    '--log-level',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR'], case_sensitive=False),
    default='INFO',
    help='Logging level.',
)
@click.pass_context
def main(ctx: click.Context, log_level: str) -> None:
    """
    Nexus: Record and replay web navigation on blockchain (IPFS).

    Record Playwright navigation sequences and store them immutably on IPFS.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Set up logging
    setup_logging(level=log_level)
    logger.debug(f'Logging level set to {log_level}')


@main.command()
@click.argument('url')
@click.option(
    '--headless/--no-headless',
    default=False,
    help='Run browser in headless mode (default: visible).',
)
@click.option(
    '--output',
    '-o',
    type=click.Path(),
    help='Save waypoint to JSON file.',
)
@click.option(
    '--description',
    '-d',
    type=str,
    help='Description for the waypoint.',
)
def record(url: str, headless: bool, output: Optional[str], description: str) -> None:
    """
    Start recording navigation on a URL.

    \b
    Example:
        nexus record https://example.com
        nexus record https://example.com --output waypoint.json --description "Login test"
    """
    click.echo(click.style('Nexus Recording Started', fg='green', bold=True))
    click.echo(f'URL: {url}')
    click.echo()
    click.echo('Commands:')
    click.echo('  c <selector>             - Click element')
    click.echo('  t <selector> <text>      - Type text into element')
    click.echo('  s <selector> <value>     - Select option in dropdown')
    click.echo('  w <seconds>              - Wait (pause)')
    click.echo('  a text <text>            - Assert text is present')
    click.echo('  a element <selector>     - Assert element is visible')
    click.echo('  a url <pattern>          - Assert URL matches pattern')
    click.echo('  screenshot <filename>    - Take screenshot')
    click.echo('  done                     - Finish recording')
    click.echo()

    try:
        recorder = NavigationRecorder()
        waypoint = asyncio.run(
            _interactive_record(recorder, url, headless, description)
        )

        if waypoint:
            click.echo()
            click.echo(click.style('Recording complete!', fg='green', bold=True))
            click.echo(f'Actions recorded: {len(waypoint.actions)}')
            click.echo(f'Assertions recorded: {len(waypoint.assertions)}')
            click.echo(f'Waypoint hash: {waypoint.hash}')
            click.echo()

            # Save to file if specified
            if output:
                waypoint.update_hash()
                with open(output, 'w') as f:
                    f.write(waypoint.to_json())
                click.echo(click.style(f'Waypoint saved to {output}', fg='cyan'))

            # Offer to upload to IPFS
            if click.confirm('Upload to IPFS?'):
                _upload_to_ipfs(waypoint)

    except Exception as e:
        click.echo(click.style(f'Error: {e}', fg='red'), err=True)
        sys.exit(1)


async def _interactive_record(
    recorder: NavigationRecorder,
    url: str,
    headless: bool,
    description: str,
) -> Optional[Waypoint]:
    """
    Run interactive recording session.

    Args:
        recorder: NavigationRecorder instance.
        url: URL to record.
        headless: Whether to run headless.
        description: Waypoint description.

    Returns:
        Recorded waypoint or None if cancelled.
    """
    await recorder.start_recording(url, headless=headless)
    waypoint = recorder.waypoint

    if waypoint:
        if description:
            waypoint.description = description

        # Interactive command loop
        while True:
            try:
                cmd = click.prompt('nexus').strip().lower()

                if not cmd:
                    continue

                parts = cmd.split(' ', 1)
                action = parts[0]

                if action == 'done':
                    break

                elif action == 'c' and len(parts) > 1:  # click
                    selector = parts[1]
                    await recorder.record_click(selector)
                    click.echo(click.style(f'Recorded click: {selector}', fg='cyan'))

                elif action == 't' and len(parts) > 1:  # type
                    args = parts[1].split(' ', 1)
                    if len(args) == 2:
                        selector, text = args
                        await recorder.record_type(selector, text)
                        click.echo(
                            click.style(f'Recorded type: {selector} = {text}', fg='cyan')
                        )

                elif action == 's' and len(parts) > 1:  # select
                    args = parts[1].split(' ', 1)
                    if len(args) == 2:
                        selector, value = args
                        await recorder.record_select(selector, value)
                        click.echo(
                            click.style(f'Recorded select: {selector} = {value}', fg='cyan')
                        )

                elif action == 'w' and len(parts) > 1:  # wait
                    try:
                        timeout = float(parts[1])
                        await recorder.record_wait(timeout)
                        click.echo(click.style(f'Recorded wait: {timeout}s', fg='cyan'))
                    except ValueError:
                        click.echo('Invalid timeout value')

                elif action == 'a' and len(parts) > 1:  # assertion
                    assert_parts = parts[1].split(' ', 1)
                    if len(assert_parts) == 2:
                        assert_type = assert_parts[0]
                        assert_target = assert_parts[1]

                        if assert_type == 'text':
                            await recorder.record_assertion_text_present(assert_target)
                            click.echo(
                                click.style(
                                    f'Recorded assertion: text present = {assert_target}',
                                    fg='cyan',
                                )
                            )
                        elif assert_type == 'element':
                            await recorder.record_assertion_element_visible(assert_target)
                            click.echo(
                                click.style(
                                    f'Recorded assertion: element visible = {assert_target}',
                                    fg='cyan',
                                )
                            )
                        elif assert_type == 'url':
                            await recorder.record_assertion_url_matches(assert_target)
                            click.echo(
                                click.style(
                                    f'Recorded assertion: url matches = {assert_target}',
                                    fg='cyan',
                                )
                            )

                elif action == 'screenshot' and len(parts) > 1:  # screenshot
                    filename = parts[1]
                    click.echo(
                        click.style(f'Screenshot would be saved to {filename}', fg='yellow')
                    )

                else:
                    click.echo('Unknown command')

            except KeyboardInterrupt:
                click.echo()
                click.echo('Recording interrupted')
                break
            except Exception as e:
                click.echo(click.style(f'Error: {e}', fg='red'), err=True)

    return waypoint


@main.command()
@click.argument('ipfs_hash')
@click.option(
    '--headless/--no-headless',
    default=True,
    help='Run browser in headless mode (default: headless).',
)
@click.option(
    '--strict/--no-strict',
    default=True,
    help='Fail on assertion errors (default: strict).',
)
def replay(ipfs_hash: str, headless: bool, strict: bool) -> None:
    """
    Replay a recorded waypoint from IPFS.

    \b
    Example:
        nexus replay QmXxxx...
        nexus replay QmXxxx... --no-headless
    """
    try:
        click.echo(click.style('Nexus Playback Started', fg='green', bold=True))
        click.echo(f'IPFS Hash: {ipfs_hash}')
        click.echo()

        # Retrieve waypoint from IPFS
        blockchain = IPFSBlockchain()
        waypoint = blockchain.retrieve_waypoint(ipfs_hash)

        click.echo(f'URL: {waypoint.url}')
        click.echo(f'Actions: {len(waypoint.actions)}')
        click.echo(f'Assertions: {len(waypoint.assertions)}')
        click.echo()

        # Replay waypoint
        playback = NavigationPlayback(strict_assertions=strict)
        success = asyncio.run(playback.replay_waypoint(waypoint, headless=headless))

        if success:
            click.echo()
            click.echo(click.style('Playback completed successfully!', fg='green', bold=True))
        else:
            click.echo()
            click.echo(
                click.style(
                    'Playback completed with warnings',
                    fg='yellow',
                    bold=True,
                )
            )

    except Exception as e:
        click.echo(click.style(f'Error: {e}', fg='red'), err=True)
        sys.exit(1)


@main.command()
@click.argument('ipfs_hash')
@click.argument('expected_hash', required=False)
def verify(ipfs_hash: str, expected_hash: Optional[str]) -> None:
    """
    Verify waypoint integrity from IPFS.

    \b
    Example:
        nexus verify QmXxxx...
        nexus verify QmXxxx... abc123...
    """
    try:
        click.echo(click.style('Verifying waypoint integrity', fg='green', bold=True))
        click.echo(f'IPFS Hash: {ipfs_hash}')
        click.echo()

        blockchain = IPFSBlockchain()
        waypoint = blockchain.retrieve_waypoint(ipfs_hash)

        computed_hash = waypoint.compute_hash()
        click.echo(f'Computed hash: {computed_hash}')
        click.echo(f'Stored hash: {waypoint.hash}')

        if expected_hash:
            is_valid = waypoint.verify_hash(expected_hash)
            if is_valid:
                click.echo()
                click.echo(
                    click.style('Integrity verified!', fg='green', bold=True)
                )
            else:
                click.echo()
                click.echo(
                    click.style(
                        'Integrity check failed!',
                        fg='red',
                        bold=True,
                    )
                )
                sys.exit(1)
        else:
            click.echo()
            click.echo(
                click.style(
                    'Waypoint retrieved successfully',
                    fg='green',
                    bold=True,
                )
            )

    except Exception as e:
        click.echo(click.style(f'Error: {e}', fg='red'), err=True)
        sys.exit(1)


@main.command()
@click.argument('waypoint_file', type=click.Path(exists=True))
@click.option(
    '--description',
    '-d',
    type=str,
    help='Description for the upload.',
)
def upload(waypoint_file: str, description: str) -> None:
    """
    Upload a waypoint JSON file to IPFS.

    \b
    Example:
        nexus upload waypoint.json
        nexus upload waypoint.json -d "My navigation test"
    """
    _upload_waypoint_file(waypoint_file, description)


@main.command()
@click.option(
    '--limit',
    '-l',
    type=int,
    default=10,
    help='Number of pins to list.',
)
def list_pins(limit: int) -> None:
    """
    List all pinned waypoints on IPFS.

    \b
    Example:
        nexus list-pins
        nexus list-pins --limit 20
    """
    try:
        click.echo(click.style('Your pinned waypoints:', fg='green', bold=True))
        click.echo()

        blockchain = IPFSBlockchain()
        pins = blockchain.list_pins()

        if not pins:
            click.echo('No pinned waypoints found')
            return

        for i, pin in enumerate(pins[:limit], 1):
            ipfs_hash = pin.get('ipfsHash', 'N/A')
            name = pin.get('name', 'Unnamed')
            size = pin.get('size', 0)
            created = pin.get('dateQueued', 'N/A')

            click.echo(f'{i}. {name}')
            click.echo(f'   Hash: {ipfs_hash}')
            click.echo(f'   Size: {size} bytes')
            click.echo(f'   Created: {created}')
            click.echo()

    except Exception as e:
        click.echo(click.style(f'Error: {e}', fg='red'), err=True)
        sys.exit(1)


def _upload_to_ipfs(waypoint: Waypoint) -> None:
    """
    Upload waypoint to IPFS.

    Args:
        waypoint: Waypoint to upload.
    """
    try:
        blockchain = IPFSBlockchain()
        description = waypoint.description or 'Recorded navigation'
        ipfs_hash = blockchain.store_waypoint(waypoint, description)

        click.echo()
        click.echo(click.style('Upload successful!', fg='green', bold=True))
        click.echo(f'IPFS Hash: {ipfs_hash}')
        click.echo()
        click.echo('To replay this waypoint:')
        click.echo(click.style(f'  nexus replay {ipfs_hash}', fg='cyan'))

    except Exception as e:
        click.echo(click.style(f'Upload error: {e}', fg='red'), err=True)


def _upload_waypoint_file(waypoint_file: str, description: Optional[str]) -> None:
    """
    Upload waypoint from JSON file to IPFS.

    Args:
        waypoint_file: Path to waypoint JSON file.
        description: Optional description.
    """
    try:
        with open(waypoint_file, 'r') as f:
            waypoint = Waypoint.from_json(f.read())

        if description:
            waypoint.description = description

        _upload_to_ipfs(waypoint)

    except Exception as e:
        click.echo(click.style(f'Error: {e}', fg='red'), err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
