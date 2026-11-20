"""Tra cứu VBCC 11 cột - CHỈ DEMO. Không đưa dữ liệu thật vào GitHub."""
import json
import unicodedata
from pathlib import Path
from datetime import datetime
import streamlit as st

st.set_page_config(page_title='Tra cứu VBCC - DEMO 11 cột', layout='centered', page_icon='🎓')
st.title('TRA CỨU VĂN BẰNG, CHỨNG CHỈ')
st.warning('BẢN THỬ NGHIỆM – 100 hồ sơ giả lập, không có giá trị xác minh văn bằng thật.')

FIELDS = ['STT','Số hiệu bằng','Số vào sổ gốc cấp văn bằng','Họ, chữ đệm và tên','Ngày, tháng, năm sinh','Giới tính','Dân tộc','Nơi sinh','Tên trường đã học','Niên khóa','Hội đồng thi']
DISPLAY = ['Số hiệu bằng','Số vào sổ gốc cấp văn bằng','Họ, chữ đệm và tên','Ngày, tháng, năm sinh','Tên trường đã học','Niên khóa','Hội đồng thi']

def norm(s):
    return ' '.join(unicodedata.normalize('NFC', str(s or '')).casefold().split())

def dob(s):
    s = str(s or '').strip()
    for fmt in ('%d/%m/%Y','%d-%m-%Y','%Y-%m-%d'):
        try: return datetime.strptime(s, fmt).strftime('%d/%m/%Y')
        except ValueError: pass
    return ''

@st.cache_data

def load_demo():
    path = Path(__file__).with_name('public_demo_11cot.json')
    obj = json.loads(path.read_text(encoding='utf-8'))
    if obj.get('demo_only') is not True or obj.get('schema') != 'VBCC_11_COT' or not isinstance(obj.get('records'),list):
        raise ValueError('Từ chối dữ liệu không đúng cấu trúc DEMO 11 cột.')
    records = obj['records']
    if len(records) != 100 or any(not isinstance(r,dict) or not all(k in r for k in FIELDS) or not str(r['Số hiệu bằng']).startswith('DEMO') or not str(r['Số vào sổ gốc cấp văn bằng']).startswith('SO-DEMO') for r in records):
        raise ValueError('Chỉ chấp nhận đúng bộ 100 hồ sơ DEMO giả lập.')
    return records

try:
    records = load_demo()
except (OSError, ValueError, json.JSONDecodeError) as exc:
    st.error(f'Không đọc được dữ liệu DEMO: {exc}')
    st.stop()

with st.form('tra_cuu'):
    number = st.text_input('Số hiệu bằng', placeholder='DEMO00001', max_chars=50)
    name = st.text_input('Họ, chữ đệm và tên', placeholder='Nguyễn Văn Dũng', max_chars=150)
    birthday = st.text_input('Ngày, tháng, năm sinh (dd/mm/yyyy)', placeholder='02/02/2004', max_chars=10)
    submitted = st.form_submit_button('Tra cứu', type='primary')

if submitted:
    if not number.strip() or not name.strip() or not birthday.strip():
        st.error('Vui lòng nhập đầy đủ ba thông tin.')
    elif not dob(birthday):
        st.error('Ngày sinh không hợp lệ. Nhập theo định dạng dd/mm/yyyy.')
    else:
        found = [r for r in records if norm(r['Số hiệu bằng']) == norm(number) and norm(r['Họ, chữ đệm và tên']) == norm(name) and dob(r['Ngày, tháng, năm sinh']) == dob(birthday)]
        if len(found) != 1:
            st.info('Không tìm thấy hồ sơ phù hợp.')
        else:
            st.success('Tìm thấy hồ sơ giả lập phù hợp (DEMO).')
            for label in DISPLAY:
                st.write(f'**{label}:** {found[0].get(label) or ""}')
