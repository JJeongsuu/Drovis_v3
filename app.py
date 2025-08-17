# app.py
import sys, os, ctypes, threading, time, socket
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from core.models import create_user_table, create_analysis_table
from gui.main_window import MainWindow, load_stylesheet

# ▼ 추가: 서버(app 객체) 직접 임포트해서 uvicorn에 넘기기 (모듈 문자열 이슈 회피)
try:
    from server.main import app as api_app  # Drovis_v3/server/main.py 의 FastAPI 인스턴스
except Exception:
    api_app = None  # 개발 중 임시 실패 대비

API_HOST = os.getenv("DROVIS_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("DROVIS_API_PORT", "8000"))

def resource_path(*parts):
    # PyInstaller로 빌드해도 동작하도록 안전한 경로 생성
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)

# DB 폴더 자동 생성 (app.py가 있는 Drovis_v3 기준으로 절대경로 사용)
DB_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database"))
os.makedirs(DB_DIR, exist_ok=True)

# DB 테이블 생성
create_user_table()
create_analysis_table()

# ====== 여기서부터 로컬 API 자동 실행 추가 ======
def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        return s.connect_ex((host, port)) == 0

def start_local_api():
    """앱 실행 시 백그라운드에서 FastAPI(uvicorn) 자동 기동"""
    if _is_port_open(API_HOST, API_PORT):
        return  # 이미 켜져 있음

    def _run():
        # 지연 임포트: 실행 시에만 로드 (PyInstaller 호환 ↑)
        import uvicorn
        if api_app is None:
            # server.main 을 직접 임포트 시도 (개발 환경 경로 문제 대비)
            from server.main import app as dynamic_app
        else:
            dynamic_app = api_app
        uvicorn.run(dynamic_app, host=API_HOST, port=API_PORT, log_level="info")

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    # 서버 리스닝 대기 (최대 5초)
    for _ in range(50):
        if _is_port_open(API_HOST, API_PORT):
            break
        time.sleep(0.1)
# ====== 로컬 API 자동 실행 추가 끝 ======

# 앱 실행
if __name__ == "__main__":

    # 윈도우에서 작업표시줄 그룹/아이콘을 이 앱용으로 분리
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u"Drovis.App")
    except Exception:
        pass

    # ▼ 추가: 앱 켤 때 로컬 API 자동 실행
    start_local_api()

    app = QApplication(sys.argv)

    # 아이콘: 반드시 창 생성 전에 전역으로 설정 + 절대경로
    ICON_PATH = resource_path("assets", "Drovis_logo.ico")
    app.setWindowIcon(QIcon(ICON_PATH))

    # 스타일
    app.setStyleSheet(load_stylesheet())

    # 메인 창 (보수적으로 창에도 한번 더 설정)
    window = MainWindow()
    window.setWindowIcon(QIcon(ICON_PATH))
    window.show()

    sys.exit(app.exec_())
