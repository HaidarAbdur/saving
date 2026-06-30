import os
# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, jsonify
# pyrefly: ignore [missing-import]
from supabase import create_client
from datetime import datetime
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
from functools import wraps
# pyrefly: ignore [missing-import]
from postgrest.exceptions import APIError

load_dotenv(dotenv_path="/home/haidar/dokumen/tabunganbaru/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "").strip()
SUPABASE_KEY = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SECRET_KEY

def handle_db_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIError as e:
            return jsonify({
                'status': 'error',
                'message': f"Supabase Error: {e.message}"
            }), 500
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f"Server Error: {str(e)}"
            }), 500
    return decorated_function

def is_placeholder(value):
    if not value:
        return True
    lowered = value.strip().lower()
    return lowered in {"", "your_key_here", "your_service_role_key", "your_url_here", "changeme", "placeholder", "xxxxx", "https://xxxxxx.supabase.co"}

if is_placeholder(SUPABASE_URL) or is_placeholder(SUPABASE_KEY):
    raise RuntimeError("Supabase environment variables belum diisi dengan nilai asli. Periksa file .env atau variabel Vercel.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__, template_folder='template')

def supabase_table(name):
    return supabase.table(name)

def to_dict_list(result):
    return [dict(row) for row in result.data or []]

# HALAMAN HTML

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/pemasukan")
def halaman_pemasukan():
    return render_template("pemasukan.html")

@app.route("/pengeluaran")
def halaman_pengeluaran():
    return render_template("pengeluaran.html")

@app.route("/catatan")
def halaman_catatan():
    return render_template("catatan.html")

@app.route("/target")
def halaman_target():
    return render_template("target.html")

@app.route("/riwayat")
def halaman_riwayat():
    return render_template("riwayat.html")

# API ENDPOINTS

@app.route('/api/transaksi', methods=['POST'])
@handle_db_errors
def transaksi():
    data = request.get_json(silent=True) or {}
    tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    tipe = data.get('tipe')
    jumlah = data.get('jumlah')
    keterangan = data.get('keterangan')
    
    if jumlah is None:
        return jsonify({'status':'error', 'message':'Jumlah harus diisi'}), 400
    try:
        jumlah = int(jumlah)
    except (ValueError, TypeError):
        return jsonify({'status':'error', 'message':'Jumlah harus berupa angka'}), 400
        
    if jumlah <= 0:
        return jsonify({'status':'error', 'message':'Jumlah harus lebih besar dari 0'}) , 400
    if tipe not in ['pemasukan','pengeluaran']:
        return jsonify({'status':'error', 'message':'Transaksi gagal ditambahkan'}) , 400
    if not keterangan or str(keterangan).strip() == '':
        return jsonify({'status':'error', 'message':'Silahkan isi keterangan terlebih dahulu'}) , 400

    result = supabase_table('tabungan').insert({
        'tipe': tipe,
        'jumlah': jumlah,
        'keterangan': keterangan
    }).execute()

    return jsonify({'status':'success', 'message':'Transaksi berhasil ditambahkan'}), 201

@app.route('/api/riwayat', methods=['GET'])
@handle_db_errors
def riwayat():
    result = supabase_table('tabungan').select('*').order('tanggal', desc=True).execute()
    return jsonify(to_dict_list(result))

@app.route('/api/saldo', methods=['GET'])
@handle_db_errors
def saldo():
    result_masuk = supabase_table('tabungan').select('jumlah', count='exact').eq('tipe', 'pemasukan').execute()
    result_keluar = supabase_table('tabungan').select('jumlah', count='exact').eq('tipe', 'pengeluaran').execute()
    total_masuk = sum(row['jumlah']for row in result_masuk.data or [])
    total_keluar = sum(row['jumlah']for row in result_keluar.data or [])
    return jsonify({'saldo': total_masuk - total_keluar})

@app.route('/api/delete', methods=['DELETE'])
@handle_db_errors
def delete():
    supabase_table('tabungan').delete().gt('id', 0).execute()
    return jsonify({'status': 'success', 'message': 'Semua transaksi berhasil direset'}), 201

@app.route('/api/catatan', methods=['GET'])
@handle_db_errors
def get_catatan():
    result = supabase_table('catatan').select('*').eq('id', 1).execute()
    catatan = result.data[0] if result.data else {'id': 1, 'konten': '', 'tanggal': ''}
    return jsonify(catatan)

@app.route('/api/catatan', methods=['POST'])
@handle_db_errors
def update_catatan():
    data = request.get_json(silent=True) or {}
    konten = data.get('konten', '')
    tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    result = supabase_table('catatan').select('*').eq('id', 1).execute()
    if result.data:
        supabase_table('catatan').update({
            'konten': konten,
            'tanggal': tanggal
        }).eq('id', 1).execute()
    else:
        supabase_table('catatan').insert({
            'id': 1,
            'konten': konten,
            'tanggal': tanggal
        }).execute()
    return jsonify({'status': 'success', 'message': 'Catatan berhasil diperbarui'}), 201

# API BARU: RINGKASAN, ANALITIK, TARGET TABUNGAN

@app.route('/api/ringkasan', methods=['GET'])
@handle_db_errors
def ringkasan():
    result_masuk = supabase_table('tabungan').select('jumlah', count='exact').eq('tipe', 'pemasukan').execute()
    result_keluar = supabase_table('tabungan').select('jumlah', count='exact').eq('tipe', 'pengeluaran').execute()
    total_masuk = sum(row['jumlah'] for row in result_masuk.data or [])
    total_keluar = sum(row['jumlah'] for row in result_keluar.data or [])
    saldo = total_masuk - total_keluar
    return jsonify({
        'total_masuk': total_masuk,
        'total_keluar': total_keluar,
        'saldo': saldo,
        'total_pemasukan': total_masuk,
        'total_pengeluaran': total_keluar
    })

@app.route('/api/analitik', methods=['GET'])
@handle_db_errors
def analitik():
    result = supabase_table('tabungan').select('*').eq('tipe', 'pengeluaran').execute()
    kategori_map = {}
    for row in result.data or []:
        keterangan = row.get('keterangan') or 'Lainnya'
        jumlah = float(row.get('jumlah', 0) or 0)
        kategori_map[keterangan] = kategori_map.get(keterangan, 0) + jumlah
    grand_total = sum(kategori_map.values())
    hasil = []
    for kategori, total in sorted(kategori_map.items(), key=lambda item: item[1], reverse=True):
        persen = round((total / grand_total * 100) if grand_total > 0 else 0, 1)
        hasil.append({
            'kategori': kategori,
            'total': total,
            'persentase': persen
        })
    return jsonify(hasil)

@app.route('/api/target', methods=['GET'])
@handle_db_errors
def get_target():
    result = supabase_table('target_tabungan').select('*').execute()
    return jsonify([dict(row) for row in result.data])

@app.route('/api/target', methods=['POST'])
@handle_db_errors
def add_target():
    data = request.get_json(silent=True) or {}
    nama = data.get('nama', '').strip()
    nominal_target = data.get('nominal_target')

    if not nama:
        return jsonify({'status':'error', 'message':'Nama target harus diisi'}), 400
    if nominal_target is None:
        return jsonify({'status':'error', 'message':'Nominal target harus diisi'}), 400
    try:
        nominal_target = float(nominal_target)
    except (ValueError, TypeError):
        return jsonify({'status':'error', 'message':'Nominal harus berupa angka'}), 400
    if nominal_target <= 0:
        return jsonify({'status':'error', 'message':'Nominal target harus lebih dari 0'}), 400

    supabase_table('target_tabungan').insert({
        'nama': nama,
        'nominal_target': nominal_target
    }).execute()
    return jsonify({'status':'success', 'message':'Target berhasil ditambahkan'}), 201

@app.route('/api/target/<int:target_id>/tambah', methods=['POST'])
@handle_db_errors
def tambah_dana_target(target_id):
    data = request.get_json(silent=True) or {}
    jumlah = data.get('jumlah')

    if jumlah is None:
        return jsonify({'status':'error', 'message':'Jumlah harus diisi'}), 400
    try:
        jumlah = float(jumlah)
    except (ValueError, TypeError):
        return jsonify({'status':'error', 'message':'Jumlah harus berupa angka'}), 400
    if jumlah <= 0:
        return jsonify({'status':'error', 'message':'Jumlah harus lebih dari 0'}), 400

    result = supabase_table('target_tabungan').select('*').eq('id', target_id).execute()
    target = result.data[0] if result.data else None
    if target is None:
        return jsonify({'status':'error', 'message':'Target tidak ditemukan'}), 404

    new_terkumpul = (float(target.get('terkumpul') or 0)) + jumlah
    supabase_table('target_tabungan').update({'terkumpul': new_terkumpul}).eq('id', target_id).execute()
    return jsonify({'status':'success', 'message':'Dana berhasil ditambahkan ke target'}), 201

@app.route('/api/target/<int:target_id>', methods=['DELETE'])
@handle_db_errors
def delete_target(target_id):
    supabase_table('target_tabungan').delete().eq('id', target_id).execute()
    return jsonify({'status':'success','message':'Target berhasil dihapus'}), 201

@app.route('/api/analitik/bulanan', methods=['GET'])
@handle_db_errors
def analitik_bulanan():
    result = supabase_table('tabungan').select('*').execute()
    data_bulanan = {}
    
    for row in result.data or []:
        tanggal_str = row.get('tanggal', '')
        if not tanggal_str: continue
        
        # Ekstrak tahun dan bulan
        try:
            tanggal = datetime.fromisoformat(tanggal_str.replace('Z', '+00:00'))
            bulan_str = tanggal.strftime('%Y-%m') # Format: 2024-06
            nama_bulan = tanggal.strftime('%B') # Format: June
        except:
            try:
                tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d %H:%M:%S')
                bulan_str = tanggal.strftime('%Y-%m')
                nama_bulan = tanggal.strftime('%B')
            except:
                continue
        
        tipe = row.get('tipe')
        jumlah = float(row.get('jumlah', 0) or 0)
        
        if bulan_str not in data_bulanan:
            data_bulanan[bulan_str] = {
                'bulan': nama_bulan,
                'tahun_bulan': bulan_str,
                'total_pemasukan': 0,
                'total_pengeluaran': 0,
                'saldo': 0
            }
        
        if tipe == 'pemasukan':
            data_bulanan[bulan_str]['total_pemasukan'] += jumlah
        elif tipe == 'pengeluaran':
            data_bulanan[bulan_str]['total_pengeluaran'] += jumlah
    
    # Hitung saldo untuk setiap bulan
    for bulan_data in data_bulanan.values():
        bulan_data['saldo'] = bulan_data['total_pemasukan'] - bulan_data['total_pengeluaran']
    
    # Urutkan berdasarkan waktu (bulan terbaru di akhir)
    data_sorted = sorted(data_bulanan.values(), key=lambda x: x['tahun_bulan'])
    
    return jsonify(data_sorted)

if __name__ == "__main__":
    app.run(debug=True)