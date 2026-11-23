import hashlib
import logging
import hmac
import time
import unicodedata
from urllib.parse import urlparse

import requests
from collections import Counter
from io import BytesIO

import streamlit as st
from openpyxl import load_workbook

st.set_page_config(page_title='Quản trị dữ liệu VBCC', page_icon='🔐', layout='wide')
HEADERS = ['STT','Số hiệu bằng','Số vào sổ gốc cấp văn bằng','Họ, chữ đệm và tên','Ngày, tháng, năm sinh','Giới tính','Dân tộc','Nơi sinh','Tên trường đã học','Niên khóa','Hội đồng thi']
MAX_ATTEMPTS = 5
SESSION_IDLE_SECONDS = 15 * 60  # Kiểm tra khi ứng dụng chạy lại; không phải bộ hẹn giờ nền.

def verify_password(password, stored):
    try:
        alg, rounds, salt, digest = stored.split('$')
        n = int(rounds)
        if alg != 'pbkdf2_sha256' or not 300000 <= n <= 2000000:
            return False
        raw_salt, expected = bytes.fromhex(salt), bytes.fromhex(digest)
        if len(raw_salt) < 16 or len(expected) != 32:
            return False
        return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), raw_salt, n), expected)
    except (ValueError, TypeError, AttributeError):
        return False

st.title('QUẢN TRỊ DỮ LIỆU VĂN BẰNG, CHỨNG CHỈ')
st.info('Hệ thống quản trị dữ liệu VBCC - Sở Giáo dục và Đào tạo Khánh Hòa.')
try:
    admin_username = str(st.secrets['ADMIN_USERNAME'])
    admin_hash = str(st.secrets['ADMIN_PASSWORD_HASH'])
except (KeyError, FileNotFoundError):
    st.error('Chưa cấu hình tài khoản quản trị trong Streamlit Secrets.')
    st.stop()

for k, default in [('authenticated',False),('failed_attempts',0),('locked_until',0.0),('last_activity',0.0)]:
    if k not in st.session_state:
        st.session_state[k] = default

# Hết hạn phiên khi không có tương tác; kiểm tra tại lần chạy ứng dụng tiếp theo.
if st.session_state.authenticated:
    now = time.time()
    last = st.session_state.last_activity
    if not last or now - last > SESSION_IDLE_SECONDS:
        st.session_state.authenticated = False
        st.session_state.last_activity = 0.0
        for key in ('vbcc_file', 'vbcc_compared', 'vbcc_inserted', 'vbcc_total',
                    'vbcc_new', 'vbcc_output', 'vbcc_confirm_insert'):
            st.session_state.pop(key, None)
        st.warning('Phiên quản trị đã hết hạn. Vui lòng đăng nhập lại.')
        st.stop()
    st.session_state.last_activity = now

if not st.session_state.authenticated:
    st.subheader('Đăng nhập quản trị')
    remaining = st.session_state.locked_until - time.time()
    if remaining > 0:
        st.error(f'Đã vượt quá số lần thử. Vui lòng thử lại sau khoảng {int(remaining // 60)+1} phút.')
        st.stop()
    if st.session_state.locked_until:
        st.session_state.failed_attempts = 0
        st.session_state.locked_until = 0.0
    with st.form('login', clear_on_submit=True):
        username = st.text_input('Tên đăng nhập', max_chars=100)
        password = st.text_input('Mật khẩu', type='password', max_chars=256)
        submitted = st.form_submit_button('Đăng nhập', type='primary')
    if submitted:
        u_ok = hmac.compare_digest(username.strip().encode('utf-8'), admin_username.encode('utf-8'))
        p_ok = verify_password(password, admin_hash)
        if u_ok and p_ok:
            st.session_state.authenticated = True
            st.session_state.failed_attempts = 0
            st.session_state.locked_until = 0.0
            st.session_state.last_activity = time.time()
            st.rerun()
        st.session_state.failed_attempts += 1
        if st.session_state.failed_attempts >= MAX_ATTEMPTS:
            st.session_state.locked_until = time.time() + 900
            st.error('Đã vượt quá số lần thử. Vui lòng thử lại sau 15 phút.')
        else:
            st.error('Tên đăng nhập hoặc mật khẩu không đúng.')
    st.caption('Bản DEMO — chỉ sử dụng hồ sơ giả lập.')
    st.stop()

st.success('Đăng nhập quản trị thành công.')
if st.button('Đăng xuất'):
    for key in ('authenticated', 'last_activity', 'vbcc_file', 'vbcc_compared',
                'vbcc_inserted', 'vbcc_total', 'vbcc_new', 'vbcc_output',
                'vbcc_confirm_insert'):
        st.session_state.pop(key, None)
    st.rerun()
st.caption('Phiên quản trị hết hạn sau 15 phút không tương tác (kiểm tra ở lần thao tác tiếp theo).')
st.warning('CHẾ ĐỘ DEMO — Chỉ cho phép nhập hồ sơ giả lập; không tải dữ liệu thật.')
st.subheader('Bước 6 — Tải và kiểm tra Excel 11 cột')
st.caption('Chỉ sử dụng hồ sơ DEMO, không tải dữ liệu văn bằng thật lên ứng dụng thử nghiệm.')
up = st.file_uploader('Chọn file Excel (.xlsx)', type=['xlsx'], max_upload_size=20)
if up is None:
    st.stop()

try:
    if up.size > 20 * 1024 * 1024:
        st.error('File vượt quá 20 MB.')
        st.stop()
    wb = load_workbook(BytesIO(up.getvalue()), read_only=True, data_only=False)
    sheet_name = next((n for n in wb.sheetnames if n.casefold() == 'data'), None)
    if sheet_name is None:
        st.error('Không tìm thấy sheet Data (không phân biệt chữ hoa/chữ thường).')
        st.stop()
    ws = wb[sheet_name]
    if ws.max_column != 11:
        st.error(f'Sheet {sheet_name} có {ws.max_column} cột, yêu cầu đúng 11 cột.')
        st.stop()
    if ws.max_row > 20002:
        st.error('Bản DEMO giới hạn tối đa 20.000 dòng dữ liệu mỗi lần kiểm tra.')
        st.stop()
    row_iter = ws.iter_rows(min_row=2, max_col=11)
    header = [str(c.value).strip() if c.value is not None else '' for c in next(row_iter)]
    if header != HEADERS:
        st.error('Tiêu đề 11 cột tại dòng 2 không khớp mẫu. Không tự động đổi thứ tự cột.')
        st.dataframe([{'Cột':i+1,'Yêu cầu':HEADERS[i],'Thực tế':header[i]} for i in range(11)], hide_index=True)
        st.stop()
    rows, warnings, errors = [], [], []
    normalized_stt = 0
    for cells in row_iter:
        if all(c.value is None or str(c.value).strip() == '' for c in cells):
            continue
        record = {}
        for col_name, cell in zip(HEADERS, cells):
            val = cell.value
            if val is None:
                record[col_name] = ''
            elif cell.data_type == 's' and isinstance(val, str):
                record[col_name] = val
            elif col_name == 'STT' and cell.data_type == 'n' and type(val) in (int, float) and val >= 0 and float(val).is_integer():
                # Convert only integer STT to TEXT. Never alter the source workbook.
                record[col_name] = str(int(val))
                normalized_stt += 1
            else:
                # Do not silently convert other columns: Excel may already have lost leading zeros.
                record[col_name] = str(val)
                errors.append({'Dòng Excel':cell.row,'Cột':col_name,
                               'Vấn đề':f'Ô không lưu kiểu TEXT (kiểu Excel: {cell.data_type}); cần đối chiếu dữ liệu gốc.'})
        for required in ('Số hiệu bằng','Họ, chữ đệm và tên','Ngày, tháng, năm sinh'):
            if not record[required].strip():
                errors.append({'Dòng Excel':cells[0].row,'Cột':required,'Vấn đề':'Thiếu trường tra cứu bắt buộc.'})
        rows.append((cells[0].row,record))
    wb.close()
except Exception as e:
    st.error(f'Không đọc được file Excel ({type(e).__name__}). Kiểm tra lại file .xlsx.')
    st.stop()

keys = Counter((r['Số hiệu bằng'].strip().casefold(), r['Họ, chữ đệm và tên'].strip().casefold(), r['Ngày, tháng, năm sinh'].strip()) for _,r in rows)
for excel_row,r in rows:
    key = (r['Số hiệu bằng'].strip().casefold(),r['Họ, chữ đệm và tên'].strip().casefold(),r['Ngày, tháng, năm sinh'].strip())
    if all(key) and keys[key] > 1:
        errors.append({'Dòng Excel':excel_row,'Cột':'Khóa tra cứu','Vấn đề':'Trùng bộ 3 thông tin tra cứu trong cùng file.'})

c1,c2,c3,c4 = st.columns(4)
c1.metric('Số hồ sơ',len(rows))
c2.metric('STT đã chuẩn hóa',normalized_stt)
c3.metric('Số cảnh báo',len(warnings))
c4.metric('Số lỗi',len(errors))
st.caption('STT số nguyên được chuyển sang chuỗi TEXT trong bộ nhớ; không chỉnh sửa file Excel gốc. Các cột khác không được tự chuyển kiểu số/ngày thành TEXT hợp lệ.')
if warnings:
    st.warning(f'Có {len(warnings)} cảnh báo cần kiểm tra.')
    st.dataframe(warnings, width="stretch", hide_index=True)
if errors:
    st.error(f'Phát hiện {len(errors)} lỗi tại {len({x["Dòng Excel"] for x in errors})} dòng Excel. Chưa đạt yêu cầu kiểm tra.')
    st.dataframe(errors, width="stretch", hide_index=True)
else:
    st.success('Không phát hiện lỗi theo các quy tắc kiểm tra hiện tại.')
st.subheader('Xem trước tối đa 20 hồ sơ (11 cột TEXT)')
st.dataframe([{'Dòng Excel':line, **record} for line,record in rows[:20]], width="stretch", hide_index=True)
st.info('Bước 7 — Đối chiếu trước, xác nhận rõ ràng rồi mới nhập hồ sơ DEMO mới.')

# Chỉ cho phép đối chiếu hồ sơ giả lập trong giai đoạn DEMO.
if errors:
    st.warning('Cần xử lý lỗi Excel trước khi đối chiếu với Supabase.')
    st.stop()
if not rows:
    st.warning('Không có hồ sơ để đối chiếu.')
    st.stop()
if any(not r['Số hiệu bằng'].strip().upper().startswith('DEMO') for _, r in rows):
    st.error('Chỉ được tải dữ liệu DEMO ở giai đoạn này. Không đối chiếu dữ liệu văn bằng thật.')
    st.stop()


def lookup_key(number, name, birthday):
    def norm(s):
        return ' '.join(unicodedata.normalize('NFC', str(s or '')).casefold().split())
    return (norm(number), norm(name), str(birthday or '').strip())


DB_COLUMNS = ['stt', 'so_hieu_bang', 'so_vao_so_goc', 'ho_ten', 'ngay_sinh',
              'gioi_tinh', 'dan_toc', 'noi_sinh', 'ten_truong', 'nien_khoa', 'hoi_dong_thi']


def api_config():
    url = str(st.secrets['SUPABASE_URL']).strip().rstrip('/')
    secret = str(st.secrets['SUPABASE_SECRET_KEY']).strip()
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or not parsed.hostname or
            not parsed.hostname.endswith('.supabase.co') or parsed.path not in ('', '/')):
        raise ValueError('SUPABASE_URL không hợp lệ. Hãy kiểm tra Project URL.')
    if not secret.startswith('sb_secret_'):
        raise ValueError('SUPABASE_SECRET_KEY phải là khóa sb_secret_... của dự án DEMO.')
    return url + '/rest/v1/vbcc', {'apikey': secret, 'Content-Type': 'application/json',
                                   'Accept': 'application/json'}


def fetch_demo_keys():
    endpoint, headers = api_config()
    found = []
    for offset in range(0, 20000, 1000):
        resp = requests.get(endpoint, headers={**headers, 'Range': f'{offset}-{offset+999}',
                         'Range-Unit': 'items'},
                         params={'select': 'so_hieu_bang,ho_ten,ngay_sinh', 'order': 'id.asc'},
                         timeout=(8, 25))
        if resp.status_code not in (200, 206):
            raise RuntimeError(f'Supabase HTTP {resp.status_code} khi đọc dữ liệu.')
        page = resp.json()
        if not isinstance(page, list):
            raise ValueError('Phản hồi Supabase không đúng định dạng.')
        found.extend(page)
        if len(page) < 1000:
            return found
    raise ValueError('Đã vượt giới hạn 20.000 hồ sơ đối chiếu của bản DEMO.')


def excel_to_db(record):
    # All 11 columns are Python str; database columns must all be TEXT.
    return dict(zip(DB_COLUMNS, [record[h] for h in HEADERS]))


def classify(existing):
    existing_keys = {lookup_key(r.get('so_hieu_bang'), r.get('ho_ten'), r.get('ngay_sinh'))
                     for r in existing}
    new, output = [], []
    for line, rec in rows:
        key = lookup_key(rec['Số hiệu bằng'], rec['Họ, chữ đệm và tên'], rec['Ngày, tháng, năm sinh'])
        is_duplicate = key in existing_keys
        if not is_duplicate:
            new.append(excel_to_db(rec))
        output.append({'Dòng Excel': line, 'Số hiệu bằng': rec['Số hiệu bằng'],
                       'Họ, chữ đệm và tên': rec['Họ, chữ đệm và tên'],
                       'Ngày, tháng, năm sinh': rec['Ngày, tháng, năm sinh'],
                       'Kết quả': 'Đã có — bỏ qua' if is_duplicate else 'Mới — có thể nhập'})
    return new, output


def insert_demo(new_records):
    """Requires UNIQUE(so_hieu_bang, ho_ten, ngay_sinh) on public.vbcc."""
    endpoint, headers = api_config()
    inserted = 0
    for i in range(0, len(new_records), 100):
        batch = new_records[i:i+100]
        response = requests.post(
            endpoint, headers={**headers, 'Prefer': 'resolution=ignore-duplicates,return=representation'},
            params={'on_conflict': 'so_hieu_bang,ho_ten,ngay_sinh'},
            json=batch, timeout=(8, 30))
        if response.status_code not in (200, 201):
            raise RuntimeError(f'Supabase HTTP {response.status_code} khi nhập. '
                               'Kiểm tra UNIQUE index trên 3 cột hoặc quyền API.')
        result = response.json()
        if not isinstance(result, list):
            raise RuntimeError('Supabase không trả danh sách kết quả nhập.')
        inserted += len(result)
    return inserted



def write_import_log(file_name, total_records, inserted_records, skipped_records, status):
    """Append a server-side audit record; never expose Supabase credentials."""
    endpoint, headers = api_config()
    log_endpoint = endpoint.rsplit('/', 1)[0] + '/vbcc_import_log'
    payload = {
        'imported_by': admin_username,
        'file_name': str(file_name)[:255],
        'total_records': int(total_records),
        'inserted_records': int(inserted_records),
        'skipped_records': int(skipped_records),
        'status': status,
    }
    response = requests.post(log_endpoint, headers={**headers, 'Prefer': 'return=minimal'},
                             json=payload, timeout=(8, 25))
    if response.status_code not in (200, 201, 204):
        raise RuntimeError(f'Ghi nhật ký Supabase thất bại (HTTP {response.status_code}).')

st.subheader('Bước 7 — Đối chiếu và nhập DEMO có xác nhận')
st.caption('Không xóa, không ghi đè. Bỏ qua trùng theo số hiệu bằng + họ tên + ngày sinh.')
file_fingerprint = hashlib.sha256(up.getvalue()).hexdigest()
if st.session_state.get('vbcc_file') != file_fingerprint:
    st.session_state.vbcc_file = file_fingerprint
    st.session_state.vbcc_compared = False
    st.session_state.vbcc_inserted = False

if st.button('1. Đối chiếu hồ sơ DEMO với Supabase', type='primary'):
    st.session_state.vbcc_compared = False
    try:
        with st.spinner('Đang đối chiếu...'):
            existing = fetch_demo_keys()
            new, output = classify(existing)
        st.session_state.vbcc_compared = True
        st.session_state.vbcc_total = len(existing)
        st.session_state.vbcc_new = new
        st.session_state.vbcc_output = output
        st.session_state.vbcc_inserted = False
    except (KeyError, FileNotFoundError):
        st.error('Thiếu SUPABASE_URL hoặc SUPABASE_SECRET_KEY trong Secrets của vbcc-admin.')
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        logging.error('VBCC Supabase comparison: %s', type(exc).__name__)
        st.error(f'Không đối chiếu được: {exc if isinstance(exc, (RuntimeError, ValueError)) else "Lỗi mạng/SSL/DNS hoặc hết thời gian chờ."}')
    except Exception as exc:
        logging.error('VBCC comparison unexpected: %s', type(exc).__name__)
        st.error('Lỗi xử lý đối chiếu. Không có dữ liệu nào được ghi.')

if st.session_state.get('vbcc_compared'):
    new = st.session_state.vbcc_new
    total = st.session_state.vbcc_total
    a, b, c = st.columns(3)
    a.metric('Hồ sơ đang có', total)
    b.metric('Hồ sơ trùng — bỏ qua', len(rows) - len(new))
    c.metric('Hồ sơ mới', len(new))
    st.dataframe(st.session_state.vbcc_output, width='stretch', hide_index=True)
    if not new:
        st.success('Không có hồ sơ mới. Không cần nhập; dữ liệu Supabase không thay đổi.')
    elif st.session_state.get('vbcc_inserted'):
        st.success('Đã thực hiện nhập. Nhấn Đối chiếu lại để xem dữ liệu mới nhất.')
    else:
        st.warning('CHỈ DỮ LIỆU DEMO. Trước khi nhập phải tạo UNIQUE index theo hướng dẫn.')
        confirmed = st.checkbox(f'Tôi xác nhận chỉ nhập {len(new)} hồ sơ DEMO mới, '
                                'bỏ qua hồ sơ trùng; không ghi đè hoặc xóa dữ liệu.',
                                key='vbcc_confirm_insert')
        if st.button('2. Xác nhận và nhập hồ sơ DEMO mới', disabled=not confirmed):
            try:
                with st.spinner('Đang kiểm tra lại và nhập hồ sơ DEMO...'):
                    # Re-read immediately before write to reduce stale comparison.
                    latest = fetch_demo_keys()
                    fresh, _ = classify(latest)
                    if len(fresh) > 1000:
                        raise ValueError('Bản DEMO giới hạn 1.000 hồ sơ mới/lần.')
                    inserted = insert_demo(fresh) if fresh else 0
                st.session_state.vbcc_inserted = True
                st.success(f'Đã thêm {inserted} hồ sơ DEMO; bỏ qua {len(rows)-inserted} hồ sơ '
                           '(trùng hoặc đã có). Không ghi đè hoặc xóa dữ liệu.')
                logging.info('VBCC DEMO import: excel_rows=%d, inserted=%d', len(rows), inserted)
                try:
                    write_import_log(up.name, len(rows), inserted, len(rows)-inserted, 'completed')
                    st.success('Đã ghi nhật ký nhập dữ liệu vào bảng vbcc_import_log.')
                except Exception as audit_exc:
                    logging.error('VBCC import audit failed: %s', type(audit_exc).__name__)
                    st.error('Hồ sơ DEMO đã được nhập, nhưng GHI NHẬT KÝ THẤT BẠI. '
                             'Không nhấn nhập lại; kiểm tra quyền INSERT của bảng vbcc_import_log và Logs.')
            except (KeyError, FileNotFoundError):
                st.error('Thiếu cấu hình Supabase trong Secrets.')
            except (requests.RequestException, RuntimeError, ValueError) as exc:
                logging.error('VBCC DEMO import: %s', type(exc).__name__)
                st.error(f'Nhập chưa hoàn tất: {exc if isinstance(exc, (RuntimeError, ValueError)) else "Lỗi kết nối mạng."} '
                         'Có thể một phần đã được nhập; hãy nhấn Đối chiếu lại trước khi thử tiếp.')
            except Exception as exc:
                logging.error('VBCC DEMO import unexpected: %s', type(exc).__name__)
                st.error('Lỗi khi nhập. Hãy đối chiếu lại để kiểm tra trạng thái.')
