"""Tra cứu VBCC 11 cột từ Supabase, CHỈ DỮ LIỆU DEMO.

Không đưa dữ liệu VBCC thật hoặc khóa Supabase lên GitHub.
"""
import json
import logging
import re
import time
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import streamlit as st

st.set_page_config(page_title="Tra cứu VBCC - DEMO 11 cột", layout="centered", page_icon="🎓")
st.title("TRA CỨU VĂN BẰNG, CHỨNG CHỈ")
st.warning("BẢN THỬ NGHIỆM – chỉ tra cứu hồ sơ DEMO, không có giá trị xác minh văn bằng thật.")

DISPLAY = {
"so_hieu_bang": "Số hiệu bằng",
"so_vao_so_goc": "Số vào sổ gốc cấp văn bằng",
"ho_ten": "Họ, chữ đệm và tên",
"ngay_sinh": "Ngày, tháng, năm sinh",
"ten_truong": "Tên trường đã học",
"nien_khoa": "Niên khóa",
"hoi_dong_thi": "Hội đồng thi",
}


def valid_date(value: str) -> bool:
if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
return False
try:
datetime.strptime(value, "%d/%m/%Y")
return True
except ValueError:
return False


def query_vbcc(number: str, name: str, birthday: str):
"""Chỉ lấy tối đa 2 kết quả khớp đủ 3 trường, không tải cả bảng."""
try:
base = str(st.secrets["SUPABASE_URL"]).strip().rstrip("/")
secret = str(st.secrets["SUPABASE_SECRET_KEY"]).strip()
except (KeyError, FileNotFoundError) as exc:
raise RuntimeError("Chưa cấu hình Supabase Secrets.") from exc

parsed = urlparse(base)
if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".supabase.co") or parsed.path not in ("", "/"):
raise RuntimeError("SUPABASE_URL không hợp lệ; dùng Project URL, không kèm /rest/v1/.")
if not secret:
raise RuntimeError("Thiếu SUPABASE_SECRET_KEY.")

params = urlencode({
"select": ",".join(DISPLAY.keys()),
"so_hieu_bang": "eq." + number,
"ho_ten": "eq." + name,
"ngay_sinh": "eq." + birthday,
"limit": "2",
})
req = Request(
f"{base}/rest/v1/vbcc?{params}",
headers={
"apikey": secret,
"Accept": "application/json",
},
method="GET",
)
try:
with urlopen(req, timeout=12) as response:
result = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        # Không hiển thị chi tiết lỗi máy chủ hoặc thông tin xác thực cho người dùng.
        raise RuntimeError("Không kết nối được cơ sở dữ liệu. Vui lòng thử lại sau.") from exc
    except HTTPError as exc:
        logging.error("VBCC Supabase HTTP error: status=%s", exc.code)
        raise RuntimeError("Không kết nối được cơ sở dữ liệu. Vui lòng thử lại sau.") from None
    except (URLError, TimeoutError, ValueError) as exc:
        logging.error("VBCC Supabase connection error: type=%s", type(exc).__name__)
        raise RuntimeError("Không kết nối được cơ sở dữ liệu. Vui lòng thử lại sau.") from None
if not isinstance(result, list):
raise RuntimeError("Phản hồi cơ sở dữ liệu không hợp lệ.")
return result


with st.form("tra_cuu"):
number = st.text_input("Số hiệu bằng", placeholder="DEMO00001", max_chars=50)
name = st.text_input("Họ, chữ đệm và tên", placeholder="Nguyễn Văn Dũng", max_chars=150)
birthday = st.text_input("Ngày, tháng, năm sinh (dd/mm/yyyy)", placeholder="02/02/2004", max_chars=10)
submitted = st.form_submit_button("Tra cứu", type="primary")

if submitted:
number, name, birthday = number.strip(), name.strip(), birthday.strip()
if not number or not name or not birthday:
st.error("Vui lòng nhập đầy đủ ba thông tin.")
elif not valid_date(birthday):
st.error("Ngày sinh không hợp lệ. Nhập đúng định dạng dd/mm/yyyy.")
elif not re.fullmatch(r"DEMO\d{5}", number):
st.info("Phiên bản thử nghiệm chỉ hỗ trợ số hiệu bằng DEMO.")
else:
# Giảm gửi yêu cầu liên tiếp trong cùng phiên; KHÔNG thay thế rate limit ở phía máy chủ.
now = time.monotonic()
last = st.session_state.get("last_lookup_time", 0.0)
if now - last < 3:
st.warning("Vui lòng chờ vài giây trước khi tra cứu tiếp.")
else:
st.session_state["last_lookup_time"] = now
try:
found = query_vbcc(number, name, birthday)
except RuntimeError as exc:
st.error(str(exc))
else:
if len(found) != 1 or found[0].get("so_hieu_bang") != number:
st.info("Không tìm thấy hồ sơ phù hợp.")
else:
st.success("Tìm thấy hồ sơ giả lập phù hợp (DEMO).")
for field, label in DISPLAY.items():
st.write(f"**{label}:** {found[0].get(field) or ''}")
