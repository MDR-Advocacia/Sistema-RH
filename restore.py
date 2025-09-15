import os
import sys
import subprocess
from app import create_app

# Carrega a configuração da aplicação para obter os detalhes do banco de dados
app = create_app()
app.app_context().push()

def restore_from_sql(backup_file_path):
    """
    Restaura o banco de dados a partir de um arquivo de backup .sql.
    Esta é uma operação destrutiva que apaga o banco atual primeiro.
    """
    if not os.path.exists(backup_file_path):
        print(f"ERRO: O arquivo de backup '{backup_file_path}' não foi encontrado.")
        sys.exit(1)

    # Pega as variáveis de conexão do ambiente, exatamente como o app faz
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    
    # Extrai os detalhes da URI de conexão
    try:
        # Formato: postgresql://user:password@host:port/dbname
        parts = db_uri.split('//')[1]
        user_pass, host_db = parts.split('@')
        user, password = user_pass.split(':')
        host, dbname = host_db.split('/')
    except ValueError:
        print("ERRO: Formato inválido para a DATABASE_URL. Não foi possível extrair os detalhes de conexão.")
        sys.exit(1)

    print(f"Iniciando a restauração do banco de dados '{dbname}' a partir do arquivo '{backup_file_path}'...")
    print("AVISO: Todos os dados atuais no banco de dados serão apagados e substituídos.")

    # Define a senha para o comando psql
    os.environ['PGPASSWORD'] = password
    
    # Comandos para dropar o banco existente e criar um novo
    # Isso garante uma restauração limpa
    drop_command = f"dropdb -h {host} -U {user} -w --if-exists {dbname}"
    create_command = f"createdb -h {host} -U {user} -w {dbname}"
    # Comando para restaurar o backup
    restore_command = f"psql -h {host} -U {user} -d {dbname} -w < {backup_file_path}"

    try:
        # Executa os comandos
        print("1/3 - Removendo banco de dados antigo...")
        subprocess.run(drop_command, shell=True, check=True, capture_output=True, text=True)
        
        print("2/3 - Criando banco de dados novo...")
        subprocess.run(create_command, shell=True, check=True, capture_output=True, text=True)
        
        print("3/3 - Restaurando dados do backup...")
        # Usamos Popen para lidar com o redirecionamento de entrada '<'
        with open(backup_file_path, 'r') as f:
            proc = subprocess.Popen(
                ["psql", "-h", host, "-U", user, "-d", dbname, "-w"],
                stdin=f,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                raise Exception(f"Erro no psql: {stderr.decode('utf-8')}")

        print("\nBanco de dados restaurado com sucesso!")
    
    except subprocess.CalledProcessError as e:
        print("\n--- ERRO DURANTE A RESTAURAÇÃO ---")
        print(f"Comando que falhou: {e.cmd}")
        print(f"Saída de erro:\n{e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"\n--- UM ERRO INESPERADO OCORREU ---")
        print(str(e))
        sys.exit(1)
    finally:
        # Remove a senha da variável de ambiente por segurança
        if 'PGPASSWORD' in os.environ:
            del os.environ['PGPASSWORD']

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python restore.py <caminho_para_o_arquivo_de_backup.sql>")
        sys.exit(1)
    
    backup_file = sys.argv[1]
    restore_from_sql(backup_file)