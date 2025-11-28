from flask import Blueprint, render_template, flash, redirect, request, url_for, current_app
from flask_login import login_required, current_user
from .models import db, Funcionario, Usuario, VinculoADSugestao, Ponto, Documento, LogAtividade, Ativo
from .ad_mirror import sync_ad_to_db_logic, sync_ad_computers_logic
from .ad_sync import get_ad_connection
from .utils import registrar_log
from thefuzz import fuzz
from .decorators import permission_required
from unidecode import unidecode
# Importação da lógica de CSV (Se der erro aqui, verifique se criou o arquivo app/ad_import.py)
from .ad_import import processar_upload_csv_ad

vinculo_bp = Blueprint('vinculo_ad', __name__, url_prefix='/vinculo_ad')

# --- FUNÇÕES AUXILIARES ---
def normalizar_nome(nome):
    """Remove acentos e coloca em minúsculas para comparação."""
    if not nome: return ""
    return unidecode(nome).lower().strip()

def encontrar_melhor_correspondencia(nome_funcionario, lista_usuarios_ad):
    """Encontra a melhor correspondência no AD baseada no nome."""
    nome_norm_func = normalizar_nome(nome_funcionario)
    melhor_pontuacao = 0
    melhor_match = None

    for usuario_ad in lista_usuarios_ad:
        display_name_val = getattr(usuario_ad.displayName, 'value', None)
        if not display_name_val:
            continue
        nome_norm_ad = normalizar_nome(display_name_val)
        pontuacao = fuzz.token_sort_ratio(nome_norm_func, nome_norm_ad)
        if pontuacao > melhor_pontuacao:
            melhor_pontuacao = pontuacao
            melhor_match = usuario_ad
    return melhor_match, melhor_pontuacao

# --- ROTAS ---

@vinculo_bp.route('/revisao', methods=['GET'])
@login_required
@permission_required(['admin_ti', 'supervisor_ti', 'admin_rh'])
def revisao():
    """Dashboard principal de Vínculos."""
    sugestoes = VinculoADSugestao.query.order_by(VinculoADSugestao.pontuacao.desc()).all()
    funcionarios_com_usuario = Funcionario.query.join(Usuario).order_by(Funcionario.nome).all()
    desligados = Funcionario.query.filter(
        Funcionario.status.in_(['Suspenso', 'Desligado (AD)'])
    ).order_by(Funcionario.nome).all()
    
    return render_template(
        'vinculo_ad/revisao.html', 
        sugestoes=sugestoes, 
        funcionarios=funcionarios_com_usuario,
        desligados=desligados
    )

@vinculo_bp.route('/importar_ad', methods=['GET', 'POST'])
@login_required
@permission_required(['admin_ti'])
def importar_dados_ad():
    """
    Rota para Upload de CSV que alimenta o AD.
    """
    logs = []
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo enviado.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado.', 'danger')
            return redirect(request.url)
            
        if file and file.filename.endswith('.csv'):
            try:
                logs = processar_upload_csv_ad(file)
                flash('Processamento concluído. Verifique o log abaixo.', 'success')
            except Exception as e:
                flash(f'Erro ao processar CSV: {str(e)}', 'danger')
        else:
            flash('Por favor, envie um arquivo .csv', 'warning')

    return render_template('vinculo_ad/importar_ad.html', logs=logs)

@vinculo_bp.route('/sincronizar_agora', methods=['POST'])
@login_required
@permission_required(['admin_ti'])
def sincronizar_agora():
    """Força a execução do script de espelhamento do AD."""
    try:
        sync_ad_to_db_logic() # Sync Usuários
        sync_ad_computers_logic() # Sync Computadores
        flash('Sincronização com AD realizada com sucesso!', 'success')
    except Exception as e:
        flash(f'Erro ao sincronizar: {str(e)}', 'danger')
        print(f"Erro Sync Manual: {e}")

    return redirect(url_for('vinculo_ad.revisao'))

@vinculo_bp.route('/executar-analise', methods=['POST'])
@login_required
@permission_required(['admin_ti'])
def executar_analise():
    """Gera sugestões de vínculo baseadas em similaridade de nome."""
    try:
        VinculoADSugestao.query.delete()
        funcionarios_alvo = Funcionario.query.all()
        
        conn = get_ad_connection()
        if not conn:
            flash("Não foi possível conectar ao Active Directory.", "danger")
            return redirect(url_for('vinculo_ad.revisao'))
        
        conn.search(
            search_base=current_app.config['LDAP_BASE_DN'],
            search_filter='(&(objectClass=user)(sAMAccountName=*))',
            attributes=['sAMAccountName', 'displayName']
        )
        usuarios_ad = conn.entries
        
        contagem = 0
        for func in funcionarios_alvo:
            if func.usuario and func.usuario.username:
                username_atual = func.usuario.username.lower()
                if any(u.sAMAccountName.value.lower() == username_atual for u in usuarios_ad if u.sAMAccountName.value):
                    continue

            match, pontuacao = encontrar_melhor_correspondencia(func.nome, usuarios_ad)
            
            if pontuacao >= 80 and match:
                sugestao = VinculoADSugestao(
                    funcionario_id=func.id,
                    funcionario_nome=func.nome,
                    ad_username=match.sAMAccountName.value,
                    ad_display_name=match.displayName.value,
                    pontuacao=pontuacao
                )
                db.session.add(sugestao)
                contagem += 1
        
        db.session.commit()
        flash(f"Análise concluída! {contagem} sugestões geradas.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erro na análise: {str(e)}", "danger")

    return redirect(url_for('vinculo_ad.revisao'))

@vinculo_bp.route('/confirmar/<int:sugestao_id>', methods=['POST'])
@login_required
@permission_required(['admin_ti'])
def confirmar_vinculo(sugestao_id):
    """Aplica o vínculo sugerido."""
    sugestao = VinculoADSugestao.query.get_or_404(sugestao_id)
    funcionario = Funcionario.query.get(sugestao.funcionario_id)

    if not funcionario:
        flash('Funcionário não encontrado.', 'danger')
        return redirect(url_for('vinculo_ad.revisao'))

    if funcionario.usuario:
        funcionario.usuario.username = sugestao.ad_username
        flash(f'Usuário atualizado para {sugestao.ad_username}.', 'success')
    else:
        novo_user = Usuario(
            username=sugestao.ad_username,
            email=funcionario.email,
            funcionario_id=funcionario.id
        )
        novo_user.set_password('Mudar123')
        db.session.add(novo_user)
        flash(f'Usuário criado e vinculado: {sugestao.ad_username}.', 'success')
    
    db.session.delete(sugestao)
    db.session.commit()
    return redirect(url_for('vinculo_ad.revisao'))

@vinculo_bp.route('/rejeitar/<int:sugestao_id>', methods=['POST'])
@login_required
@permission_required(['admin_ti'])
def rejeitar_vinculo(sugestao_id):
    sugestao = VinculoADSugestao.query.get_or_404(sugestao_id)
    db.session.delete(sugestao)
    db.session.commit()
    flash('Sugestão rejeitada.', 'info')
    return redirect(url_for('vinculo_ad.revisao'))

@vinculo_bp.route('/unificar-contas', methods=['POST'])
@login_required
@permission_required(['admin_ti'])
def unificar_contas():
    """
    Unifica duas contas: Apaga a 'Duplicada' e move tudo para a 'Correta'.
    """
    id_duplicado = request.form.get('id_duplicado')
    id_correto = request.form.get('id_correto')

    if not id_duplicado or not id_correto or id_duplicado == id_correto:
        flash('Selecione duas contas diferentes.', 'warning')
        return redirect(url_for('vinculo_ad.revisao'))

    try:
        func_old = Funcionario.query.get(id_duplicado)
        func_new = Funcionario.query.get(id_correto)
        
        if not func_old or not func_new:
            flash('Funcionários não encontrados.', 'danger')
            return redirect(url_for('vinculo_ad.revisao'))

        cpf_temp = f"temp_{func_old.id}_{func_old.cpf[:3]}" if func_old.cpf else f"temp_{func_old.id}"
        func_old.cpf = cpf_temp
        db.session.flush()

        if not func_new.data_nascimento and func_old.data_nascimento:
            func_new.data_nascimento = func_old.data_nascimento
        if not func_new.telefone and func_old.telefone:
            func_new.telefone = func_old.telefone
        
        Ponto.query.filter_by(funcionario_id=func_old.id).update({'funcionario_id': func_new.id})
        Documento.query.filter_by(funcionario_id=func_old.id).update({'funcionario_id': func_new.id})
        
        if func_old.usuario and func_new.usuario:
            LogAtividade.query.filter_by(usuario_id=func_old.usuario.id).update({'usuario_id': func_new.usuario.id})
            for perm in func_old.usuario.permissoes:
                if perm not in func_new.usuario.permissoes:
                    func_new.usuario.permissoes.append(perm)
        
        if func_old.usuario:
            db.session.delete(func_old.usuario)
        db.session.delete(func_old)
        
        db.session.commit()
        
        try:
            registrar_log(f"Unificou conta {func_old.nome} em {func_new.nome}", current_user.id)
        except:
            pass
            
        flash(f'Contas unificadas com sucesso! {func_old.nome} foi removido e seus dados migrados para {func_new.nome}.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao unificar: {str(e)}', 'danger')

    return redirect(url_for('vinculo_ad.revisao'))