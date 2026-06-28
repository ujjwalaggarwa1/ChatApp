try:
    import asyncio

    from networks import connectionManager
    from encryptions import Encryption
    import Logger

    from textual.app import App, ComposeResult
    from textual.screen import Screen
    from textual.widgets import Header, Footer, Static, Input, RichLog, Button, ContentSwitcher
    from textual.widget import Widget
    from textual.validation import Regex
    from textual.containers import Vertical, Horizontal, VerticalScroll
    from textual.binding import Binding
    
    Logger.setup_logging(backup_count=1)
    logger = Logger.get_module_logger("Main")

    per = True
except ImportError:
    per = False
    print("Unable to load modules, run: pip install -r requirements.txt ")


class MainApp(App[None]): #type:ignore
    
    theme = "nord" #type:ignore
    
    BINDINGS = [
        Binding(key="escape", action="quit", description="Exit"),
        Binding(key="ctrl+q", action="", description="", show=False)
        ]


    def __init__(self):
        super().__init__()
        self.crypticEngine: Encryption = Encryption()
        self.networkEngine: connectionManager | None = None


    def on_mount(self) -> None:
        self.install_screen(SetupScreen(), "setup")
        self.install_screen(ChatScreen(), "chat")
        
        self.push_screen("setup")


    def startNetworks(self, nodeUser:str):
        '''
        Starts the backend processes
        '''
        self.networkEngine = connectionManager(nodeUser, self.crypticEngine)
        asyncio.create_task(self.networkEngine.start_server())


class SetupScreen(Screen[None]): #type:ignore
    '''
    Handles the landing page.
    '''
    
    app: MainApp # the program was giving error without this type hint
    
    CSS_PATH = "styles/startup.tcss"
    
    def compose(self) -> ComposeResult:
        self.title="SetUp Screen"
        
        yield Header(show_clock=True, time_format="%I:%M:%S%p", icon="Chat")
        
        with Vertical():
            yield Static(
                "[b]ChatApp Entry Page[/b]\n\n"
                "Welcome to the node configuration terminal.\n"
                "Please enter your node identity name below:",
                id="prompt"
            )
            
            yield Input(
                placeholder="Enter Your Name...",
                id="identity_input",
                validators=[Regex(regex=r"\S+",
                                failure_description="Name cannot be empty")]
            ) # i dont get how to make a good regex thats why this regex was made by ai
            
        yield Footer()
        
    def on_mount(self) -> None:
        self.query_one("#identity_input").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if not event.validation_result or not event.validation_result.is_valid:
            self.app.bell() #this is a cool function i found that will make a beep on wrong input :)
            return 
        
        chosen_name = event.value.strip().capitalize()
        
        self.app.startNetworks(chosen_name)
        self.app.switch_screen("chat")

class ConversationPane(Widget):
    """An independent container holding the history and input for a single chat."""
    
    def __init__(self, peer_name: str, **kwargs):
        super().__init__(**kwargs)
        self.peer_name = peer_name

    def compose(self) -> ComposeResult:
        with Vertical():
            yield RichLog(id=f"log_{self.id}", max_lines=1000, wrap=True)
            yield Input(placeholder=f"Message {self.peer_name}...", id=f"input_{self.id}")

class ChatScreen(Screen[None]): #type:ignore
    '''
    handles the discovery and chat page
    '''
    app: MainApp
    
    CSS_PATH = "styles/chat.tcss"
    has_active_popup = False
    
    def compose(self) -> ComposeResult:
        self.title='Chat Screen'
        
        yield Header(show_clock=True, time_format="%I:%M:%S%p", icon="Chat")

        with Horizontal():
            
            with Vertical(id="sidebar"):
                
                with Vertical(id="Available"):
                    yield Static("[b][cyan]Available People[/cyan][/b]")
                    yield VerticalScroll(id="peopleList")
                    
                with Vertical(id="Connected"):
                    yield Static("[b][green]Connected People[/green][/b]")
                    yield VerticalScroll(id="connectedList")
                    
                    
            with Vertical(id="main_viewport"):
                
                with ContentSwitcher(id="chat_switcher", initial="empty_view"):
                    yield Static("Select a chat to connect.", id="empty_view")
                    
                with Vertical(id="notification_zone"):
                    yield Static(id="notification_msg")
                    with Horizontal(id="notification_actions"):
                        yield Button("Accept", variant="success", id="btn_accept_req")
                        yield Button("Decline", variant="error", id="btn_decline_req")

        yield Footer()


    def establish_session(self, peer_name: str, peer_id: str) -> None:
        """this is called when a handshake succeeds to initialize the private chat panel."""
        
        switcher = self.query_one("#chat_switcher", ContentSwitcher)
        active_container = self.query_one("#connectedList", VerticalScroll) 
        
        safe_id = f"peer_{str(peer_id).replace('.', '').replace(':', '_').replace('(','').replace(')','').replace("'","").replace('"', '').replace(" ","").replace(",", "")}"
        
        new_pane = ConversationPane(peer_name=peer_name, id=safe_id)
        switcher.mount(new_pane)
        
        sidebar_btn = Button(f"{peer_name}", id=f"btn_{safe_id}")
        active_container.mount(sidebar_btn)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        engine = self.app.networkEngine
        
        if not button_id or not engine:
            return

        if button_id.startswith("btn_peer_"):
            target_pane_id = button_id.replace("btn_", "")
            self.query_one("#chat_switcher", ContentSwitcher).current = target_pane_id
            
        current_handshake = getattr(engine, "pending_handshake", None)

        
        if button_id == "btn_accept_req":
            if current_handshake:
                peer_name = current_handshake.get("name", "Unknown Node")
                peer_ip = current_handshake.get("ip", "")
                
                engine.handshake_approved = True
                engine.handshake_signal.set() 
                
                self.establish_session(peer_name, peer_ip)
            
            
            self.query_one("#notification_zone").remove_class("visible")
            self.has_active_popup = False

        
        elif button_id == "btn_decline_req":
            if current_handshake:
                engine.handshake_approved = False
                engine.handshake_signal.set()
            
            self.query_one("#notification_zone").remove_class("visible")
            self.has_active_popup = False

    def on_mount(self) -> None:
        self.set_interval(1.0, self.refresh_page)

    def refresh_page(self) -> None:
        """Queries the connectionManager cache and manages incoming handshakes safely."""
        if not self.app.networkEngine:
            return

        engine = self.app.networkEngine
        container = self.query_one("#peopleList", VerticalScroll)
        active_peers = engine.availability

        zone = self.query_one("#notification_zone", Vertical)
        
        current_handshake = getattr(engine, "pending_handshake", None)
        
        if current_handshake and not self.has_active_popup:
            msg = self.query_one("#notification_msg", Static)
            
            peer_name = current_handshake.get("name", "Unknown Node")
            peer_device = current_handshake.get("device", "Unknown Node")
            
            msg.update(f"[cyan]Inbound request from {peer_name} ({peer_device})[/cyan]")
            zone.add_class("visible")
            self.has_active_popup = True  # Lock the UI popup open

        
        existing_buttons = {btn.id for btn in container.query(Button)}
        current_peer_ids = set()

        for peer_id, profile in active_peers.items():
            del peer_id
            safe_id_str = profile.get("safe_id", "") if profile else ""
            if not safe_id_str:
                continue
                
            safe_btn_id = f"d{safe_id_str}"
            current_peer_ids.add(safe_btn_id)

            if safe_btn_id not in existing_buttons:
                button_label = f"{profile.get('peer_name', 'Unknown')} ({profile.get('device', 'Node')})"
                new_btn = Button(button_label, id=safe_btn_id)
                container.mount(new_btn)

        for btn in container.query(Button):
            if btn.id and btn.id.startswith("d") and btn.id not in current_peer_ids:
                btn.remove()


if __name__ == "__main__" and per==True:
    MainApp().run()