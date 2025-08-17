import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QMessageBox, QHBoxLayout
)
# 핵심: 로컬 SMTP가 아니라 서버 API 호출로 변경
from core.services import auth_client  # 새로 만든 auth_client.py 사용

class RegisterWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle("회원가입")
        self.setFixedSize(1200, 1000)
        self.parent_window = parent
        self._verified_token = None  # 이메일 인증 완료 후 받은 토큰 저장

        layout = QVBoxLayout()

        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("아이디 입력 (예: user123)")
        layout.addWidget(QLabel("아이디"))
        layout.addWidget(self.id_input)

        layout.addWidget(QLabel("이메일"))
        email_row = QHBoxLayout()
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("이메일 입력 (예: user@example.com)")
        self.send_code_btn = QPushButton("인증코드 보내기")
        self.send_code_btn.clicked.connect(self.send_verification_code)
        email_row.addWidget(self.email_input)
        email_row.addWidget(self.send_code_btn)
        layout.addLayout(email_row)

        code_row = QHBoxLayout()
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("6자리 인증코드")
        self.code_input.setMaxLength(6)
        self.verify_btn = QPushButton("인증 확인")
        self.verify_btn.clicked.connect(self.verify_code)
        code_row.addWidget(self.code_input)
        code_row.addWidget(self.verify_btn)
        layout.addLayout(code_row)

        self.pw_input = QLineEdit()
        self.pw_input.setPlaceholderText("비밀번호 입력 (8자 이상)")
        self.pw_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(QLabel("비밀번호"))
        layout.addWidget(self.pw_input)

        self.pw2_input = QLineEdit()
        self.pw2_input.setPlaceholderText("비밀번호 다시 입력")
        self.pw2_input.setEchoMode(QLineEdit.Password)
        self.pw2_input.returnPressed.connect(self.handle_register)
        layout.addWidget(QLabel("비밀번호 확인"))
        layout.addWidget(self.pw2_input)

        self.register_btn = QPushButton("가입하기")
        self.register_btn.clicked.connect(self.handle_register)
        layout.addWidget(self.register_btn)

        self.back_btn = QPushButton("뒤로가기")
        self.back_btn.clicked.connect(self.go_back)
        layout.addWidget(self.back_btn)

        self.setLayout(layout)

    # 여기부터 서버 호출
    def send_verification_code(self):
        email = self.email_input.text().strip()
        if not email:
            QMessageBox.warning(self, "입력 오류", "이메일을 입력해주세요.")
            return
        try:
            auth_client.send_code(email)
            QMessageBox.information(self, "전송 완료", "인증코드를 이메일로 보냈습니다. 5분 내에 입력해주세요.")
        except Exception as e:
            QMessageBox.critical(self, "전송 실패", f"코드 전송 실패: {e}")

    def verify_code(self):
        email = self.email_input.text().strip()
        code = self.code_input.text().strip()
        if not email or not code:
            QMessageBox.warning(self, "입력 오류", "이메일과 인증코드를 입력해주세요.")
            return
        try:
            token = auth_client.verify_code(email, code)
            self._verified_token = token
            QMessageBox.information(self, "인증 성공", "이메일 인증이 완료되었습니다.")
        except Exception as e:
            QMessageBox.warning(self, "인증 실패", f"{e}")

    def handle_register(self):
        username = self.id_input.text().strip()
        email = self.email_input.text().strip()
        pw1 = self.pw_input.text()
        pw2 = self.pw2_input.text()

        if not username or not email or not pw1 or not pw2:
            QMessageBox.warning(self, "입력 오류", "모든 항목을 입력해주세요.")
            return
        if len(pw1) < 8:
            QMessageBox.warning(self, "비밀번호 오류", "비밀번호는 8자 이상이어야 합니다.")
            return
        if pw1 != pw2:
            QMessageBox.warning(self, "비밀번호 오류", "비밀번호가 일치하지 않습니다.")
            return
        if not self._verified_token:
            QMessageBox.warning(self, "인증 필요", "이메일 인증을 완료한 뒤 가입할 수 있습니다.")
            return
        try:
            ok = auth_client.register(username, email, pw1, self._verified_token)
            if ok:
                QMessageBox.information(self, "가입 완료", f"{username}님, 가입을 환영합니다!")
                self.close()
                if self.parent_window:
                    self.parent_window.show()
        except Exception as e:
            QMessageBox.warning(self, "가입 실패", f"{e}")

    def go_back(self):
        self.close()
        if self.parent_window:
            self.parent_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RegisterWindow()
    window.show()
    sys.exit(app.exec_())
