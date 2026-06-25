
# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime

DATABASE = 'tabungan.db'

def db_connect():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

app = Flask(__name__)

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
            tanggal DATETIME DEFAULT CURRENT_TIMESTAMP,
        )
    """)
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/api/transaksi', methods=['POST'])
def transaksi():
    try:
        data = request.get_json()
        tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tipe = data.get('tipe')
        jumlah = data.get('jumlah')
        keterangan = data.get('keterangan')
        
        if jumlah <= 0:
            return jsonify({'status':'error', 'message':'Jumlah harus lebih besar dari 0'}) , 400
        if tipe not in ['pemasukan','pengeluaran']:
            return jsonify({'status':'error', 'message':'Transaksi gagal ditambahkan'}) , 400
        if keterangan == '':
            return jsonify({'status':'error', 'message':'Silahkan isi keterangan terlebih dahulu'}) , 400
        conn = db_connect()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO tabungan (tanggal, tipe, jumlah, keterangan) VALUES (?,?,?)
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
    cur.execute('SELECT SUM(jumlah) WHERE tipe = "pemasukan" - SUM(jumlah) WHERE tipe = "pengeluaran"  FROM tabungan')
    data = cur.fetchone()
    conn.close()
    return jsonify({'saldo': data})

@app.route('/api/delete', methods=['DELETE'])
def delete():
    try:
        data = request.get_json()
        conn = db_connect()
        cur = conn.cursor()
        cur.execute('DELETE transaksi FROM tabungan')
        conn.commit()
        conn.close()
        return jsonify({'status':'success', 'message':'Transaksi berhasil direset'}), 200
    except Exception as e:
        return jsonify({'status':'error', 'message':str(e)})

@app.route('/api/catatan', methods=['POST'])
def catatan():
    try:
        data = request.get_json()
        tanggal = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        konten = data.get('konten')
        conn = db_connect()
        cur = conn.cursor()
        cur.execute('SELECT id FROM catatan WHERE id = ?', (id,))
        catatan_ada = cur.fetchone()
        
        if catatan_ada is None:
            cur.execute("""
                INSERT INTO catatan (id) VALUES (?)
            """)
        else:
            cur.execute("""
                UPDATE catatan WHERE id = ?
            """, (id))
        conn.commit()
        conn.close()
        return jsonify({'status':'success', 'message':'Catatan berhasil ditambahkan'}), 200
    except Exception as e:
        return jsonify({'status':'error', 'message':str(e)})


if __name__ == "__main__":
    create_table()
    app.run(debug=True)