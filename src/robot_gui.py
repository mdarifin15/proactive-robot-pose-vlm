# robot_gui.py

import sys
import os
import asyncio
import traceback
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog, QCheckBox,
    QMessageBox, QFrame
)
from PyQt6.QtGui import QPixmap, QFont, QPalette, QColor
from PyQt6.QtCore import Qt, pyqtSlot

# --- Import worker classes from our updated robot_action.py ---
from robot_action import WorkerSignals, AnalysisWorker, RobotActionWorker

# Import your custom backend modules
import tts_handler

class RobotAppGUI(QWidget):
    # --- MODIFIED: The constructor now accepts config_tts ---
    def __init__(self, config_robot, config_llm, config_tts, gemini_client, parent=None):
        super().__init__(parent)
        # Store all the configurations passed from main.py
        self.config_robot = config_robot
        self.config_llm = config_llm
        self.config_tts = config_tts  # --- NEW: Store the TTS config
        self.gemini_client = gemini_client

        # The GUI is responsible for the PyAudio instance
        self.pya_instance = tts_handler.init_pyaudio_for_tts()

        # Member variables for state management
        self.current_image_path = None
        self.current_qt_pixmap = None
        self.current_suggested_actions = []
        self.symptom_description_for_speech = ""

        # Thread references for proper management
        self.analysis_worker_thread = None
        self.action_worker_thread = None

        self._init_ui()
        if not tts_handler.TTS_ENABLED_FLAG:
            self._append_robot_speech("System: TTS is disabled (PyAudio or SDK init failed).")

    def _init_ui(self):
        # This entire UI layout method is unchanged.
        self.setWindowTitle("\U0001F916 Symptom Recognition & Robot Assistant")
        self.setGeometry(100, 100, 850, 700)
        main_palette = self.palette()
        main_palette.setColor(QPalette.ColorRole.Window, QColor("#fafafa"))
        self.setPalette(main_palette)
        self.setAutoFillBackground(True)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        top_row_layout = QHBoxLayout()
        top_row_layout.setSpacing(10)
        image_card, image_card_layout = self._create_card("Uploaded Image")
        self.image_display_label = QLabel("No image loaded")
        self.image_display_label.setMinimumSize(250, 250)
        self.image_display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_display_label.setStyleSheet("QLabel { background-color: #f0f0f0; border-radius: 4px; }")
        image_card_layout.addWidget(self.image_display_label, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        self.upload_button = QPushButton("\U0001F4C6 Upload Image")
        self.upload_button.clicked.connect(self._select_and_analyze_image)
        image_card_layout.addWidget(self.upload_button, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        image_card.setFixedWidth(280)
        top_row_layout.addWidget(image_card, 0)
        analysis_stack_widget = QWidget()
        analysis_stack_layout = QVBoxLayout(analysis_stack_widget)
        analysis_stack_layout.setContentsMargins(0,0,0,0)
        analysis_stack_layout.setSpacing(10)
        desc_card, desc_card_layout = self._create_card("Symptom Description")
        self.symptom_desc_text = QTextEdit()
        self.symptom_desc_text.setReadOnly(True)
        self.symptom_desc_text.setMinimumHeight(60)
        desc_card_layout.addWidget(self.symptom_desc_text)
        analysis_stack_layout.addWidget(desc_card)
        insights_card, insights_card_layout = self._create_card("Symptom Insights")
        self.symptom_insights_text = QTextEdit()
        self.symptom_insights_text.setReadOnly(True)
        self.symptom_insights_text.setMinimumHeight(80)
        insights_card_layout.addWidget(self.symptom_insights_text)
        analysis_stack_layout.addWidget(insights_card)
        actions_card, actions_card_layout = self._create_card("Suggested Robot Actions")
        self.robot_actions_text = QTextEdit()
        self.robot_actions_text.setReadOnly(True)
        self.robot_actions_text.setMinimumHeight(50)
        actions_card_layout.addWidget(self.robot_actions_text)
        analysis_stack_layout.addWidget(actions_card)
        analysis_stack_layout.addStretch(1)
        top_row_layout.addWidget(analysis_stack_widget, 2)
        main_layout.addLayout(top_row_layout)
        speech_card, speech_card_layout = self._create_card("Robot Speech")
        self.robot_speech_area = QTextEdit()
        self.robot_speech_area.setReadOnly(True)
        self.robot_speech_area.setMinimumHeight(100)
        speech_card_layout.addWidget(self.robot_speech_area)
        main_layout.addWidget(speech_card)
        button_frame = QFrame()
        button_frame.setStyleSheet("QFrame { border: none; }")
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0,5,0,5)
        self.auto_execute_checkbox = QCheckBox("Auto-execute Actions")
        button_layout.addWidget(self.auto_execute_checkbox)
        button_layout.addStretch(1)
        self.execute_button = QPushButton("\U000025B6 Execute Actions")
        self.execute_button.setEnabled(False)
        self.execute_button.clicked.connect(self._trigger_robot_execution)
        button_layout.addWidget(self.execute_button)
        self.clear_button = QPushButton("\U0001F5D1 Clear All")
        self.clear_button.clicked.connect(self._clear_all_results)
        button_layout.addWidget(self.clear_button)
        self.about_button = QPushButton("About")
        self.about_button.clicked.connect(self._show_about_dialog)
        button_layout.addWidget(self.about_button)
        main_layout.addWidget(button_frame)
        bottom_bar_frame = QFrame()
        bottom_bar_frame.setFixedHeight(25)
        bottom_bar_frame.setStyleSheet("QFrame { border-top: 1px solid #d0d0d0; background-color: #e8e8e8; }")
        bottom_bar_layout = QHBoxLayout(bottom_bar_frame)
        bottom_bar_layout.setContentsMargins(10,2,10,2)
        self.status_label = QLabel("Ready. Upload an image to start.")
        self.status_label.setStyleSheet("QLabel { border: none; background-color: transparent; }")
        bottom_bar_layout.addWidget(self.status_label, 1)
        main_layout.addWidget(bottom_bar_frame)
        disclaimer_text_content = "Disclaimer: This robot assistant provides suggestions based on AI analysis and is not a substitute for professional medical advice.\n Always consult a healthcare professional for medical concerns."
        self.disclaimer_label = QLabel(disclaimer_text_content)
        self.disclaimer_label.setWordWrap(True)
        self.disclaimer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.disclaimer_label.setStyleSheet("QLabel { font-size: 8pt; color: #666666; margin-top: 3px; padding: 2px; background-color: transparent; }")
        main_layout.addWidget(self.disclaimer_label)
        self.setLayout(main_layout)

    def _create_card(self, title=None):
        # This helper method is unchanged.
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setFrameShadow(QFrame.Shadow.Raised)
        card.setStyleSheet("QFrame { background-color: white; border-radius: 8px; border: 1px solid #d0d0d0;}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10,10,10,10)
        card_layout.setSpacing(6)
        if title:
            card_title = QLabel(title)
            card_title.setFont(QFont("Helvetica", 11, QFont.Weight.Bold))
            card_title.setStyleSheet("QLabel { border: none; background-color: transparent; }")
            card_layout.addWidget(card_title)
        return card, card_layout

    def _update_text_widget(self, widget, text_content):
        # This helper method is unchanged.
        text_to_set = str(text_content) if text_content is not None else ""
        if isinstance(text_to_set, str):
            text_to_set = text_to_set.replace("\\n", "\n")
        widget.setPlainText(text_to_set)

    @pyqtSlot(str)
    def _append_robot_speech(self, text_to_append):
        # This slot is unchanged.
        self.robot_speech_area.append(text_to_append)
        self.robot_speech_area.ensureCursorVisible()

    @pyqtSlot(str)
    def _update_status_label(self, text):
        # This slot is unchanged.
        self.status_label.setText(text)

    def _clear_all_results(self):
        # This method is unchanged.
        if (self.analysis_worker_thread and self.analysis_worker_thread.isRunning()) or \
           (self.action_worker_thread and self.action_worker_thread.isRunning()):
            QMessageBox.information(self, "Busy", "An operation is in progress. Please wait before clearing.")
            return
        self.current_image_path = None
        self.image_display_label.clear()
        self.image_display_label.setText("No image loaded")
        self._update_text_widget(self.symptom_desc_text, "")
        self._update_text_widget(self.symptom_insights_text, "")
        self._update_text_widget(self.robot_actions_text, "")
        self.robot_speech_area.clear()
        self.current_suggested_actions = []
        self.symptom_description_for_speech = ""
        self.execute_button.setEnabled(False)
        self.status_label.setText("Ready. Upload an image to start.")
        if tts_handler.TTS_ENABLED_FLAG:
            self._append_robot_speech("System: Results cleared.")

    def _show_about_dialog(self):
        # This method is unchanged.
        QMessageBox.information(self, "About Robot Assistant", "Symptom Recognition & Robot Assistant\n\nDeveloped by: Arifin, University of Tsukuba\nPowered by Google Gemini and ROBOTIS.\n\n--- IMPORTANT DISCLAIMER ---\nThis tool is for demonstration and assistive purposes only. It is NOT a medical device and does NOT provide medical diagnoses. Always consult with a qualified healthcare professional for any medical concerns or before making any decisions related to your health.")

    def _select_and_analyze_image(self):
        # This method is unchanged.
        if (self.analysis_worker_thread and self.analysis_worker_thread.isRunning()) or \
           (self.action_worker_thread and self.action_worker_thread.isRunning()):
            QMessageBox.information(self, "Busy", "An operation is already in progress. Please wait.")
            return
        filepath, _ = QFileDialog.getOpenFileName(self, "Select an Image", "", "Image files (*.jpg *.jpeg *.png *.bmp *.gif)")
        if not filepath: return
        self._clear_all_results()
        self.current_image_path = filepath
        self._append_robot_speech(f"System: Image selected - {os.path.basename(filepath)}")
        self._update_status_label("Loading image...")
        try:
            pixmap = QPixmap(self.current_image_path)
            if pixmap.isNull(): raise ValueError("QPixmap is null.")
            self.current_qt_pixmap = pixmap.scaled(self.image_display_label.width(), self.image_display_label.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.image_display_label.setPixmap(self.current_qt_pixmap)
        except Exception as e:
            QMessageBox.critical(self, "Image Error", f"Failed to load/display: {e}")
            self._update_status_label("Error loading image.")
            self.image_display_label.setText("Error loading image.")
            return

        self._update_status_label("Analyzing image... Please wait.")
        self.upload_button.setEnabled(False)
        self.execute_button.setEnabled(False)
        if not self.gemini_client:
            self._handle_worker_error("GUI Error: Gemini client not initialized.")
            return

        # The AnalysisWorker creation is unchanged.
        self.analysis_worker_thread = AnalysisWorker(
            self.current_image_path, self.gemini_client,
            self.config_llm, self.config_robot, parent=self
        )
        self.analysis_worker_thread.signals.analysis_complete.connect(self._update_gui_with_analysis_results)
        self.analysis_worker_thread.signals.error_occurred.connect(self._handle_worker_error)
        self.analysis_worker_thread.finished.connect(self._on_analysis_thread_finished)
        self.analysis_worker_thread.start()
        print("GUI: AnalysisWorker thread started.")

    @pyqtSlot()
    def _on_analysis_thread_finished(self):
        # This method is unchanged.
        print("GUI: Analysis thread finished signal received.")
        self.upload_button.setEnabled(True)
        if self.analysis_worker_thread:
            self._disconnect_worker_signals(self.analysis_worker_thread, is_analysis_worker=True)
            if self.analysis_worker_thread.isRunning(): self.analysis_worker_thread.wait(100)
            self.analysis_worker_thread = None
            print("GUI: Analysis worker reference and signals cleared.")

    @pyqtSlot(dict)
    def _update_gui_with_analysis_results(self, analysis_results_dict):
        # This method is unchanged.
        print("GUI: Updating with analysis results.")
        if analysis_results_dict.get("error"):
            if not (self.status_label.text().startswith("Operation failed.") or self.status_label.text().startswith("LLM analysis failed.")):
                self._handle_worker_error(analysis_results_dict["error"])
            return
        desc_text = analysis_results_dict.get("symptom_description", "N/A")
        self.symptom_description_for_speech = desc_text
        self._update_text_widget(self.symptom_desc_text, desc_text)
        insights_text = analysis_results_dict.get("symptom_insights_text", "N/A")
        self._update_text_widget(self.symptom_insights_text, insights_text)
        self.current_suggested_actions = analysis_results_dict.get("action_labels", [])
        actions_display_text = ", ".join(self.current_suggested_actions) if self.current_suggested_actions else "No actions suggested."
        self._update_text_widget(self.robot_actions_text, actions_display_text)
        if self.current_suggested_actions:
            self.execute_button.setEnabled(True)
            self._update_status_label("Analysis complete. Ready for execution.")
            self._append_robot_speech(f"System: Suggested: {actions_display_text}")
            if self.auto_execute_checkbox.isChecked():
                self._append_robot_speech("System: Auto-executing actions...")
                self._trigger_robot_execution()
        else:
            self.execute_button.setEnabled(False)
            self._update_status_label("Analysis complete. No actions to execute.")
            self._append_robot_speech("System: No actions suggested.")

    def _trigger_robot_execution(self):
        # This method is unchanged until the point of worker creation.
        if (self.action_worker_thread and self.action_worker_thread.isRunning()) or \
           (self.analysis_worker_thread and self.analysis_worker_thread.isRunning()):
            QMessageBox.information(self, "Busy", "Another operation is already in progress.")
            return
        if not self.current_suggested_actions:
            QMessageBox.information(self, "No Actions", "No actions to execute.")
            self._append_robot_speech("System: No actions to execute.")
            return

        current_symptom_description = self.symptom_desc_text.toPlainText()
        self._update_status_label("Robot action execution starting...")
        self._append_robot_speech(f"System: Executing: {self.current_suggested_actions}")
        self.upload_button.setEnabled(False)
        self.execute_button.setEnabled(False)
        if not self.gemini_client: self._handle_worker_error("GUI Error: Gemini client not initialized."); return
        if not self.pya_instance and tts_handler.TTS_ENABLED_FLAG: self._handle_worker_error("GUI Error: PyAudio not initialized."); return

        if self.action_worker_thread:
            self._disconnect_worker_signals(self.action_worker_thread, is_analysis_worker=False)
            if self.action_worker_thread.isRunning(): self.action_worker_thread.wait(100)
            self.action_worker_thread = None

        # --- MODIFIED: The creation of RobotActionWorker now includes config_tts ---
        self.action_worker_thread = RobotActionWorker(
            actions_to_perform=list(self.current_suggested_actions),
            symptom_description=current_symptom_description,
            gemini_client=self.gemini_client,
            config_robot=self.config_robot,
            config_llm=self.config_llm,
            config_tts=self.config_tts,  # Pass the dedicated TTS config
            pya_instance_ref=self.pya_instance,
            parent=self
        )

        self.action_worker_thread.signals.action_speech_update.connect(self._append_robot_speech)
        self.action_worker_thread.signals.action_status_update.connect(self._update_status_label)
        self.action_worker_thread.signals.actions_finished.connect(self._on_actions_finished)
        self.action_worker_thread.signals.error_occurred.connect(self._handle_worker_error)
        self.action_worker_thread.start()
        print("GUI: New RobotActionWorker thread started.")

    @pyqtSlot(str)
    def _on_actions_finished(self, message):
        # This method is unchanged.
        print(f"GUI: Actions finished signal received: {message}")
        self._update_status_label(message if message else "Robot actions finished.")
        self.upload_button.setEnabled(True)
        self.execute_button.setEnabled(True)
        if self.action_worker_thread:
            self._disconnect_worker_signals(self.action_worker_thread, is_analysis_worker=False)
            if self.action_worker_thread.isRunning(): self.action_worker_thread.wait(200)
            self.action_worker_thread = None
        print("GUI: Actions worker reference and signals cleared/disconnected.")

    @pyqtSlot(str)
    def _handle_worker_error(self, error_message):
        # This method is unchanged.
        source_object_name = "Unknown Worker"; worker_to_clear = None; is_analysis = False
        sender_obj = self.sender()
        if sender_obj and sender_obj.parent() and isinstance(sender_obj.parent(), QThread):
            source_object_name = sender_obj.parent().objectName()
            if sender_obj.parent() == self.analysis_worker_thread: worker_to_clear = self.analysis_worker_thread; is_analysis = True
            elif sender_obj.parent() == self.action_worker_thread: worker_to_clear = self.action_worker_thread; is_analysis = False

        print(f"GUI: Worker error slot from {source_object_name}: {error_message}")
        QMessageBox.critical(self, "Operation Error", f"Error from {source_object_name}:\n{error_message}")
        self._update_status_label(f"Operation failed ({source_object_name}).")
        self.upload_button.setEnabled(True)
        self.execute_button.setEnabled(True if self.current_suggested_actions else False)

        if worker_to_clear:
            self._disconnect_worker_signals(worker_to_clear, is_analysis_worker=is_analysis)
            if worker_to_clear.isRunning(): worker_to_clear.wait(100)
            if is_analysis: self.analysis_worker_thread = None
            else: self.action_worker_thread = None
            print(f"GUI_DEBUG: Cleared {source_object_name} reference due to its error signal.")
        else: # Fallback
            if self.analysis_worker_thread and not self.analysis_worker_thread.isRunning(): self.analysis_worker_thread = None
            if self.action_worker_thread and not self.action_worker_thread.isRunning(): self.action_worker_thread = None

    def _disconnect_worker_signals(self, worker_thread_ref, is_analysis_worker):
        # This method is unchanged.
        if worker_thread_ref and hasattr(worker_thread_ref, 'signals'):
            signals_obj = worker_thread_ref.signals
            thread_name = worker_thread_ref.objectName() if worker_thread_ref.objectName() else "UnnamedWorker"
            print(f"GUI_DEBUG: Attempting to disconnect signals from {thread_name}...")

            if is_analysis_worker:
                try: signals_obj.analysis_complete.disconnect(self._update_gui_with_analysis_results)
                except TypeError: pass
                try: worker_thread_ref.finished.disconnect(self._on_analysis_thread_finished)
                except TypeError: pass
            else: # RobotActionWorker
                try: signals_obj.action_speech_update.disconnect(self._append_robot_speech)
                except TypeError: pass
                try: signals_obj.action_status_update.disconnect(self._update_status_label)
                except TypeError: pass
                try: signals_obj.actions_finished.disconnect(self._on_actions_finished)
                except TypeError: pass

            # Common signal for both worker types
            try: signals_obj.error_occurred.disconnect(self._handle_worker_error)
            except TypeError: pass
            
            print(f"GUI_DEBUG: Signal disconnection attempt complete for {thread_name}.")

    def closeEvent(self, event):
        # This method is unchanged and correctly handles PyAudio termination.
        threads_active = False; active_threads_list = []
        if self.analysis_worker_thread and self.analysis_worker_thread.isRunning(): threads_active = True; active_threads_list.append(self.analysis_worker_thread)
        if self.action_worker_thread and self.action_worker_thread.isRunning(): threads_active = True; active_threads_list.append(self.action_worker_thread)
        quit_message = "Are you sure you want to quit?"
        if threads_active: quit_message = "Operations are in progress. Quit anyway?"
        reply = QMessageBox.question(self, 'Confirm Exit', quit_message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            print("GUI: Closing application confirmed.")
            if threads_active:
                print("GUI: Waiting briefly for active threads...")
                for thread_to_wait in active_threads_list:
                    self._disconnect_worker_signals(thread_to_wait, (thread_to_wait == self.analysis_worker_thread))
                    thread_to_wait.wait(200)

            # Terminate PyAudio when the GUI closes
            if self.pya_instance:
                tts_handler.terminate_pyaudio_for_tts(self.pya_instance)

            event.accept()
            QApplication.instance().quit()
        else:
            event.ignore()