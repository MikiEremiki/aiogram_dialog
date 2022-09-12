from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Dict, List, Optional, Union

from aiogram.types import CallbackQuery, InlineKeyboardButton

from aiogram_dialog.api.entities import ChatEvent
from aiogram_dialog.api.protocols import DialogManager, DialogProtocol
from aiogram_dialog.widgets.text import Case, Text
from aiogram_dialog.widgets.widget_event import (
    ensure_event_processor,
    WidgetEventProcessor,
)
from .base import Keyboard
from ..managed import ManagedWidgetAdapter

OnStateChanged = Callable[
    [ChatEvent, "ManagedCheckboxAdapter", DialogManager], Awaitable,
]
OnStateChangedVariant = Union[
    OnStateChanged, WidgetEventProcessor, None,
]


class BaseCheckbox(Keyboard, ABC):
    def __init__(
            self,
            checked_text: Text,
            unchecked_text: Text,
            id: str,
            on_click: OnStateChangedVariant = None,
            on_state_changed: OnStateChangedVariant = None,
            when: Union[str, Callable] = None,
    ):
        super().__init__(id, when)
        self.text = Case(
            {True: checked_text, False: unchecked_text},
            selector=self._is_text_checked,
        )
        self.on_click = ensure_event_processor(on_click)
        self.on_state_changed = ensure_event_processor(on_state_changed)

    async def _render_keyboard(
            self, data: Dict, manager: DialogManager,
    ) -> List[List[InlineKeyboardButton]]:
        checked = int(self.is_checked(manager))
        # store current checked status in callback data
        return [
            [
                InlineKeyboardButton(
                    text=await self.text.render_text(data, manager),
                    callback_data=self._item_callback_data(checked),
                ),
            ],
        ]

    async def _process_item_callback(
            self,
            c: CallbackQuery,
            data: str,
            dialog: DialogProtocol,
            manager: DialogManager,
    ) -> bool:
        # remove prefix and cast "0" as False, "1" as True
        checked = data != "0"
        await self.on_click.process_event(c, self.managed(manager), manager)
        await self.set_checked(c, not checked, manager)
        return True

    def _is_text_checked(
            self, data: Dict, case: Case, manager: DialogManager,
    ) -> bool:
        del data  # unused
        del case  # unused
        return self.is_checked(manager)

    @abstractmethod
    def is_checked(self, manager: DialogManager) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def set_checked(
            self, event: ChatEvent, checked: bool,
            manager: DialogManager,
    ):
        raise NotImplementedError


class Checkbox(BaseCheckbox):
    def __init__(
            self,
            checked_text: Text,
            unchecked_text: Text,
            id: str,
            on_click: Union[OnStateChanged, WidgetEventProcessor, None] = None,
            on_state_changed: Optional[OnStateChanged] = None,
            default: bool = False,
            when: Union[str, Callable] = None,
    ):
        super().__init__(
            checked_text, unchecked_text, id, on_click, on_state_changed, when,
        )
        self.default = default

    def is_checked(self, manager: DialogManager) -> bool:
        return self.get_widget_data(manager, self.default)

    async def set_checked(
            self, event: ChatEvent, checked: bool,
            manager: DialogManager,
    ) -> None:
        self.set_widget_data(manager, checked)
        await self.on_state_changed.process_event(
            event, self.managed(manager), manager,
        )

    def managed(self, manager: DialogManager):
        return ManagedCheckboxAdapter(self, manager)


class ManagedCheckboxAdapter(ManagedWidgetAdapter[Checkbox]):
    def is_checked(self) -> bool:
        return self.widget.is_checked(self.manager)

    async def set_checked(
            self,
            event: ChatEvent,
            checked: bool,
    ) -> None:
        return await self.widget.set_checked(event, checked, self.manager)
