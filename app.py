# app.py
import sys, os
from PyQt5.QtWidgets import QApplication
from core.models import create_user_table, create_analysis_table
from gui.main_window import MainWindow, load_stylesheet
from PyQt5.QtGui import QIcon

# DB 폴더 자동 생성
if not os.path.exists("database"):
    os.makedirs("database")

# DB 테이블 생성
create_user_table()
create_analysis_table()

# 앱 실행
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("assets/Drovis_logo.ico"))
    app.setStyleSheet(load_stylesheet())  # 스타일시트 적용
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
