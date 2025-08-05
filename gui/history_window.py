from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)
from PyQt5.QtCore import Qt
import json
import os


class HistoryWindow(QWidget):
    def __init__(self, username=None, history_file="data/history.json"):
        super().__init__()
        self.setWindowTitle("분석 기록")
        self.setGeometry(300, 200, 900, 600)
        self.history_file = history_file
        self.username = username

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("최근 분석 기록")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 15px;")
        layout.addWidget(title)

        # ✅ 5열 테이블 구성
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            [
                "파일명",
                "포즈 인식 성공",
                "탐지 행동 비율\n(아래 내용은 예시임)",
                "위험도",
                "시간",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # 뒤로 가기 버튼
        btn_back = QPushButton("뒤로 가기")
        btn_back.clicked.connect(self.go_back_to_upload)
        layout.addWidget(btn_back)

        # 로그아웃 버튼
        btn_logout = QPushButton("로그아웃")
        btn_logout.clicked.connect(self.logout_to_main)
        layout.addWidget(btn_logout)

        # 닫기 버튼
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

        # 기록 삭제 버튼
        btn_clear = QPushButton("기록 삭제")
        btn_clear.clicked.connect(self.clear_history)
        layout.addWidget(btn_clear)

        self.setLayout(layout)
        self.load_history()

    def load_history(self):
        if not os.path.exists(self.history_file):
            return

        with open(self.history_file, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []

        self.table.setRowCount(len(history))

        for row, item in enumerate(history):
            filename = item.get("filename", "")
            result = item.get("result", "미정")
            timestamp = item.get("timestamp", "")
            pose_success = item.get("pose_success", 0)
            pose_fail = item.get("pose_fail", 0)
            label_counts = item.get("label_counts", {})

            # 1. 파일명
            self.table.setItem(row, 0, QTableWidgetItem(filename))

            # 2. 포즈 인식 결과
            pose_text = f"성공 : {pose_success}프레임\n실패 : {pose_fail}프레임"
            self.table.setItem(row, 1, QTableWidgetItem(pose_text))

            # 3. 탐지 행동 비율
            label_text = ""
            for label in ["Loitering", "Reapproach", "Delivery"]:
                count = label_counts.get(label, 0)
                total = sum(label_counts.values())
                percent = (count / total * 100) if total > 0 else 0
                label_text += f"- {label} : {count}회 ({percent:.2f}%)\n"
            self.table.setItem(row, 2, QTableWidgetItem(label_text.strip()))

            # 4. 위험도 (색상 포함)
            risk_item = QTableWidgetItem(result)
            if result == "상":
                risk_item.setForeground(Qt.red)
            elif result == "중":
                risk_item.setForeground(Qt.darkYellow)
            elif result == "하":
                risk_item.setForeground(Qt.darkGreen)
            self.table.setItem(row, 3, risk_item)

            # 5. 분석 시간
            self.table.setItem(row, 4, QTableWidgetItem(timestamp))

    def clear_history(self):
        reply = QMessageBox.question(
            self,
            "기록 삭제",
            "모든 분석 기록을 삭제할까요?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if os.path.exists(self.history_file):
                os.remove(self.history_file)
            self.table.setRowCount(0)
            QMessageBox.information(self, "삭제됨", "기록이 삭제되었습니다.")

    def go_back_to_upload(self):
        from gui.upload_window import UploadWindow  # 순환 import 방지

        self.upload_window = UploadWindow(username=self.username)
        self.upload_window.show()
        self.close()

    def logout_to_main(self):
        from gui.main_window import MainWindow

        self.main_window = MainWindow()
        self.main_window.show()
        self.close()
        self.deleteLater()


# 단독 실행 시 테스트용
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = HistoryWindow()
    window.show()
    sys.exit(app.exec_())
