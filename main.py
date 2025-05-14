import flet as ft
import os
import json
from datetime import datetime

class Note:
    def __init__(self, title="", content="", created_at=None, updated_at=None):
        self.title = title
        self.content = content
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or self.created_at

    def to_dict(self):
        return {
            "title": self.title,
            "content": self.content,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            title=data.get("title", ""),
            content=data.get("content", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


class NoteManager:
    def __init__(self, storage_dir="notes"):
        os.makedirs(storage_dir, exist_ok=True)
        self.storage_dir = storage_dir
        self.index_path = os.path.join(self.storage_dir, "index.json")
        self.notes = {}
        self.load_notes()
        # Prevent immediate write during initialization
        self._initial_load_complete = True

    def load_notes(self):
        if not os.path.exists(self.index_path):
            # Don't save during initial load
            if hasattr(self, '_initial_load_complete') and self._initial_load_complete:
                self.save_notes()
            return

        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                raw_data = f.read().strip()
                if not raw_data:
                    print("Index file is empty. Initializing empty note list.")
                    return

                index_data = json.loads(raw_data)

                if not isinstance(index_data, dict):
                    print("Invalid format: expected a dictionary of notes.")
                    return

                for note_id, note_data in index_data.items():
                    if isinstance(note_data, dict):
                        self.notes[note_id] = Note.from_dict(note_data)
                    else:
                        print(f"Skipping malformed note: {note_id}")

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
        except Exception as e:
            print(f"Unexpected error while loading notes: {e}")

    def save_notes(self):
        # Skip initial save during app startup
        if not hasattr(self, '_initial_load_complete'):
            return
            
        index_data = {
            note_id: note.to_dict()
            for note_id, note in self.notes.items()
        }
        try:
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(index_data, f, indent=2)
        except Exception as e:
            print(f"Error saving notes: {e}")

    def add_note(self, note_id, note):
        self.notes[note_id] = note
        self.save_notes()

    def delete_note(self, note_id):
        if note_id in self.notes:
            del self.notes[note_id]
            self.save_notes()

    def update_note(self, note_id, title=None, content=None):
        if note_id in self.notes:
            note = self.notes[note_id]
            if title is not None:
                note.title = title
            if content is not None:
                note.content = content
            note.updated_at = datetime.now().isoformat()
            self.save_notes()

    def get_most_recent_note_id(self):
        if not self.notes:
            return None
        return max(self.notes, key=lambda nid: self.notes[nid].updated_at)


def main(page: ft.Page):
    # Configure the page
    page.title = "NoteMark"
    page.padding = 0
    page.spacing = 0
    page.window_bgcolor = ft.colors.TRANSPARENT
    page.bgcolor = "#1E1E1E"  # Dark background
    page.window_frameless = True
    
    # Make window frameless on desktop platforms
    if page.platform in ["windows", "macos", "linux"]:
        page.window_title_bar_hidden = True
        page.window_frameless = True
    
    # Initialize note manager
    note_manager = NoteManager()
    current_note_id = None
    
    # App state
    auto_save_timer = None
    is_loading_note = False  # Flag to prevent saving during load
    
    # App refs
    note_list_view = ft.Ref[ft.ListView]()
    note_editor = ft.Ref[ft.TextField]()
    markdown_view = ft.Ref[ft.Markdown]()
    title_text = ft.Ref[ft.Text]()
    preview_container = ft.Ref[ft.Container]()
    
    # CUSTOM COMPONENTS
    # Markdown style for dark theme with monospace font
    md_style_sheet = ft.MarkdownStyleSheet(
        # Base text style
        p_text_style=ft.TextStyle(
            color="#E0E0E0",  # Light grey for normal text
            size=16,
        ),
        
        # Headings with slate blue accents
        h1_text_style=ft.TextStyle(color="#8BE9FD", size=28, weight=ft.FontWeight.BOLD),
        h2_text_style=ft.TextStyle(color="#8BE9FD", size=24, weight=ft.FontWeight.BOLD),
        h3_text_style=ft.TextStyle(color="#8BE9FD", size=20, weight=ft.FontWeight.BOLD),
        h4_text_style=ft.TextStyle(color="#8BE9FD", size=18, weight=ft.FontWeight.BOLD),
        h5_text_style=ft.TextStyle(color="#8BE9FD", size=16, weight=ft.FontWeight.BOLD),
        h6_text_style=ft.TextStyle(color="#8BE9FD", size=14, weight=ft.FontWeight.BOLD),
        
        # Links with cyan
        a_text_style=ft.TextStyle(color="#50FA7B", decoration=ft.TextDecoration.UNDERLINE),
        
        # Emphasis styles
        em_text_style=ft.TextStyle(color="#FFB86C", italic=True),  # Orange italic
        strong_text_style=ft.TextStyle(color="#FF79C6", weight=ft.FontWeight.BOLD),  # Pink bold
        
        # Blockquotes
        blockquote_decoration=ft.BoxDecoration(
            border=ft.Border(
                left=ft.BorderSide(width=4, color="#BD93F9")  # Purple accent
            ),
        ),
        blockquote_padding=10,
        blockquote_text_style=ft.TextStyle(color="#F1FA8C", italic=True),  # Light yellow
        
        # Lists
        list_indent=24.0,
        list_bullet_text_style=ft.TextStyle(color="#FF79C6", size=16),
        
        # Horizontal rule
        horizontal_rule_decoration=ft.BoxDecoration(
            border=ft.Border(
                top=ft.BorderSide(width=1, color="#6272A4")  # Muted blue-purple
            )
        ),
        
        # Tables
        table_head_text_style=ft.TextStyle(
            color="#F8F8F2", 
            weight=ft.FontWeight.BOLD,
        ),
        table_body_text_style=ft.TextStyle(color="#F8F8F2"),
        table_cells_padding=8,
        table_cells_decoration=ft.BoxDecoration(
            border=ft.Border(
                top=ft.BorderSide(width=1, color="#6272A4"),
                left=ft.BorderSide(width=1, color="#6272A4"),
                bottom=ft.BorderSide(width=1, color="#6272A4"),
                right=ft.BorderSide(width=1, color="#6272A4"),
            )
        ),
        
        # Spacing
        block_spacing=16.0,
    )

    
    def minimize_window(e):
        if page.platform in [ft.PagePlatform.WINDOWS, ft.PagePlatform.MACOS, ft.PagePlatform.LINUX]:
            page.window_minimized = True
            page.update()
    
    def maximize_window(e):
        if page.platform in [ft.PagePlatform.WINDOWS, ft.PagePlatform.MACOS, ft.PagePlatform.LINUX]:
            page.window_maximized = not page.window_maximized
            page.update()
    
    def close_window(e):
        # Auto-save before closing
        if current_note_id and note_editor.current:
            save_current_note()
        page.window_close()
    
    def update_note_list():
        """Update the sidebar note list with the current notes"""
        if not note_list_view.current:
            return
            
        note_list_view.current.controls.clear()
        
        for note_id, note in sorted(note_manager.notes.items(), 
                                  key=lambda x: x[1].updated_at, 
                                  reverse=True):
            title_display = note.title or "Untitled"
            date_display = datetime.fromisoformat(note.updated_at).strftime("%d/%m/%Y, %H:%M")
            
            # Create a note item container that looks like the reference image
            note_item = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            title_display,
                            color="#FFFFFF" if note_id == current_note_id else "#BBBBBB",
                            size=14,
                            weight=ft.FontWeight.BOLD if note_id == current_note_id else None,
                            font_family="Menlo, Monaco, Consolas, monospace",
                        ),
                        ft.Text(
                            date_display,
                            size=12,
                            color="#888888",
                            font_family="Menlo, Monaco, Consolas, monospace",
                        ),
                    ],
                    spacing=2,
                    tight=True,
                ),
                width=200,
                bgcolor="#333333" if note_id == current_note_id else "#252525",
                border_radius=0,  # No rounded corners like in image
                ink=True,
                padding=10,
                margin=ft.margin.only(bottom=1),  # Small gap between items
                on_click=lambda e, nid=note_id: load_note(nid),
            )
            
            note_list_view.current.controls.append(note_item)
        
        page.update()
    
    def load_note(note_id):
        """Load a note into the editor"""
        nonlocal current_note_id, is_loading_note
        
        # Save current note before loading a new one - only if not initial load
        if current_note_id and not is_loading_note and note_editor.current and note_editor.current.value:
            save_current_note()
        
        is_loading_note = True  # Set flag to prevent auto-save during loading
        current_note_id = note_id
        
        if note_id in note_manager.notes:
            note = note_manager.notes[note_id]
            
            # Update title and content
            if title_text.current:
                title_text.current.value = note.title
            
            if note_editor.current:
                note_editor.current.value = note.content
            
            if markdown_view.current:
                markdown_view.current.value = note.content
                
            update_note_list()
            page.update()
        
        is_loading_note = False  # Reset flag after loading
    
    def create_new_note(e=None):
        """Create a new empty note"""
        nonlocal current_note_id
        
        # Save current note before creating a new one
        if current_note_id and note_editor.current and note_editor.current.value:
            save_current_note()
        
        # Generate a new unique ID
        note_id = f"note_{datetime.now().timestamp()}"
        
        # Create new note
        new_note = Note(title="Untitled", content="")
        note_manager.add_note(note_id, new_note)
        
        # Load the new note
        current_note_id = note_id
        
        if title_text.current:
            title_text.current.value = new_note.title
        
        if note_editor.current:
            note_editor.current.value = ""
            note_editor.current.focus()
        
        if markdown_view.current:
            markdown_view.current.value = ""
        
        update_note_list()
        page.update()
    
    def save_current_note():
        """Save the current note"""
        # Don't save if we're in the process of loading a note
        if not current_note_id or is_loading_note:
            return
            
        if not note_editor.current:
            return
            
        content = note_editor.current.value
        
        # Extract title from first line if it starts with # (heading)
        lines = content.strip().split('\n', 1)
        if lines and lines[0].startswith('#'):
            title = lines[0].lstrip('#').strip()
        else:
            # Use first line or "Untitled" if empty
            title = (lines[0][:30] if lines and lines[0].strip() else "Untitled")
        
        # Update the note
        note_manager.update_note(current_note_id, title=title, content=content)
        
        # Update title display
        if title_text.current:
            title_text.current.value = title
        
        # Update markdown preview
        if markdown_view.current:
            markdown_view.current.value = content
        
        update_note_list()
    
    def schedule_auto_save(e=None):
        """Schedule an auto-save after typing"""
        nonlocal auto_save_timer
        
        # Don't schedule auto-save if we're loading a note
        if is_loading_note:
            return
        
        # If a timer is running, cancel it
        if auto_save_timer:
            page.clear_timeout(auto_save_timer)
        
        # Set a new timer
        auto_save_timer = page.set_timeout(1000, save_current_note)
    
    def delete_current_note(e=None):
        """Delete the current note"""
        if not current_note_id:
            return
            
        # Delete the note
        note_manager.delete_note(current_note_id)
        
        # If there are other notes, load the most recent one
        if note_manager.notes:
            load_note(note_manager.get_most_recent_note_id())
        else:
            # Create a new note if all are deleted
            create_new_note()
    
    # UI COMPONENTS
    # Window controls (traffic light style)
    window_controls = ft.Row(
        [
            ft.Container(
                width=12, height=12,
                border_radius=6,
                bgcolor="#FF5F56",  # Red
                on_click=close_window,
                ink=False,
            ),
            ft.Container(
                width=12, height=12,
                border_radius=6,
                bgcolor="#FFBD2E",  # Yellow
                on_click=minimize_window, 
                ink=False,
            ),
            ft.Container(
                width=12, height=12,
                border_radius=6,
                bgcolor="#27C93F",  # Green
                on_click=maximize_window,
                ink=False,
            ),
        ],
        spacing=8,
        alignment=ft.MainAxisAlignment.START,
    )
    
    # Title bar area 
    title_bar = ft.Container(
        content=ft.Row(
            [
                window_controls,
                ft.Container(
                    content=ft.Text(
                        ref=title_text,
                        value="Welcome",
                        color="#FFFFFF",
                        size=14,
                        text_align=ft.TextAlign.CENTER,
                        font_family="Menlo, Monaco, Consolas, monospace",
                    ),
                    expand=True,
                    alignment=ft.alignment.center,
                ),
                # Empty container for symmetry
                ft.Container(width=60),
            ],
            spacing=0,
        ),
        padding=10,
        bgcolor="#252525",  # Darker than the editor area
    )
    
    # Note list sidebar
    sidebar = ft.Container(
        content=ft.ListView(
            ref=note_list_view,
            spacing=0,
            padding=0,
        ),
        width=200,
        bgcolor="#252525",
    )

    def open_link(e):
        page.launch_url(e.url)
    
    # Note editor and preview
    main_content = ft.Container(
        content=ft.Stack(
            [
                # Editor
                ft.TextField(
                    ref=note_editor,
                    multiline=True,
                    min_lines=20,
                    max_lines=None,  # Allow unlimited lines
                    cursor_color="#FFFFFF",
                    text_style=ft.TextStyle(
                        color="#E0E0E0",
                        size=14,
                        font_family="Menlo, Monaco, Consolas, monospace",
                    ),
                    border=ft.InputBorder.NONE,
                    content_padding=20,
                    bgcolor="transparent",
                    on_change=schedule_auto_save,
                ),
                
                # Markdown preview
                ft.Container(
                    ref=preview_container,
                    content=ft.Column(
                        [
                            ft.Markdown(
                                ref=markdown_view,
                                selectable=True,
                                code_theme=ft.MarkdownCodeTheme.ATOM_ONE_DARK,
                                md_style_sheet=md_style_sheet,
                                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                                expand=False,
                                on_tap_link=open_link
                            ),
                        ],
                        tight=True,
                        scroll=ft.ScrollMode.ADAPTIVE
                    ),
                    padding=20,
                    visible=False,  # Initially hidden
                ),
            ],
        ),
        expand=True,
        bgcolor="#1E1E1E",  # Main editor area background
    )
    
    # Action buttons in the sidebar
    sidebar_actions = ft.Container(
        content=ft.Row(
            [
                # New note button
                ft.IconButton(
                    icon=ft.icons.ADD if hasattr(ft, 'icons') else ft.Icons.ADD,
                    icon_color="#BBBBBB",
                    tooltip="New note",
                    on_click=create_new_note,
                ),
                
                # Delete note button
                ft.IconButton(
                    icon=ft.icons.DELETE if hasattr(ft, 'icons') else ft.Icons.DELETE,
                    tooltip="Delete note",
                    icon_color="#BBBBBB",
                    on_click=delete_current_note,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        bgcolor="#252525",
        padding=5,
    )
    
    
    def toggle_preview():
        """Toggle between edit and preview modes"""
        if preview_container.current and note_editor.current:
            # Update content before switching
            save_current_note()
            
            # Toggle visibility
            preview_container.current.visible = not preview_container.current.visible
            note_editor.current.visible = not note_editor.current.visible
            
            page.update()
    
    # HELPER FUNCTIONS
    def create_welcome_note():
        """Create a welcome note with instructions"""
        welcome_md = """# Welcome to NoteDow 👋

NoteDown is a simple note-taking app that uses Markdown syntax to format your notes.

You can create your first note by clicking on the top-left icon on the sidebar, or delete one by clicking on top right icon.

Following there's a quick overview of the currently supported Markdown syntax.

## Text formatting

This is a **bold** text.
This is an *italic* text.

## Headings

Here are all the heading formats currently supported by NoteMark:

# Heading 1
## Heading 2 
### Heading 3
#### Heading 4

## Lists

- Item 1
- Item 2
- Item 3

1. First item
2. Second item
3. Third item

## Links and Images

[Visit GitHub](https://github.com)

## Code Blocks

```python
def hello_world():
    print("Hello, NoteDown!")
```

## Blockquotes

> This is a blockquote.
> It can span multiple lines.

## Horizontal Rule

---

Enjoy using NoteDown!
"""
        # Create a sample note with numeric names
        for i in range(1, 8):
            note_id = f"note{i}"
            title = f"Note{i}" if i > 1 else "Welcome"
            content = welcome_md if i == 1 else f"# Note {i}\nThis is a test note {i}."
            
            created = datetime.now().isoformat()
            
            # Make them appear to be created at slightly different times
            # for proper ordering in the sidebar
            note = Note(
                title=title,
                content=content,
                created_at=created,
                updated_at=created
            )
            note_manager.add_note(note_id, note)
        
        # Return the ID of the welcome note
        return "note1"
    
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.VISIBILITY,
        on_click= lambda _: toggle_preview()
    )
    
    # Create layout
    page.add(
        ft.Column(
            [
                ft.WindowDragArea(
                    title_bar
                ),  # Custom title bar with traffic light controls
                ft.Row(
                    [
                        ft.Column(
                            [
                                sidebar_actions,  # New and delete buttons
                                sidebar,  # Note list
                            ],
                            spacing=0,
                            alignment=ft.alignment.top_left
                        ),
                        ft.Column(
                            [
                                main_content,  # Editor/preview area
                            ],
                            spacing=0,
                            expand=True,
                            tight=True,
                        ),
                    ],
                    spacing=0,
                    expand=True,
                    tight=True,
                ),
            ],
            spacing=0,
            expand=True,
            tight=True,
        ),
    )
    
    # Initialize UI
    if not note_manager.notes:
        # Create welcome notes if no notes exist
        welcome_id = create_welcome_note()
        current_note_id = welcome_id
    else:
        # Load most recent note
        current_note_id = note_manager.get_most_recent_note_id()
    
    # Load initial note
    load_note(current_note_id)
    
    page.update()


if __name__ == "__main__":
    ft.app(target=main)  # Use WINDOW view for desktop apps
