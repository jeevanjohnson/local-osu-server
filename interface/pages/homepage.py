from nicegui import ui
import core.usecases.application.authentication as auth_usecases

def build() -> None:
    
    @ui.page("/")
    def homepage() -> None:
        
        if auth_usecases.is_logged_in():
            ui.navigate.to("/dashboard")
        else:
            ui.navigate.to("/login")
        
