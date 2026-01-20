import os
import sys
import threading
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

# --- 테스트용: 아주 작은 PDF 바이트 (1페이지) ---
TEST_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Contents 4 0 R >>\nendobj\n"
    b"4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 18 Tf 50 150 Td (HELLO TEST PDF) Tj ET\nendstream\nendobj\n"
    b"xref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n0000000200 00000 n \n"
    b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n300\n%%EOF\n"
)

PORT = 8765

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path != "/preview.pdf":
            self.send_response(404)
            self.end_headers()
            return

        data = TEST_PDF_BYTES
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        return

def run_server():
    httpd = HTTPServer(("127.0.0.1", PORT), Handler)
    httpd.serve_forever()

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    url = f"http://127.0.0.1:{PORT}/preview.pdf?ts={int(time.time()*1000)}"
    print("Opening:", url)

    try:
        # 기본 브라우저로 열기
        if sys.platform == "win32":
            os.system(f'start "" "{url}"')
        else:
            webbrowser.open(url)
    except Exception as e:
        print("Browser open failed:", e)

    # 서버가 바로 죽지 않게 잠깐 유지
    time.sleep(10)
    print("Done. (If you saw a PDF page in browser, localhost preview works.)")
