# import asyncio
# from networks import connectionManager
# from encryptions import Encryption
# from textual.app import App
# from textual.widgets import Static


# class HelloWorld(App):
#     BINDINGS = [
#         ("escape", "quit", "press escape to quit the app"),
#         ("ctrl+c", "", "press escape to quit the app")  # You can map multiple keys to the same action
#     ]
#     def compose(self):
#         yield Static("hello world!")


# if __name__ == '__main__':
#     app = HelloWorld()
#     app.run()


# # from os import system
# from textual import on
# from textual.app import App, ComposeResult
# from textual.widgets import Button

# class SuspendingApp(App[None]):

#     def compose(self) -> ComposeResult:
#         yield Button("Open the editor", id="edit")

#     @on(Button.Pressed, "#edit")
#     def run_external_editor(self) -> None:
#         with self.suspend():  
#             # system("code .")
#             print("success")
#             print(input("word: "))
            


# if __name__ == "__main__":
#     SuspendingApp().run()



# from textual.app import App, ComposeResult
# from textual.widgets import Button, Label


# class QuestionApp(App[str]):
#     CSS_PATH = "me.tcss"

#     def compose(self) -> ComposeResult:
#         yield Label("Do you love Textual?", id="question")
#         yield Button("Yes", id="yes", variant="primary")
#         yield Button("No", id="no", variant="error")

#     def on_button_pressed(self, event: Button.Pressed) -> None:
#         self.exit(event.button.id)


# if __name__ == "__main__":
#     app = QuestionApp()
#     reply = app.run()
#     print(reply)\


from textual.app import App, ComposeResult
from textual.events import Key
from textual.widgets import Button, Header, Label


class MyApp(App[str]):
    CSS_PATH = "me.tcss"
    TITLE = "A Question App"
    SUB_TITLE = "The most important question"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Do you love Textual?", id="question")
        yield Button("Yes", id="yes", variant="primary")
        yield Button("No", id="no", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)

    def on_key(self, event: Key):
        self.title = event.key
        self.sub_title = f"You just pressed {event.key}!"


if __name__ == "__main__":
    app = MyApp()
    reply = app.run()
    print(reply)