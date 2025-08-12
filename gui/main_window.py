# ================================
# main_window.py
# Drovis: 메인 메뉴 창
# - 역할: 로그인/회원가입, 업로드 창, 기록 창으로 이동하는 허브
# - 포인트: 경로 설정, 스타일(QSS) 로드, 시그널-슬롯 연결
# ================================
import sys
import os
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from PyQt5.QtCore import Qt  # 중앙정렬

# -------------------------------------------------------
# [모듈 경로 설정]
# - 현재 파일의 상위 폴더를 sys.path에 추가하여
#   'gui.~~~' 같은 내부 모듈을 import 할 수 있게 함
# -------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(PARENT_DIR)

# -------------------------------------------------------
# [다른 창 import]
# - LoginWindow: 로그인 화면
# - RegisterWindow: 회원가입 화면
# - 상대 경로 기준으로 'gui' 패키지 아래에 있다고 가정
# -------------------------------------------------------
from gui.login_window import LoginWindow
from gui.register_window import RegisterWindow


# -------------------------------------------------------
# [스타일시트 로더]
# - 같은 폴더의 styles.qss 파일을 읽어 문자열로 반환
# - 파일이 없으면 빈 문자열 반환(= 스타일 미적용)
# -------------------------------------------------------
def load_stylesheet():
    qss_path = os.path.join(os.path.dirname(__file__), "styles.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


class MainWindow(QMainWindow):
    """
    앱 실행 시 가장 먼저 보이는 메인 메뉴 창.
    - 중앙에 환영 문구 라벨
    - 로그인 / 회원가입 버튼
    - 버튼 클릭 시 각각의 창을 띄우고, 메인 창은 숨김
    """

    def __init__(self):
        super().__init__()

        # -----------------------------
        # [Title Bar]
        # - 창 제목과 크기 설정
        # -----------------------------
        self.setWindowTitle("Drovis")
        self.setFixedSize(1200, 1000)

        # -----------------------------
        # [중앙 위젯 + 레이아웃 구성]
        # - QMainWindow는 반드시 setCentralWidget 필요
        # - VBox : 세로 배치(위→아래) 버튼들
        # -----------------------------
        central_widget = QWidget()
        layout = QVBoxLayout()

        # 환영 문구 라벨
        welcome_label = QLabel("마약 드로퍼 탐지를 도와주는 Drovis입니다.")
        # (1) 텍스트 중앙 정렬
        welcome_label.setAlignment(Qt.AlignCenter)

        # (2) 레이아웃 내에서 위젯 위치도 중앙 정렬
        layout.addWidget(welcome_label)
        layout.setAlignment(welcome_label, Qt.AlignCenter)

        # -----------------------------
        # [로그인 버튼]
        # - 클릭 시 open_login_window() 실행
        # -----------------------------
        login_btn = QPushButton("로그인")
        login_btn.clicked.connect(
            self.open_login_window
        )  # 로그인 버튼 클릭 시 로그인 창 열기
        layout.addWidget(login_btn)  # 로그인 버튼 추가

        # -----------------------------
        # [회원가입 버튼]
        # - 클릭 시 open_register_window() 실행
        # -----------------------------
        register_btn = QPushButton("회원가입")
        register_btn.clicked.connect(self.open_register_window)
        layout.addWidget(register_btn)

        # 중앙 위젯에 레이아웃 장착 후 메인 창에 설정
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # 창 초기화
        self.login_window = None
        self.register_window = None

    # ---------------------------------------------------
    # [로그인 창 열기]
    # - LoginWindow를 생성하여 표시
    # - parent=self 로 넘겨서 자식 창에서 '뒤로가기' 시 복귀 가능
    # - self.hide()로 메인 창은 화면에서만 숨김(완전 종료 아님)
    # ---------------------------------------------------
    def open_login_window(self):
        self.login_window = LoginWindow(parent=self)
        self.login_window.show()
        self.hide()

    # ---------------------------------------------------
    # [회원가입 창 열기]
    # - RegisterWindow를 생성하여 표시
    # - parent=self 로 넘겨서 가입 완료/취소 시 메인으로 복귀
    # ---------------------------------------------------
    def open_register_window(self):
        self.register_window = RegisterWindow(parent=self)
        self.register_window.show()
        self.hide()


# -------------------------
# 애플리케이션 시작부
# - QSS 로드 후 QApplication 생성
# - MainWindow 인스턴스 표시
# -------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 앱 전체에 스타일시트 적용(선택 사항)
    app.setStyleSheet(load_stylesheet())

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
