"""Public VBCC DEMO. The JSON in public GitHub is PUBLIC; NEVER put real personal records here."""
import json
import unicodedata
from pathlib import Path
import streamlit as st

st.set_page_config(page_title='Tra cứu VBCC — DEMO', layout='centered')
st.title('TRA CỨU VĂN BẰNG, CHỨNG CHỈ')
st.warning('BẢN THỬ NGHIỆM — Toàn bộ hồ sơ là dữ liệu giả lập. Không có giá trị xác minh văn bằng thật.')


def normalize(s):
    s = unicodedata.normalize('NFD', str(s).strip().casefold())
    return ' '.join(''.join(c for c in s if unicodedata.category(c) != 'Mn').replace('đ', 'd').split())


@st.cache_data
def load_data():
    path = Path(__file__).parent / 'public_demo.json'
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8') as f:
        payload = json.load(f)
    if payload.get('demo_only') is not True or not isinstance(payload.get('records'), list):
        raise ValueError('Tệp không đúng định dạng DEMO.')
    if any(not str(r.get('Số hiệu bằng', '')).startswith('DEMO') for r in payload['records']):
        raise ValueError('Từ chối dữ liệu không phải DEMO.')
    return payload['records']

try:
    rows = load_data()
except (ValueError, OSError, json.JSONDecodeError) as e:
    st.error(f'Không đọc được dữ liệu công khai: {e}')
    st.stop()
if not rows:
    st.info('Chưa có phiên dữ liệu DEMO được công bố.')
else:
    with st.form('lookup'):
        number = st.text_input('Số hiệu bằng')
        name = st.text_input('Họ và tên')
        dob = st.text_input('Ngày, tháng, năm sinh (nhập đúng như dữ liệu mẫu)')
        search = st.form_submit_button('Tra cứu', type='primary')
    if search:
        if not all([number.strip(), name.strip(), dob.strip()]):
            st.error('Vui lòng nhập đầy đủ cả ba thông tin.')
        else:
            matches = [r for r in rows if normalize(r.get('Số hiệu bằng')) == normalize(number)
                       and normalize(r.get('Họ, chữ đệm và tên')) == normalize(name)
                       and str(r.get('Ngày, tháng, năm sinh', '')).strip() == dob.strip()]
            if not matches:
                st.info('Không tìm thấy hồ sơ phù hợp.')
            else:
                st.success('Tìm thấy hồ sơ giả lập phù hợp.')
                for r in matches:
                    st.write('**Số hiệu bằng:**', r['Số hiệu bằng'])
                    st.write('**Tên văn bằng:**', r.get('Tên văn bằng', ''))
                    st.write('**Tình trạng văn bằng:**', r.get('Tình trạng văn bằng', ''))
