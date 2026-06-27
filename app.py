
# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime

DATABASE = 'tabungan.db'

def db_connect():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

app = Flask(__name__, template_folder='template')

def create_table():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tabungan(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipe TEXT NOT NULL CHECK(tipe IN ('pemasukan', 'pengeluaran')),
            jumlah REAL NOT NULL,
            keterangan TEXT,
            tanggal DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS catatan(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            konten TEXT,
            tanggal DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS target_tabungan(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            nominal_target REAL NOT NULL,
            terkumpul REAL DEFAULT 0,
            tanggal DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# ============================================================
# ROUTE HALAMAN HTML
# ============================================================

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

# ============================================================
# API TRANSAKSI (SUDAH ADA - TIDAK DIUBAH)
# ============================================================

@app.route('/api/transaksi', methods=['POST'])
def transaksi():
    try:
        data = request.get_json(silent=True) or {}
        tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tipe = data.get('tipe')
        jumlah = data.get('jumlah')
        keterangan = data.get('keterangan')
        
        if jumlah is None:
            return jsonify({'status':'error', 'message':'Jumlah harus diisi'}), 400
        try:
            jumlah = float(jumlah)
        except (ValueError, TypeError):
            return jsonify({'status':'error', 'message':'Jumlah harus berupa angka'}), 400
            
        if jumlah <= 0:
            return jsonify({'status':'error', 'message':'Jumlah harus lebih besar dari 0'}) , 400
        if tipe not in ['pemasukan','pengeluaran']:
            return jsonify({'status':'error', 'message':'Transaksi gagal ditambahkan'}) , 400
        if not keterangan or str(keterangan).strip() == '':
            return jsonify({'status':'error', 'message':'Silahkan isi keterangan terlebih dahulu'}) , 400
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO tabungan (tanggal, tipe, jumlah, keterangan) VALUES (?,?,?,?)
        """,(tanggal, tipe, jumlah, keterangan))
        conn.commit()
        conn.close()
        return jsonify({'status':'success', 'message':'Transaksi berhasil ditambahkan'}), 200
    except Exception as e:
        return jsonify({'status':'error', 'message':str(e)}), 500

@app.route('/api/riwayat', methods=['GET'])
def riwayat():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('SELECT * FROM tabungan ORDER BY tanggal DESC')
    data = cur.fetchall()
    conn.close()
    return jsonify([dict(row) for row in data])

@app.route('/api/saldo', methods=['GET'])
def saldo():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('SELECT (SELECT IFNULL(SUM(jumlah), 0) FROM tabungan WHERE tipe = "pemasukan") - (SELECT IFNULL(SUM(jumlah), 0) FROM tabungan WHERE tipe = "pengeluaran")')
    data = cur.fetchone()[0]
    conn.close()
    return jsonify({'saldo': data})

@app.route('/api/delete', methods=['DELETE'])
def delete():
    try:
        conn = db_connect()
        cur = conn.cursor()
        cur.execute('DELETE FROM tabungan')
        conn.commit()
        conn.close()
        return jsonify({'status':'success', 'message':'Transaksi berhasil direset'}), 200
    except Exception as e:
        return jsonify({'status':'error', 'message':str(e)})

@app.route('/api/catatan', methods=['GET'])
def get_catatan():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('SELECT * FROM catatan WHERE id = 1')
    data = cur.fetchone()
    conn.close()
    if data is None: return jsonify({'konten': ''})
    return jsonify(dict(data))

@app.route('/api/catatan', methods=['POST'])
def update_catatan():
    try:
        id = 1
        data = request.get_json(silent=True) or {}
        tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        konten = data.get('konten', '')
        conn = db_connect()
        cur = conn.cursor()
        cur.execute('SELECT * FROM catatan WHERE id = ?', (id,))
        catatan_ada = cur.fetchone()
        if catatan_ada is None:
            cur.execute("""
                INSERT INTO catatan (id, konten, tanggal) VALUES (?,?,?)
            """, (id, konten, tanggal))
        else:
            cur.execute("""
                UPDATE catatan SET konten = ?, tanggal = CURRENT_TIMESTAMP WHERE id = ?
            """, (konten, id))
        conn.commit()
        conn.close()
        return jsonify({'status':'success', 'message':'Catatan berhasil diupdate'}), 200
    except Exception as e:
        return jsonify({'status':'error', 'message':str(e)})

# ============================================================
# API BARU: RINGKASAN, ANALITIK, TARGET TABUNGAN
# ============================================================

@app.route('/api/ringkasan', methods=['GET'])
def ringkasan():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('SELECT IFNULL(SUM(jumlah), 0) FROM tabungan WHERE tipe = "pemasukan"')
    total_masuk = cur.fetchone()[0]
    cur.execute('SELECT IFNULL(SUM(jumlah), 0) FROM tabungan WHERE tipe = "pengeluaran"')
    total_keluar = cur.fetchone()[0]
    conn.close()
    return jsonify({
        'total_masuk': total_masuk,
        'total_keluar': total_keluar,
        'saldo': total_masuk - total_keluar
    })

@app.route('/api/analitik', methods=['GET'])
def analitik():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT keterangan, SUM(jumlah) as total
        FROM tabungan
        WHERE tipe = 'pengeluaran'
        GROUP BY keterangan
        ORDER BY total DESC
    """)
    data = cur.fetchall()
    conn.close()

    hasil = []
    grand_total = sum(row['total'] for row in data)
    for row in data:
        persen = (row['total'] / grand_total * 100) if grand_total > 0 else 0
        hasil.append({
            'kategori': row['keterangan'],
            'total': row['total'],
            'persentase': round(persen, 1)
        })
    return jsonify(hasil)

@app.route('/api/target', methods=['GET'])
def get_target():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('SELECT * FROM target_tabungan ORDER BY tanggal DESC')
    data = cur.fetchall()
    conn.close()
    return jsonify([dict(row) for row in data])

@app.route('/api/target', methods=['POST'])
def add_target():
    try:
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

        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO target_tabungan (nama, nominal_target) VALUES (?, ?)
        """, (nama, nominal_target))
        conn.commit()
        conn.close()
        return jsonify({'status':'success', 'message':'Target berhasil ditambahkan'}), 200
    except Exception as e:
        return jsonify({'status':'error', 'message':str(e)}), 500

@app.route('/api/target/<int:target_id>/tambah', methods=['POST'])
def tambah_dana_target(target_id):
    try:
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

        conn = db_connect()
        cur = conn.cursor()
        cur.execute('SELECT * FROM target_tabungan WHERE id = ?', (target_id,))
        target = cur.fetchone()
        if target is None:
            conn.close()
            return jsonify({'status':'error', 'message':'Target tidak ditemukan'}), 404

        new_terkumpul = target['terkumpul'] + jumlah
        cur.execute('UPDATE target_tabungan SET terkumpul = ? WHERE id = ?', (new_terkumpul, target_id))
        conn.commit()
        conn.close()
        return jsonify({'status':'success', 'message':'Dana berhasil ditambahkan ke target'}), 200
    except Exception as e:
        return jsonify({'status':'error', 'message':str(e)}), 500

@app.route('/api/target/<int:target_id>', methods=['DELETE'])
def delete_target(target_id):
    try:
        conn = db_connect()
        cur = conn.cursor()
        cur.execute('DELETE FROM target_tabungan WHERE id = ?', (target_id,))
        conn.commit()
        conn.close()
        return jsonify({'status':'success', 'message':'Target berhasil dihapus'}), 200
    except Exception as e:
        return jsonify({'status':'error', 'message':str(e)}), 500


if __name__ == "__main__":
    create_table()
    app.run(host="0.0.0.0", port=5000, debug=True)