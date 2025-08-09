import os
import sys
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QProgressBar,
    QDialog,
)
from PyQt5.QtCore import Qt, QTimer
from gui.history_window import HistoryWindow
from core.services.predict import predict_from_video


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
        self.loading_dialog = None  # 분석중 다이얼로그 핸들
        self.progress_timer = None  # 게이지 애니메이션용 타이머
        self.progress_value = 0  # 게이지 현재 값
        self.setup_ui()

    def show_loading_dialog(self, message="분석 중입니다...", estimated_ms=4000):
        # QDialog로 로딩창 생성
        self.loading_dialog = QDialog(self)
        self.loading_dialog.setWindowTitle("예측 진행 중")
        self.loading_dialog.setModal(True)
        self.loading_dialog.setFixedSize(300, 100)

        layout = QVBoxLayout()
        self.loading_label = QLabel(message)
        self.loading_label.setAlignment(Qt.AlignCenter)

        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 100)  # 0~100% 진행
        self.loading_bar.setValue(0)  # 초기값 0%

        layout.addWidget(self.loading_label)
        layout.addWidget(self.loading_bar)
        self.loading_dialog.setLayout(layout)
        self.loading_dialog.show()

        # 진행률 타이머 시작
        self.progress_value = 0
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(lambda: self.update_progress(estimated_ms))
        self.progress_timer.start(estimated_ms // 100)

    def update_progress(self, estimated_ms):
        if self.progress_value < 100:
            self.progress_value += 1
            self.loading_bar.setValue(self.progress_value)
        else:
            self.progress_timer.stop()

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
        self.result_table.setHorizontalHeaderLabels(
            ["파일명", "상태", "위험도", "시간"]
        )
        self.result_table.setSortingEnabled(True)
        layout.addWidget(self.result_table)

        self.setLayout(layout)

    # ============================================================
    # 분석 버튼 클릭 시 UI 흐름:
    # 1. 분석 중이면: 무한 게이지바 + '분석 중입니다...' 메시지 표시
    # 2. 분석 끝나면: 게이지바 100% + '분석 결과: 상' 형식 표시
    # ============================================================
    def start_analysis(self):
        if not self.file_path:
            QMessageBox.warning(self, "경고", "먼저 영상을 업로드하세요.")
            return

        # 분석 중 다이얼로그 띄우기 (예상 시간 4초 기준)
        self.show_loading_dialog("AI 분석 중입니다...", estimated_ms=4000)

        # 실제 분석 실행
        result_data = predict_from_video(self.file_path, self.username)

        # 분석 종료 → 로딩창 닫기
        def run_prediction_after_progress():
            result_data = predict_from_video(self.file_path, self.username)

            if not result_data["success"]:
                self.loading_dialog.close()
                QMessageBox.critical(self, "오류", result_data["message"])
                return

            result = result_data["result"]
            filename = result_data["filename"]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

            # 분석 결과 반영
            self.loading_label.setText(f"분석 결과: {result}")
            QApplication.processEvents()
            QTimer.singleShot(1200, self.loading_dialog.close)  # 결과 보여준 뒤 닫기

            # 결과 테이블에 결과 표시
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
                "confidence": None,
                "timestamp": timestamp,
                "description": "AI 자동 분석 결과",
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

        # 예측 실행을 게이지바 100% 완료 후로 연기 (예상 시간 기준)
        QTimer.singleShot(4000, run_prediction_after_progress)

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "영상 선택", "", "Video Files (*.mp4 *.avi *.mov)"
        )
        if file_path:
            self.file_path = file_path
            self.file_label.setText(os.path.basename(file_path))

    def open_history_window(self):
        self.history_window = HistoryWindow(username=self.username)
        self.history_window.show()
        self.hide()


# 주석
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
