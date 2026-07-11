import pytest

from app.commands import (
    AppCommand,
    CommandPriority,
    CommandType,
    Direction,
)
from app.state import control_mode


def test_move_command_contains_direction_and_distance() -> None:
    command = AppCommand.move(Direction.UP)

    assert command.type == CommandType.MOVE
    assert command.direction == Direction.UP
    assert command.amount == 30


def test_rotate_command_defaults_to_ninety_degrees() -> None:
    command = AppCommand.rotate(Direction.LEFT)

    assert command.type == CommandType.ROTATE
    assert command.direction == Direction.LEFT
    assert command.amount == 90


def test_follow_command_does_not_choose_a_target() -> None:
    command = AppCommand.start_follow()

    assert command.type == CommandType.START_FOLLOW
    assert not hasattr(command, "target_id")


def test_mode_command_identifies_requested_mode() -> None:
    command = AppCommand.set_control_mode(control_mode.VOICE_COMMANDS)

    assert command.type == CommandType.SET_CONTROL_MODE
    assert command.mode == control_mode.VOICE_COMMANDS


def test_photo_command_defaults_to_non_blocking_three_second_delay() -> None:
    command = AppCommand.take_photo()

    assert command.type == CommandType.TAKE_PHOTO
    assert command.delay_seconds == 3.0
    assert command.priority == CommandPriority.BACKGROUND


def test_land_has_higher_priority_than_flight_and_background_actions() -> None:
    assert AppCommand.land().priority > AppCommand.move(Direction.LEFT).priority
    assert AppCommand.land().priority > AppCommand.take_photo().priority


def test_stop_follow_has_higher_priority_than_mode_change() -> None:
    assert (
        AppCommand.stop_follow().priority
        > AppCommand.set_control_mode(control_mode.GESTURES).priority
    )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: AppCommand.move(Direction.UP, 0),
        lambda: AppCommand.rotate(Direction.FORWARD, 90),
        lambda: AppCommand.take_photo(-1),
        lambda: AppCommand(CommandType.LAND, amount=30),
        lambda: AppCommand(CommandType.SET_CONTROL_MODE),
    ],
)
def test_invalid_command_payloads_are_rejected(factory) -> None:
    with pytest.raises(ValueError):
        factory()


def test_commands_are_immutable() -> None:
    command = AppCommand.take_off()

    with pytest.raises((AttributeError, TypeError)):
        command.amount = 30


@pytest.mark.parametrize(
    ("command", "description"),
    [
        (AppCommand.take_off(), "TAKE OFF"),
        (AppCommand.move(Direction.LEFT, 30), "MOVE LEFT 30 cm"),
        (AppCommand.rotate(Direction.RIGHT, 90), "ROTATE RIGHT 90 deg"),
        (AppCommand.flip(Direction.BACK), "FLIP BACK"),
        (AppCommand.take_photo(3), "TAKE PHOTO IN 3s"),
    ],
)
def test_command_has_human_readable_description(
    command: AppCommand,
    description: str,
) -> None:
    assert command.description == description
