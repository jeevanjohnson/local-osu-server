import packets
from ext import glob
from typing import Union
from server import Request
from typing import Optional
from typing import Callable
from server import Response

def local_message(
    message: str, 
    channel: str = '#osu'
) -> bytes:
    return packets.sendMsg(
        client = 'local',
        msg = message,
        target = channel,
        userid = -1,
    )

def button_func(func: Callable) -> Callable:

    async def editied_func(request: Request) -> Response:
        return await func(**request.params)

    return editied_func

class Button:
    def __init__(
        self, name: str, 
        func: Callable, 
        docs: Optional[str] = None,
    ) -> None:

        self.name = name
        self.docs = docs
        self._func = func
        self.func = button_func(func)

        self.menu_name: Optional[str] = None
        self.category_name: Optional[str] = None
    
    @property
    def url(self) -> str:
        fmt_url = 'http://127.0.0.1:5000/{menu_name}{category_name}{name}'

        return fmt_url.format(
            menu_name = '' if not self.menu_name else f'{self.menu_name}/',
            category_name = '' if not self.category_name else f'{self.category_name}/',
            name = self.name,
        ).lower().replace(' ', '_')
    
    def __str__(self) -> str:
        fmt_button = '[{url} {name}]{docs}'

        return fmt_button.format(
            url = self.url,
            name = self.name,
            docs = '' if not self.docs else f' | {self.docs}'
        )

    @property
    def loaded(self) -> bool:
        path = self.url.removeprefix('http://127.0.0.1:5000')
        
        if path not in glob.handlers:
            return False
        else:
            return True
    
    def load(self) -> None:
        path = self.url.removeprefix('http://127.0.0.1:5000')
        glob.handlers[path] = self.func

class Menu:
    def __init__(self, name: str, **kwargs: Union[Button, list[Button]]) -> None:
        self.name = name
        self.categories = kwargs
    
    def add_button(self, category: str, button: Button) -> None:
        if category in self.categories:
            buttons = self.categories[category]
            if isinstance(buttons, list):
                buttons.append(button)
                return
            else:
                self.categories[category] = [buttons, button]
                return
        else:
            self.categories[category] = button
            return

    def as_binary(self, newline_per_category: bool = False) -> bytearray:
        menu_binary = bytearray(packets.userSilenced(-1))

        menu_binary += local_message(self.name)
        if self.categories:
            menu_binary += local_message('\n')

        categories_as_items = self.categories.items()
        len_categories = len(categories_as_items)

        for idx, (category, buttons) in enumerate(categories_as_items):
            menu_binary += local_message(category)

            if not isinstance(buttons, list):
                buttons = [buttons]
            
            for button in buttons:
                if not button.loaded:
                    if not button.menu_name:
                        button.menu_name = self.name
                    
                    if not button.category_name:
                        button.category_name = category

                    button.load()
                
                menu_binary += local_message(str(button))
            
            if newline_per_category and idx != (len_categories - 1):
                menu_binary += local_message('\n')
            
        return menu_binary