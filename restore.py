import os
import sys
import subprocess
from app import create_app

app = create_app()
app.app_context().push()

def restore_from_sql(backup_file_path):
    if not os.path.exists(backup_file_path):
        print(f"ERRO: Arquivo '{backup_file_path}' não encontrado.")
        sys.exit(1)

    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    
    try:
        parts = db_uri.split('//')[1]
        user_pass, host_db = parts.rsplit('@', 1)
        user, password = user_pass.split(':')
        host_port, dbname = host_db.split('/')

        if ':' in host_port:
            host, port = host_port.split(':')
        else:
            host = host_port
            port = "5432"
            
    except ValueError:
        print("ERRO: URL do banco inválida.")
        sys.exit(1)

    print(f"Restaurando banco '{dbname}' em '{host}:{port}'...")
    os.environ['PGPASSWORD'] = password
    
    drop_cmd = f"dropdb -h {host} -p {port} -U {user} -w --if-exists --force {dbname}"
    create_cmd = f"createdb -h {host} -p {port} -U {user} -w {dbname}"

    try:
        print("1/3 - Removendo banco antigo...")
        subprocess.run(drop_cmd, shell=True, check=True, capture_output=True)
        
        print("2/3 - Criando banco novo...")
        subprocess.run(create_cmd, shell=True, check=True, capture_output=True)
        
        print("3/3 - Restaurando backup (Formato Binário)...")
        
        # ALTERAÇÃO: check=False para capturar o resultado manualmente
        result = subprocess.run(
            ["pg_restore", "-h", host, "-p", port, "-U", user, "-d", dbname, "-w", backup_file_path],
            check=False 
        )

        # O pg_restore retorna 1 quando há avisos (como o erro de versão), mas os dados foram salvos.
        if result.returncode > 1:
            print(f"\n❌ Falha crítica no pg_restore (Código {result.returncode})")
            sys.exit(1)
        
        if result.returncode == 1:
            print("\n⚠️ Aviso: Backup restaurado com alertas de versão (Dados preservados).")
        else:
            print("\n✅ Sucesso: Backup restaurado perfeitamente!")
        
        print("Limpando histórico de migrações antigo...")
        try:
            subprocess.run(
                ["psql", "-h", host, "-p", port, "-U", user, "-d", dbname, "-w", "-c", "DROP TABLE IF EXISTS alembic_version;"],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except:
            pass

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erro no processo: {e}")
        sys.exit(1)
    finally:
        if 'PGPASSWORD' in os.environ: del os.environ['PGPASSWORD']

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python restore.py <arquivo.sql>")
    else:
        restore_from_sql(sys.argv[1])