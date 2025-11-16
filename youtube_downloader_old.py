import os
import sys
import subprocess
import re
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QCheckBox,
    QPushButton,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QFileDialog,
    QSizePolicy,  # Keep for potential future use, but not strictly needed now
    QFrame,  # Added for separator line
    QComboBox,  # Add QComboBox
    QRadioButton,  # Add QRadioButton
    QListView,  # Add QListView
    QMenu,  # Import QMenu
)
from PyQt6.QtGui import (
    QIcon,
    QAction,
)  # Import QAction if needed for custom actions, though standard ones exist
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from downloader import YTVideoDownloader


# --- Format Fetch Thread --- (NEW)
class FormatFetchThread(QThread):
    formats_fetched = pyqtSignal(dict)
    fetch_error = pyqtSignal(str)

    def __init__(self, url, browsers=None):
        super().__init__()
        self.url = url
        self.browsers = browsers if browsers else []

    def run(self):
        temp_downloader = YTVideoDownloader(use_rich=False, browsers=self.browsers)
        result = temp_downloader.get_formats(self.url)
        if result["status"]:
            self.formats_fetched.emit(result)
        else:
            self.fetch_error.emit(
                result.get("message", "Unknown error fetching formats.")
            )


# --- End Format Fetch Thread ---


# --- Download Thread --- (Modified)
class DownloadThread(QThread):
    progress_update = pyqtSignal(dict)
    finished = pyqtSignal(dict)

    # Add format_string parameter
    def __init__(self, url, browsers=None, download_dir=None, format_string=None):
        super().__init__()
        self.url = url
        self.browsers = browsers if browsers else []
        self.download_dir = download_dir
        self.format_string = format_string  # Store format string

    def run(self):
        def gui_hook(d):
            title = "N/A"
            if d.get("info_dict") and d["info_dict"].get("title"):
                title = d["info_dict"]["title"]
            elif d.get("filename"):
                base = os.path.basename(d["filename"])
                title = os.path.splitext(base)[0]
            progress_data = {
                "percent": 0,
                "speed": 0,
                "downloaded": 0,
                "total": 0,
                "status": d.get("status", "unknown"),
                "title": title,
            }
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                speed = d.get("speed")
                if total and downloaded is not None:
                    progress_data["percent"] = int((downloaded / total) * 100)
                    progress_data["total"] = total
                    progress_data["downloaded"] = downloaded
                if speed is not None:
                    progress_data["speed"] = speed
                self.progress_update.emit(progress_data)
            elif d.get("status") == "finished":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes")
                if downloaded is not None:
                    progress_data["total"] = downloaded
                    progress_data["downloaded"] = downloaded
                elif total is not None:
                    progress_data["total"] = total
                    progress_data["downloaded"] = total
                progress_data["percent"] = 100
                progress_data["speed"] = 0
                progress_data["title"] = title
                self.progress_update.emit(progress_data)

        downloader = YTVideoDownloader(
            progress_hook=gui_hook,
            use_rich=False,
            browsers=self.browsers,
            download_dir=self.download_dir,
        )
        # Pass format_string to download_video method
        result = downloader.download_video(self.url, format_string=self.format_string)
        self.finished.emit(result)


# --- End Download Thread ---


class YouTubeDownloaderApp(QWidget):
    def __init__(self):
        super().__init__()

        # Determine base path for defaults
        if getattr(sys, "frozen", False):
            self.base_path = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))

        # Download directory attribute
        self.current_download_dir = os.path.join(self.base_path, "downloaded_videos")

        # Resource path setup
        if hasattr(sys, "_MEIPASS"):
            self.root_path = sys._MEIPASS
        else:
            self.root_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        os.chdir(self.root_path)

        self.setWindowTitle("Youtube Downloader")
        # Adjust height for the new settings layout
        self.setFixedSize(600, 670)

        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint
        )

        icon_path = os.path.join(self.root_path, "yt.png")
        self.setWindowIcon(QIcon(icon_path))

        self.download_thread = None
        self.fetched_formats = []
        self.current_video_title = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # --- Enhanced Intro Panel ---
        intro_label = QLabel()
        intro_label.setTextFormat(Qt.TextFormat.RichText)
        intro_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intro_label.setStyleSheet(
            """
            QLabel#IntroLabel {
                border: 1px solid #8f9dc2;
                border-radius: 15px;
                color: #333;
                font-family: Arial, sans-serif;
                padding: 10px;
            }
        """
        )
        intro_label.setObjectName("IntroLabel")
        intro_label.setText(
            """
            <div style="text-align: center;">
                <!-- New inner div for the border and background -->
                <div style="border: 1px solid #80deea; border-radius: 8px;  padding: 15px; display: inline-block;">
                    <div style="font-size: 18pt; font-weight: 600; color: #004d40;">
                    YouTube Downloader
                </div>
                    <div style="font-size: 10pt; color: #6e4414; margin-top: 5px;">
                        Developed by Sujit - 
                        <a href="https://github.com/SSujitX"
                           style="color: #2d8bff; text-decoration: none; font-weight: 500;">
                            GitHub
                        </a>
                    </div>
                    <div style="font-size: 10pt; color: #00796b; margin-top: 8px;">
                         Download youtube video or audio with best quality.
                </div>
                </div>
            </div>
            """
        )
        intro_label.setOpenExternalLinks(True)
        # --- End Enhanced Intro Panel ---

        # --- URL Section with Fetch Button --- (MODIFIED)
        url_layout = QHBoxLayout()
        self.label = QLabel("YouTube URL:")  # Shortened Label
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.setMinimumHeight(35)
        # --- Custom Context Menu for URL Input --- (NEW)
        self.url_input.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.url_input.customContextMenuRequested.connect(
            self.show_url_input_context_menu
        )
        # --- End Custom Context Menu Setup ---
        self.fetch_formats_button = QPushButton("Fetch Formats")  # NEW Button
        self.fetch_formats_button.clicked.connect(self.handle_fetch_formats)
        self.fetch_formats_button.setFixedHeight(35)
        self.fetch_formats_button.setObjectName("FetchFormatsButton")
        url_layout.addWidget(self.label)
        url_layout.addWidget(self.url_input, 1)
        url_layout.addWidget(self.fetch_formats_button)
        # --- End URL Section ---

        # --- Settings Group (Vertical Stack) ---
        settings_group = QGroupBox("Options")  # Rename again
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(10)

        # -- Download Type (Radio Buttons) -- (NEW)
        type_group_label = QLabel("<b>Download Type:</b>")
        type_layout = QHBoxLayout()
        self.video_radio = QRadioButton("Download Video (includes best audio)")
        self.audio_radio = QRadioButton("Download Audio Only")
        self.video_radio.setChecked(True)  # Default to video
        self.video_radio.toggled.connect(self.update_download_options)
        # audio_radio toggled also calls update_download_options
        type_layout.addWidget(self.video_radio)
        type_layout.addWidget(self.audio_radio)
        type_layout.addStretch()

        # -- Format Selection (Contextual) -- (MODIFIED)
        format_layout = QHBoxLayout()
        self.video_format_label = QLabel("Video Format:")  # Label for video combo
        self.video_format_combo = QComboBox()
        self.video_format_combo.addItem("Best Available", "bv")

        self.audio_format_label = QLabel("Audio Format:")  # Label for audio combo
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItem("Best Available", "ba")

        format_layout.addWidget(self.video_format_label)
        format_layout.addWidget(self.video_format_combo, 2)
        format_layout.addWidget(self.audio_format_label)
        format_layout.addWidget(self.audio_format_combo, 2)
        # Initially hide audio controls
        self.audio_format_label.setVisible(False)
        self.audio_format_combo.setVisible(False)
        # --- End Format Selection --

        # -- Cookie Section -- (MODIFIED Layout)
        cookie_group_label = QLabel("<b>Cookies:</b>")
        cookie_explanation_label = QLabel(
            "Use browser cookies for age-restricted or private videos."
        )
        cookie_explanation_label.setObjectName("ExplanationLabel")
        cookie_explanation_label.setWordWrap(True)

        # Main row for cookies
        cookie_main_layout = QHBoxLayout()
        self.use_cookies_checkbox = QCheckBox("Use Browser Cookies")
        self.use_cookies_checkbox.stateChanged.connect(self.toggle_browser_checkboxes)
        self.firefox_checkbox = QCheckBox("Firefox")
        self.chrome_checkbox = QCheckBox("Chrome")
        self.firefox_checkbox.setEnabled(False)
        self.chrome_checkbox.setEnabled(False)

        cookie_main_layout.addWidget(self.use_cookies_checkbox)
        cookie_main_layout.addStretch()  # Push browser checkboxes to the right
        cookie_main_layout.addWidget(self.firefox_checkbox)
        cookie_main_layout.addWidget(self.chrome_checkbox)
        # --- End Cookie Section --

        # -- Folder Section --
        folder_group_label = QLabel("<b>Save Location:</b>")
        folder_explanation_label = QLabel("Choose where downloaded videos are saved.")
        folder_explanation_label.setObjectName("ExplanationLabel")
        folder_explanation_label.setWordWrap(True)
        folder_row_layout = QHBoxLayout()
        self.folder_path_label = QLabel(f"{self.current_download_dir}")
        # self.folder_path_label.setWordWrap(False) # Prevent explicit wrapping
        self.folder_path_label.setObjectName("FolderPathLabel")
        # Use elide mode if needed, though small font might be enough
        # self.folder_path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # fm = self.folder_path_label.fontMetrics()
        # elided_text = fm.elidedText(self.current_download_dir, Qt.TextElideMode.ElideRight, self.folder_path_label.width() - 10) # Adjust width as needed
        # self.folder_path_label.setText(elided_text) # This needs to be updated when path changes too

        self.change_folder_button = QPushButton("Change Folder")
        self.change_folder_button.clicked.connect(self.change_download_folder)
        self.change_folder_button.setFixedHeight(28)
        self.change_folder_button.setObjectName("change_folder_button")
        folder_row_layout.addWidget(self.folder_path_label, 1)
        folder_row_layout.addWidget(self.change_folder_button)
        # --- End Folder Section ---

        # Add sections to settings layout
        settings_layout.addWidget(type_group_label)
        settings_layout.addLayout(type_layout)
        settings_layout.addLayout(format_layout)
        settings_layout.addWidget(cookie_group_label)
        settings_layout.addWidget(cookie_explanation_label)
        settings_layout.addLayout(cookie_main_layout)
        settings_layout.addWidget(folder_group_label)
        settings_layout.addWidget(folder_explanation_label)
        settings_layout.addLayout(folder_row_layout)
        settings_group.setLayout(settings_layout)
        # --- End Settings Group ---

        # Apply custom scrollbar style programmatically
        self.style_combobox_scrollbar(self.video_format_combo)
        self.style_combobox_scrollbar(self.audio_format_combo)

        # --- Title Label --- (Add before progress bar)
        self.title_label = QLabel(" ")
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setFixedHeight(25)
        self.progress.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #bfbfbf;
                border-radius: 10px; /* Match intro radius */
                background-color: #e0e0e0; /* Lighter gray background */
                text-align: center;
                font-weight: bold;
                color: #333;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    spread:pad,
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #007acc, /* Keep gradient for progress */
                    stop:1 #4db8ff
                );
                border-radius: 10px; /* Match radius */
            }
        """
        )

        # --- Labels for Speed and Size ---
        progress_details_layout = QHBoxLayout()
        self.size_label = QLabel("Size: N/A")
        self.speed_label = QLabel("Speed: N/A")
        self.size_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        progress_details_layout.addWidget(self.size_label)
        progress_details_layout.addWidget(self.speed_label)
        # --- End Labels ---

        # --- Buttons Layout ---
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("Download Now")
        self.download_button.clicked.connect(self.handle_download)
        self.download_button.setFixedHeight(35)  # Set fixed height

        self.open_folder_button = QPushButton("Open Download Folder")
        self.open_folder_button.clicked.connect(self.open_folder)
        self.open_folder_button.setFixedHeight(35)  # Set fixed height

        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.open_folder_button)
        # --- End Buttons Layout ---

        # --- Label for Last Download ---
        self.last_download_label = QLabel("Last download: None")
        self.last_download_label.setObjectName("LastDownloadLabel")
        self.last_download_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.last_download_label.setStyleSheet(
            "font-size: 9pt; color: #6c757d; margin-top: 5px; padding-bottom: 5px;"
        )  # Add styling and bottom padding
        self.last_download_label.setWordWrap(True)  # Allow wrapping if filename is long
        # --- End Label ---

        layout.addWidget(intro_label)
        layout.addLayout(url_layout)  # Use the url layout here
        layout.addWidget(settings_group)
        layout.addWidget(self.title_label)
        layout.addWidget(self.progress)
        layout.addLayout(progress_details_layout)
        layout.addLayout(button_layout)
        layout.addWidget(self.last_download_label)

        self.setLayout(layout)
        self.setStyleSheet(
            """
            QWidget { font-size: 10pt; background-color: #f8f9fa; }
            QPushButton { background-color: #007bff; color: white; padding: 8px 12px; border-radius: 6px; font-size: 10pt; font-weight: 500; border: none; }
            QPushButton#change_folder_button { background-color: #6c757d; padding: 5px 10px; font-size: 9pt; } /* Changed color to gray */
            QPushButton#change_folder_button:hover { background-color: #5a6268; } /* Darker gray on hover */
            QPushButton#FetchFormatsButton { padding: 6px 10px; font-size: 9pt; margin-left: 5px; }
            QPushButton:hover { background-color: #0056b3; } /* Default hover, excluding gray button */
            QPushButton:disabled { background-color: #ced4da; color: #6c757d; }
            QLineEdit { padding: 8px; border-radius: 4px; border: 1px solid #ced4da; background-color: #ffffff; }
            QGroupBox { font-weight: bold; margin-top: 12px; margin-bottom: 8px; border: 1px solid #ced4da; border-radius: 6px; padding: 10px 8px 8px 8px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px 0 5px; margin-left: 10px; background-color: #f8f9fa; color: #495057; }
            QCheckBox, QRadioButton { margin-top: 4px; margin-bottom: 4px; margin-left: 5px; font-family: Arial, sans-serif; }
            
            /* QComboBox Base Style */
            QComboBox { padding: 3px; border-radius: 4px; border: 1px solid #ced4da; background-color: #ffffff; min-height: 20px; }
            
            /* Dropdown Button Style */
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px; border-left-width: 1px; border-left-color: #ced4da;
                border-left-style: solid; border-top-right-radius: 3px; border-bottom-right-radius: 3px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop: 1 #e9ecef);
            }
            
            /* NOTE: Scrollbar styling is now applied via python code */
            
            /* Other Labels */
            QLabel#SizeLabel, QLabel#SpeedLabel { font-size: 9pt; color: #495057; padding: 2px 5px 5px 5px; }
            QLabel#FolderPathLabel { font-size: 7pt; color: #343a40; margin-bottom: 1px; margin-top: 1px; } /* Smaller font, reduced margins */
            QLabel#ExplanationLabel { font-size: 8pt; color: #6c757d; margin-bottom: 4px; margin-top: 4px; font-style: italic; }
            QLabel#TitleLabel { font-size: 10pt; color: #212529; font-weight: 500; margin-top: 8px; margin-bottom: 2px; }
            QGroupBox QLabel { font-weight: normal; }
            QGroupBox QLabel b { font-weight: bold; }

            /* --- Custom Context Menu Styling --- (NEW) */
            QMenu {
                background-color: #f8f9fa; /* Light background to match window */
                border: 1px solid #ced4da; /* Similar border to GroupBox */
                padding: 5px; /* Padding around items */
                border-radius: 4px;
            }
            QMenu::item {
                padding: 5px 20px 5px 20px; /* Padding for each item */
                color: #212529; /* Dark text color */
                border-radius: 3px; /* Slight rounding for hover */
            }
            QMenu::item:selected {
                background-color: #e0e7ff; /* Light blue background on hover/selection */
                color: #004085; /* Darker blue text on hover */
            }
            QMenu::item:disabled {
                color: #adb5bd; /* Gray out disabled items */
                background-color: transparent;
            }
            QMenu::separator {
                height: 1px;
                background: #ced4da; /* Separator line color */
                margin-left: 10px;
                margin-right: 10px;
                margin-top: 3px;
                margin-bottom: 3px;
            }
            /* --- End Custom Context Menu Styling --- */
            """
        )
        # Set object names for the new labels for potential styling
        self.size_label.setObjectName("SizeLabel")
        self.speed_label.setObjectName("SpeedLabel")
        # Set initial state for audio format combo
        self.video_format_combo.setCurrentIndex(0)  # Index 0 = Video
        self.audio_format_combo.setCurrentIndex(0)  # Index 0 = Audio

    # --- Show Custom Context Menu for URL Input --- (NEW)
    def show_url_input_context_menu(self, position):
        menu = QMenu()

        # Standard actions from QLineEdit
        undo_action = menu.addAction("Undo")
        undo_action.triggered.connect(self.url_input.undo)
        undo_action.setEnabled(self.url_input.isUndoAvailable())

        redo_action = menu.addAction("Redo")
        redo_action.triggered.connect(self.url_input.redo)
        redo_action.setEnabled(self.url_input.isRedoAvailable())

        menu.addSeparator()

        cut_action = menu.addAction("Cut")
        cut_action.triggered.connect(self.url_input.cut)
        cut_action.setEnabled(self.url_input.hasSelectedText())

        copy_action = menu.addAction("Copy")
        copy_action.triggered.connect(self.url_input.copy)
        copy_action.setEnabled(self.url_input.hasSelectedText())

        paste_action = menu.addAction("Paste")
        paste_action.triggered.connect(self.url_input.paste)
        paste_action.setEnabled(bool(QApplication.clipboard().text()))

        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(
            self.url_input.del_
        )  # Note: 'del' is a keyword, method is 'del_'
        delete_action.setEnabled(self.url_input.hasSelectedText())

        menu.addSeparator()

        select_all_action = menu.addAction("Select All")
        select_all_action.triggered.connect(self.url_input.selectAll)
        select_all_action.setEnabled(
            bool(self.url_input.text())
        )  # Enable if there is text

        # Execute the menu - requires mapping the position
        menu.exec(self.url_input.mapToGlobal(position))

    # --- End Custom Context Menu ---

    # --- Helper to Style ComboBox Scrollbars --- (NEW)
    def style_combobox_scrollbar(self, combobox):
        scrollbar_style = """
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0; /* Background of the scrollbar track */
                width: 8px;       /* Width of the vertical scroll bar */
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #bdbdbd; /* Color of the scrollbar handle */
                border-radius: 4px;
                min-height: 20px;   /* Minimum handle height */
            }
            QScrollBar::handle:vertical:hover {
                background: #e7816b; /* Color on hover */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;   /* Hide the arrows */
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;   /* Hide the page area background */
            }
        """
        view = combobox.view()
        if view:  # Ensure view exists
            scrollbar = view.verticalScrollBar()
            if scrollbar:
                scrollbar.setStyleSheet(scrollbar_style)

    # --- End Helper ---

    # --- update_download_options --- (Unchanged)
    def update_download_options(self):
        is_video = self.video_radio.isChecked()
        self.video_format_label.setVisible(is_video)
        self.video_format_combo.setVisible(is_video)
        self.audio_format_label.setVisible(not is_video)
        self.audio_format_combo.setVisible(not is_video)
        if is_video:
            self.audio_format_combo.setCurrentIndex(0)  # Reset audio to Best Available
        else:
            self.video_format_combo.setCurrentIndex(0)  # Reset video to Best Available

    # --- Format Fetching Slots --- (Modified to populate both combos)
    def handle_fetch_formats(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(
                self, "Input Error", "Please enter a YouTube URL first."
            )
            return
        self.fetch_formats_button.setEnabled(False)
        self.fetch_formats_button.setText("Fetching...")
        self.title_label.setText("Fetching available formats...")
        # Clear existing formats (keep defaults)
        self.video_format_combo.clear()
        self.audio_format_combo.clear()
        self.video_format_combo.addItem("Best Available", "bv")
        self.audio_format_combo.addItem("Best Available", "ba")
        self.fetched_formats = []
        selected_browsers = []
        if self.use_cookies_checkbox.isChecked():
            if self.firefox_checkbox.isChecked():
                selected_browsers.append("firefox")
            if self.chrome_checkbox.isChecked():
                selected_browsers.append("chrome")
        self.format_fetch_thread = FormatFetchThread(url, browsers=selected_browsers)
        self.format_fetch_thread.formats_fetched.connect(self.on_formats_fetched)
        self.format_fetch_thread.fetch_error.connect(self.on_fetch_error)
        self.format_fetch_thread.start()

    def on_formats_fetched(self, result):
        self.fetch_formats_button.setEnabled(True)
        self.fetch_formats_button.setText("Fetch Formats")
        self.title_label.setText(" ")
        self.fetched_formats = result.get("formats", [])
        info = result.get("info", {})
        video_title = info.get("title", "Video")
        self.current_video_title = video_title
        self.title_label.setText(
            f"Formats for: {video_title[:50]}{'...' if len(video_title) > 50 else ''}"
        )
        if not self.fetched_formats:
            QMessageBox.warning(
                self, "No Formats", "Could not find any download formats for this URL."
            )
            return

        # Clear existing formats (keep defaults)
        self.video_format_combo.clear()
        self.audio_format_combo.clear()
        self.video_format_combo.addItem("Best Available", "bv")
        self.audio_format_combo.addItem("Best Available", "ba")

        video_items = []
        audio_items = []
        preferred_vcodecs = ("avc", "vp9", "av01")
        preferred_acodecs = ("mp4a", "opus")
        min_height = 480
        for f in self.fetched_formats:
            format_id = f.get("format_id")
            if not format_id:
                continue
            description = self.create_format_description(f)
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            height = f.get("height")
            abr = f.get("abr", 0)
            fps = f.get("fps", 0)
            if vcodec != "none" and acodec == "none":
                if (
                    height
                    and height >= min_height
                    and any(vcodec.startswith(p) for p in preferred_vcodecs)
                ):
                    video_items.append((height, fps, format_id, description))
            elif acodec != "none" and vcodec == "none":
                if any(acodec.startswith(p) for p in preferred_acodecs):
                    audio_items.append((abr, format_id, description))
        video_items.sort(key=lambda x: (x[0] or 0, x[1] or 0), reverse=True)
        audio_items.sort(key=lambda x: (x[0] or 0), reverse=True)
        # Populate both combo boxes
        for height, fps, fmt_id, desc in video_items:
            self.video_format_combo.addItem(desc, fmt_id)
        for abr, fmt_id, desc in audio_items:
            self.audio_format_combo.addItem(desc, fmt_id)
        QMessageBox.information(
            self,
            "Formats Fetched",
            f"Found {len(video_items)} video and {len(audio_items)} filtered audio/video formats.",
        )

    def on_fetch_error(self, message):
        self.fetch_formats_button.setEnabled(True)
        self.fetch_formats_button.setText("Fetch Formats")
        self.title_label.setText(" ")
        QMessageBox.critical(self, "Fetch Error", message)

    # --- change_download_folder --- (Unchanged from previous correct state)
    def change_download_folder(self):
        new_folder = QFileDialog.getExistingDirectory(
            self, "Select Download Folder", self.current_download_dir
        )
        if new_folder:
            self.current_download_dir = new_folder
            self.folder_path_label.setText(f"{self.current_download_dir}")

    # --- update_progress_display --- (Modified)
    def update_progress_display(self, progress_data):
        percent = progress_data.get("percent", 0)
        speed = progress_data.get("speed")
        downloaded = progress_data.get("downloaded")
        total = progress_data.get("total")
        title = progress_data.get("title", "N/A")
        # Update Title Label only if downloading and different, don't overwrite "Formats for:" status
        current_title_text = self.title_label.text()
        if progress_data.get("status") == "downloading" and title and title != "N/A":
            if (
                not current_title_text.startswith("Formats for:")
                and current_title_text != title
            ):
                self.title_label.setText(f"{title}")
        elif progress_data.get(
            "status"
        ) != "downloading" and current_title_text.startswith("Formats for:"):
            pass  # Keep format status until download starts/ends or fetch again
        elif progress_data.get("status") != "downloading":
            if current_title_text != " ":
                self.title_label.setText(" ")  # Clear only if not already cleared

        self.progress.setValue(percent)
        # Update speed/size labels (logic unchanged)
        if speed is not None and speed > 0:
            speed_str = self.format_bytes(speed) + "/s"
        elif progress_data.get("status") == "downloading":
            speed_str = "Starting..."
        else:
            speed_str = "N/A"
        self.speed_label.setText(f"Speed: {speed_str}")
        if downloaded is not None and total is not None and total > 0:
            size_str = f"{self.format_bytes(downloaded)} / {self.format_bytes(total)}"
        else:
            size_str = "N/A"
        self.size_label.setText(f"Size: {size_str}")

    # --- toggle_browser_checkboxes --- (Modified - no longer needs toggle_format_combos call)
    def toggle_browser_checkboxes(self, state):
        enable = state == Qt.CheckState.Checked.value
        self.firefox_checkbox.setEnabled(enable)
        self.chrome_checkbox.setEnabled(enable)
        if not enable:
            self.firefox_checkbox.setChecked(False)
            self.chrome_checkbox.setChecked(False)

    # --- handle_download (MODIFIED - Uses Radio Buttons) ---
    def handle_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Input Error", "Please enter a YouTube URL.")
            return

        # --- Get Selected Download Type and Format ---
        format_string = None  # Default

        if self.video_radio.isChecked():  # Download Video selected
            vid = self.video_format_combo.currentData()  # Get video format (bv or ID)
            if vid == "bv":  # Best Available video selected
                format_string = None  # Let yt-dlp choose best video + best audio
            else:  # Specific video format selected
                format_string = f"{vid}+ba"  # Combine specific video + best audio

        elif self.audio_radio.isChecked():  # Download Audio selected
            aid = self.audio_format_combo.currentData()  # Get audio format (ba or ID)
            format_string = aid  # Use the selected audio format ID (or 'ba')

        else:  # Should not happen with radio buttons, but good practice
            QMessageBox.warning(
                self, "Error", "Please select a download type (Video or Audio)."
            )
            return
        # --- End Format Selection ---

        selected_browsers = []
        if self.use_cookies_checkbox.isChecked():
            if self.firefox_checkbox.isChecked():
                selected_browsers.append("firefox")
            if self.chrome_checkbox.isChecked():
                selected_browsers.append("chrome")

        try:
            os.makedirs(self.current_download_dir, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(
                self,
                "Folder Error",
                f"Could not create download directory:\n{self.current_download_dir}\nError: {e}",
            )
            return

        self.title_label.setText("Starting download...")  # Set status
        self.progress.setValue(0)
        self.speed_label.setText("Speed: N/A")
        self.size_label.setText("Size: N/A")
        self.download_button.setEnabled(False)
        self.download_button.setText("Downloading...")
        self.fetch_formats_button.setEnabled(False)  # Disable fetch during download

        self.download_thread = DownloadThread(
            url,
            browsers=selected_browsers,
            download_dir=self.current_download_dir,
            format_string=format_string,
        )
        self.download_thread.progress_update.connect(self.update_progress_display)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.start()

    # --- End handle_download ---

    # --- on_download_finished --- (MODIFIED - Added Renaming Logic)
    def on_download_finished(self, result):
        self.fetch_formats_button.setEnabled(True)
        if self.title_label.text().startswith("Starting download..."):
            self.title_label.setText(" ")
        self.speed_label.setText("Speed: N/A")

        new_filepath = None  # To store the path after potential rename

        if result["status"] and result["filepath"]:
            original_filepath = result["filepath"]
            # --- Renaming Logic --- START ---
            try:
                # Determine selected format description
                format_desc = ""
                format_data = ""
                if self.video_radio.isChecked():
                    format_desc = self.video_format_combo.currentText()
                    format_data = self.video_format_combo.currentData()
                elif self.audio_radio.isChecked():
                    format_desc = self.audio_format_combo.currentText()
                    format_data = self.audio_format_combo.currentData()

                # Only rename if a specific format was selected (not 'Best Available')
                # and we have a title stored
                if format_data not in ["bv", "ba"] and self.current_video_title:
                    base_title = self.current_video_title
                    # Simplify format description (remove size estimate)
                    format_part = re.sub(r"\s*\([^)]*Size\)$", "", format_desc).strip()
                    sanitized_title = self.sanitize_filename(base_title)
                    sanitized_format = self.sanitize_filename(format_part)
                    # Get extension from original path
                    _, ext = os.path.splitext(original_filepath)
                    # Construct new name
                    new_filename = f"{sanitized_title} - {sanitized_format}{ext}"
                    new_filepath_attempt = os.path.join(
                        self.current_download_dir, new_filename
                    )

                    # Rename the file
                    if original_filepath != new_filepath_attempt:
                        if os.path.exists(new_filepath_attempt):
                            # Handle existing file (e.g., add counter, overwrite, or skip)
                            # For now, just log a warning and don't rename
                            print(
                                f"Warning: File '{new_filename}' already exists. Skipping rename."
                            )
                            new_filepath = original_filepath  # Keep original path
                        else:
                            os.rename(original_filepath, new_filepath_attempt)
                            new_filepath = (
                                new_filepath_attempt  # Update path to new one
                            )
                            print(
                                f"Renamed '{os.path.basename(original_filepath)}' to '{new_filename}'"
                            )
                    else:
                        new_filepath = original_filepath  # No rename needed
                else:
                    # Keep original path if 'Best Available' or no title
                    new_filepath = original_filepath
            except Exception as e:
                print(f"Error during file rename: {e}")
                QMessageBox.warning(
                    self,
                    "Rename Warning",
                    f"Could not rename file after download:\n{e}",
                )
                new_filepath = original_filepath  # Fallback to original path
            # --- Renaming Logic --- END ---

            # Update result with the potentially new filepath
            result["filepath"] = new_filepath

            # Update UI based on the final filepath
            if new_filepath:
                try:
                    size_bytes = os.path.getsize(new_filepath)
                    size_str = self.format_bytes(size_bytes)
                    self.size_label.setText(f"Size: {size_str} / {size_str}")
                except Exception:
                    self.size_label.setText("Size: N/A")  # Reset if error getting size
            else:  # If filepath became None due to rename error
                self.size_label.setText("Size: N/A")
                self.last_download_label.setText("Last download: Failed (Rename Error)")

        elif not result["status"]:
            self.size_label.setText("Size: N/A")
            self.last_download_label.setText("Last download: Failed")

        # Enable download button regardless of rename success/failure
        self.download_button.setEnabled(True)
        self.download_button.setText("Download Now")

        # Show success message ONLY if status is True and we have a final filepath
        if result["status"] and result["filepath"]:
            self.url_input.clear()
            final_filepath = result["filepath"]
            final_filename = os.path.basename(final_filepath)
            self.last_download_label.setText(f"Last download: {final_filename}")
            size_mb = 0
            try:
                size_bytes = os.path.getsize(final_filepath)
                if size_bytes > 0:
                    size_mb = size_bytes / (1024 * 1024)
            except OSError:
                pass
            size_str_msg = f"{size_mb:.2f} MB" if size_mb > 0 else "Unknown Size"

            download_type_msg = "video"
            if final_filename.lower().endswith(  # Check final filename
                (".m4a", ".mp3", ".opus", ".ogg", ".wav", ".aac", ".flac")
            ):
                download_type_msg = "audio"

            msg = QMessageBox(self)
            msg.setWindowTitle("✅ Download Complete")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setTextFormat(Qt.TextFormat.RichText)
            # Show the FINAL filename in the message
            msg.setText(
                f"<b>{final_filename}</b><br><small>Size: {size_str_msg}</small>"
            )
            msg.setInformativeText(
                f"Your {download_type_msg} has been saved successfully to:\n{os.path.dirname(final_filepath)}"
            )
            msg.setStyleSheet("QPushButton{min-width: 100px;}")
            text_label = msg.findChild(QLabel, "qt_msgbox_label")
            info_label = msg.findChild(QLabel, "qt_msgbox_informative_label")
            if text_label:
                text_label.setWordWrap(True)
            if info_label:
                info_label.setWordWrap(True)
            open_btn = msg.addButton(
                "📁 Open Folder", QMessageBox.ButtonRole.AcceptRole
            )
            ok_btn = msg.addButton("OK", QMessageBox.ButtonRole.RejectRole)
            msg.exec()
            if msg.clickedButton() == open_btn:
                self.open_folder()
        elif not result["status"]:
            # Keep failure message logic simple
            if not self.last_download_label.text().endswith("Failed"):
                self.last_download_label.setText("Last download: Failed")
            QMessageBox.critical(
                self, "Download Failed", result.get("message", "Unknown error")
            )

    # --- End on_download_finished ---

    # --- Add sanitize_filename helper method ---
    def sanitize_filename(self, filename):
        # Remove invalid characters for Windows filenames
        sanitized = re.sub(r'[\\/:*?"<>|]', "", filename)
        # Replace spaces with underscores (optional, but common)
        # sanitized = sanitized.replace(' ', '_')
        # Limit length (optional)
        # max_len = 100
        # sanitized = sanitized[:max_len]
        return sanitized

    # --- End sanitize_filename ---

    # --- open_folder --- (unchanged)
    def open_folder(self):
        folder_path = self.current_download_dir
        try:
            os.makedirs(folder_path, exist_ok=True)
        except OSError as e:
            QMessageBox.warning(
                self, "Folder Error", f"Could not create or access download folder: {e}"
            )
            return
        if sys.platform == "win32":
            try:
                norm_folder_path = os.path.normpath(folder_path)
                os.startfile(norm_folder_path)
            except FileNotFoundError:
                QMessageBox.warning(
                    self, "Folder Error", f"Could not find folder: {norm_folder_path}"
                )
            except OSError as e:
                QMessageBox.warning(
                    self,
                    "Folder Error",
                    f"Failed to open folder: {norm_folder_path}\nError: {e}",
                )
            except Exception as e:
                QMessageBox.warning(
                    self, "Folder Error", f"An unexpected error occurred: {e}"
                )
        elif sys.platform == "darwin":
            try:
                subprocess.check_call(["open", folder_path])
            except FileNotFoundError:
                QMessageBox.warning(
                    self, "Folder Error", f"Could not find folder: {folder_path}"
                )
            except subprocess.CalledProcessError:
                QMessageBox.warning(
                    self, "Folder Error", f"Failed to open folder: {folder_path}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self, "Folder Error", f"An unexpected error occurred: {e}"
                )
        else:
            try:
                subprocess.check_call(["xdg-open", folder_path])
            except FileNotFoundError:
                QMessageBox.warning(
                    self,
                    "Folder Error",
                    f"Could not open folder (xdg-open not found?). Path: {folder_path}",
                )
            except subprocess.CalledProcessError:
                QMessageBox.warning(
                    self, "Folder Error", f"Failed to open folder: {folder_path}"
                )
            except Exception as e:
                QMessageBox.warning(
                    self, "Folder Error", f"An unexpected error occurred: {e}"
                )

    # --- End open_folder ---

    def format_bytes(self, size_bytes):
        if size_bytes is None or size_bytes <= 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = 0
        while size_bytes >= 1024 and i < len(size_name) - 1:
            size_bytes /= 1024.0
            i += 1
        if i > 0:
            return f"{size_bytes:.1f} {size_name[i]}"
        else:
            return f"{size_bytes} {size_name[i]}"

    # --- Utility to create a user-friendly format description --- (MODIFIED)
    def create_format_description(self, f):
        # Prioritize resolution/note, fps, codec, size
        desc_parts = []

        # Resolution/Note (e.g., 1080p, 720p60, Audio)
        note = f.get("format_note", "")
        if not note:
            if f.get("height"):
                note = f"{f.get('height')}p"
            elif f.get("acodec") != "none" and f.get("vcodec") == "none":
                note = "Audio"
            elif f.get("vcodec") != "none" and f.get("acodec") == "none":
                note = "Video"
            else:
                note = f.get("resolution", "")  # Fallback
        if note:
            desc_parts.append(note)

        # FPS (only for video)
        if f.get("vcodec") != "none":
            fps = f.get("fps")
            if fps:
                desc_parts.append(f"@{fps:.0f}fps")

        # Extension/Codec (e.g., mp4, opus)
        ext = f.get("ext", "")
        vcodec = f.get("vcodec", "")
        acodec = f.get("acodec", "")
        codec_str = ""
        if vcodec != "none" and vcodec.startswith("avc"):
            codec_str = "H.264"
        elif vcodec != "none" and vcodec.startswith("vp9"):
            codec_str = "VP9"
        elif vcodec != "none" and vcodec.startswith("av01"):
            codec_str = "AV1"
        elif acodec != "none" and acodec.startswith("mp4a"):
            codec_str = "AAC"
        elif acodec != "none" and acodec.startswith("opus"):
            codec_str = "Opus"
        # Add codec if found, otherwise use extension
        if codec_str:
            desc_parts.append(codec_str)
        elif ext:
            desc_parts.append(ext)

        # Filesize
        fs = f.get("filesize") or f.get("filesize_approx")
        if fs:
            size_str = self.format_bytes(fs)
            desc_parts.append(f"({size_str})")
        else:
            desc_parts.append("(N/A Size)")

        return " ".join(desc_parts).strip()

    # --- End Utility ---


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YouTubeDownloaderApp()
    window.show()
    sys.exit(app.exec())
