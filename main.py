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
        
        chat_screen = self.get_screen("chat")
        self.networkEngine.on_session_established = chat_screen.handle_session_established
        self.networkEngine.on_session_closed = chat_screen.handle_session_closed
        self.networkEngine.on_message_received = chat_screen.handle_message_received
        
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
    
    def __init__(self, peer_name: str, peer_ip: str, peer_port: int, **kwargs):
        super().__init__(**kwargs)
        self.peer_name = peer_name
        self.peer_ip = peer_ip
        self.peer_port = peer_port

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
        
        safe_id = f"peer_{str(peer_id).replace('.', '').replace(':', '_')}"
        
        # Check if already established
        try:
            self.query_one(f"#{safe_id}", ConversationPane)
            return
        except Exception:
            pass
            
        if ":" in peer_id:
            peer_ip, peer_port_str = peer_id.split(":")
            peer_port = int(peer_port_str)
        else:
            peer_ip = peer_id
            peer_port = 0
            
        new_pane = ConversationPane(peer_name=peer_name, peer_ip=peer_ip, peer_port=peer_port, id=safe_id)
        switcher.mount(new_pane)
        
        sidebar_btn = Button(f"{peer_name}", id=f"btn_{safe_id}")
        active_container.mount(sidebar_btn)
        
        # Automatically switch to the new session
        switcher.current = safe_id

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        engine = self.app.networkEngine
        
        if not button_id or not engine:
            return

        if button_id.startswith("btn_peer_"):
            target_pane_id = button_id.replace("btn_", "")
            self.query_one("#chat_switcher", ContentSwitcher).current = target_pane_id
            
        elif button_id.startswith("avail_"):
            # Clicked on an available peer, initiate connection
            target_peer = None
            for p_id, profile in engine.availability.items():
                if f"avail_{profile.get('safe_id')}" == button_id:
                    target_peer = (p_id, profile)
                    break
            if target_peer:
                peer_id, profile = target_peer
                peer_ip, peer_port = peer_id
                peer_name = profile.get("peer_name", "Unknown")
                logger.info(f"Initiating connection handshake to {peer_name} ({peer_ip}:{peer_port})")
                asyncio.create_task(engine._initiate_tcp(peer_ip, peer_port, {}))
            
        current_handshake = getattr(engine, "pending_handshake", None)

        if button_id == "btn_accept_req":
            if current_handshake:
                peer_name = current_handshake.get("name", "Unknown Node")
                peer_ip = current_handshake.get("ip", "")
                peer_port = current_handshake.get("port")
                
                engine.handshake_approved = True
                engine.handshake_signal.set() 
                
                peer_id_str = f"{peer_ip}:{peer_port}" if peer_port else peer_ip
                self.establish_session(peer_name, peer_id_str)
            
            self.query_one("#notification_zone").remove_class("visible")
            self.has_active_popup = False

        elif button_id == "btn_decline_req":
            if current_handshake:
                engine.handshake_approved = False
                engine.handshake_signal.set()
            
            self.query_one("#notification_zone").remove_class("visible")
            self.has_active_popup = False

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        input_widget = event.input
        input_id = input_widget.id
        
        if input_id and input_id.startswith("input_peer_"):
            message = event.value.strip()
            if not message:
                return
                
            input_widget.value = ""
            
            # Find the ancestor ConversationPane
            pane = input_widget.parent
            while pane and not isinstance(pane, ConversationPane):
                pane = pane.parent
                
            if pane and self.app.networkEngine:
                # Send message asynchronously
                success = await self.app.networkEngine.send_message(pane.peer_ip, pane.peer_port, message)
                
                # Write to local UI log
                log_widget = pane.query_one(f"#log_{pane.id}", RichLog)
                if success:
                    log_widget.write(f"[bold green]You[/]: {message}")
                else:
                    log_widget.write(f"[bold red]System: Failed to send message to {pane.peer_name}[/]")

    def handle_session_established(self, peer_ip: str, peer_port: int, peer_name: str) -> None:
        """Triggered from backend when a connection establishes."""
        peer_id = f"{peer_ip}:{peer_port}"
        self.establish_session(peer_name, peer_id)

    def handle_session_closed(self, peer_ip: str, peer_port: int) -> None:
        """Triggered from backend when a connection is closed."""
        peer_id = f"{peer_ip}:{peer_port}"
        safe_id = f"peer_{str(peer_id).replace('.', '').replace(':', '_')}"
        
        # Remove button
        try:
            btn = self.query_one(f"#btn_{safe_id}")
            btn.remove()
        except Exception:
            pass
            
        # Remove pane
        try:
            pane = self.query_one(f"#{safe_id}")
            switcher = self.query_one("#chat_switcher", ContentSwitcher)
            if switcher.current == safe_id:
                switcher.current = "empty_view"
            pane.remove()
        except Exception:
            pass

    def handle_message_received(self, peer_ip: str, peer_port: int, text: str) -> None:
        """Triggered from backend when a message is decrypted."""
        peer_id = f"{peer_ip}:{peer_port}"
        safe_id = f"peer_{str(peer_id).replace('.', '').replace(':', '_')}"
        
        try:
            log_widget = self.query_one(f"#log_{safe_id}", RichLog)
            peer_name = "Unknown"
            if self.app.networkEngine:
                session = self.app.networkEngine.active_sessions.get((peer_ip, peer_port))
                if session:
                    peer_name = session.get("peer_name", "Unknown")
            
            log_widget.write(f"[bold cyan]{peer_name}[/]: {text}")
        except Exception as e:
            logger.exception(f"Error handling message received: {e}")

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
                
            safe_btn_id = f"avail_{safe_id_str}"
            current_peer_ids.add(safe_btn_id)

            if safe_btn_id not in existing_buttons:
                button_label = f"{profile.get('peer_name', 'Unknown')} ({profile.get('device', 'Node')})"
                new_btn = Button(button_label, id=safe_btn_id)
                container.mount(new_btn)

        for btn in container.query(Button):
            if btn.id and btn.id.startswith("avail_") and btn.id not in current_peer_ids:
                btn.remove()


if __name__ == "__main__" and per==True:
    MainApp().run()