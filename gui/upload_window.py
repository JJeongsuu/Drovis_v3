import os
import sys
import json
<<<<<<< HEAD
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTableWidget,
    QTableWidgetItem, QMessageBox
)
from gui.history_window import HistoryWindow
from core.services.predict import predict_from_video
=======


# Qt 플랫폼 환경변수
from PyQt5 import QtCore

plugin_path = os.path.join(os.path.dirname(QtCore.__file__), "plugins", "platforms")
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path

>>>>>>> origin/main

# 경로 설정
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = r"C:\경로\plugins\platforms"
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(PARENT_DIR)


class UploadWindow(QWidget):
    def __init__(self, username="guest"):
        super().__init__()
        self.setWindowTitle("Drovis - 영상 분석")
        self.resize(1000, 600)
        self.file_path = None
        self.history_window = None
        self.username = username
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # 영상 업로드 영역
        upload_layout = QHBoxLayout()
        self.upload_btn = QPushButton("영상 업로드")
        self.upload_btn.clicked.connect(self.upload_file)
        self.file_label = QLabel("업로드된 파일 없음")
        upload_layout.addWidget(self.upload_btn)
        upload_layout.addWidget(self.file_label)
        layout.addLayout(upload_layout)

        # 분석 시작 버튼
        self.analyze_btn = QPushButton("분석 시작")
        self.analyze_btn.clicked.connect(self.start_analysis)
        layout.addWidget(self.analyze_btn)

        # 분석 기록 보기
        self.history_btn = QPushButton("분석 기록 보기")
        self.history_btn.clicked.connect(self.open_history_window)
        layout.addWidget(self.history_btn)

        # 결과 테이블
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["파일명", "상태", "유사도 결과", "시간"])
        self.result_table.setSortingEnabled(True)
        layout.addWidget(self.result_table)

        self.setLayout(layout)

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "영상 선택", "", "Video Files (*.mp4 *.avi *.mov)"
        )
        if file_path:
            self.file_path = file_path
            self.file_label.setText(os.path.basename(file_path))

    def start_analysis(self):
        if not self.file_path:
            QMessageBox.warning(self, "경고", "먼저 영상을 업로드하세요.")
            return

        result_data = predict_from_video(self.file_path, self.username)

        if not result_data["success"]:
            QMessageBox.critical(self, "오류", result_data["message"])
            return

        result = result_data["result"]
        filename = result_data["filename"]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 테이블에 결과 표시
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        self.result_table.setItem(row, 0, QTableWidgetItem(filename))
        self.result_table.setItem(row, 1, QTableWidgetItem("완료"))
        self.result_table.setItem(row, 2, QTableWidgetItem(result))
        self.result_table.setItem(row, 3, QTableWidgetItem(timestamp))

        # 기록 저장
        history_item = {
            "filename": filename,
            "result": result,
            "confidence": None,  # 추후 confidence 추가 시 여기에
            "timestamp": timestamp,
            "description": "AI 자동 분석 결과"
        }

        history_file = "data/history.json"
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        try:
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            else:
                history = []
        except json.JSONDecodeError:
            history = []

        history.append(history_item)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def open_history_window(self):
        self.history_window = HistoryWindow(username=self.username)
        self.history_window.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # QSS 적용
    qss_path = os.path.join(os.path.dirname(__file__), "styles.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = UploadWindow()
    window.show()
    sys.exit(app.exec_())
