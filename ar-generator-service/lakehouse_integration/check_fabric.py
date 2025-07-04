import os, pyodbc

server   = os.getenv("SERVER")
database = os.getenv("DATABASE")
client_id     = os.getenv("CLIENT_ID")      # UID
client_secret = os.getenv("CLIENT_SECRET")  # PWD

print("\n🧾   Parámetros cargados")
print(f"SERVER   : {server}")
print(f"DATABASE : {database}")
print(f"CLIENT_ID: {client_id[:8]}…")

conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={server};"
    f"DATABASE={database};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
    "Authentication=ActiveDirectoryServicePrincipal;"
    f"UID={client_id};"
    f"PWD={client_secret};"
)

print("⌛   Conectando con Service Principal…")
try:
    conn = pyodbc.connect(conn_str, timeout=10)
    print("✅   Conexión establecida.\n")

    cur = conn.cursor()
    cur.execute("""
        SELECT TOP 3 TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE';
    """)
    for s, t in cur.fetchall():
        print(f"- {s}.{t}")

    cur.close()
    conn.close()
except Exception as e:
    print(f"❌  Error:\n{e}")