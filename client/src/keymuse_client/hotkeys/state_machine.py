from dataclasses import dataclass


@dataclass(frozen=True)
class HotkeyState:
    ctrl_down: bool = False
    alt_down: bool = False

    def is_active(self) -> bool:
        return self.ctrl_down and self.alt_down


def update_state(state: HotkeyState, ctrl_down: bool, alt_down: bool) -> HotkeyState:
    return HotkeyState(ctrl_down=ctrl_down, alt_down=alt_down)
