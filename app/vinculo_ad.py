from flask import Blueprint, render_template, flash, redirect, request, url_for, jsonify, current_app
from flask_login import login_required
# --- IMPORTAÇÃO CORRIGIDA ---
# Adicionei Ponto, Documento, e LogAtividade que são necessários para a função unificar_contas
from .models import db, Funcionario, Usuario, VinculoADSugestao, Ponto, Documento, LogAtividade
from .ad_sync import get_ad_connection
from .utils import normalizar_nome, registrar_log
from thefuzz import fuzz
from .decorators import permission_required

vinculo_bp = Blueprint('vinculo_ad', __name__)

@vinculo_bp.route('/revisao', methods=['GET'])
@login_required
@permission_required(['admin_ti'])
def revisao_vinculos():
    sugestoes = VinculoADSugestao.query.order_by(VinculoADSugestao.pontuacao.desc()).all()
    
    # NOVO: Busca todos os funcionários que têm uma conta de usuário
    # Vamos usar esta lista para preencher os dropdowns de unificação.
    funcionarios_com_usuario = Funcionario.query.join(Usuario).order_by(Funcionario.nome).all()
    
    return render_template(
        'vinculo_ad/revisao.html', 
        sugestoes=sugestoes, 
        funcionarios=funcionarios_com_usuario # NOVO: Passa a lista para o template
    )

@vinculo_bp.route('/executar-analise', methods=['POST'])
@login_required
@permission_required(['admin_ti'])
def executar_analise():
    try:
        VinculoADSugestao.query.delete()
        
        # --- LÓGICA ALTERADA ---
        # Agora buscamos funcionários que JÁ POSSUEM um usuário, para poder corrigir o vínculo.
        funcionarios_com_usuario = Funcionario.query.join(Usuario).all()
        
        conn = get_ad_connection()
        if not conn:
            flash("Não foi possível conectar ao Active Directory.", "danger")
            return redirect(url_for('vinculo_ad.revisao_vinculos'))
        
        # Busca todos os usuários do AD de uma vez para otimizar
        conn.search(
            search_base=current_app.config['LDAP_BASE_DN'],
            search_filter='(&(objectClass=user)(sAMAccountName=*))',
            attributes=['sAMAccountName', 'displayName']
        )
        usuarios_ad = conn.entries
        conn.unbind()

        contagem_sugestoes = 0
        for func in funcionarios_com_usuario:
            # Pula a análise se o username já parece estar vinculado corretamente
            if func.usuario and func.usuario.username:
                if any(u.sAMAccountName.value.lower() == func.usuario.username.lower() for u in usuarios_ad):
                    continue

            match, pontuacao = encontrar_melhor_correspondencia(func.nome, usuarios_ad)
            
            # Gera sugestões para revisão manual (limiar de 80% de similaridade)
            if pontuacao >= 80 and match:
                nova_sugestao = VinculoADSugestao(
                    funcionario_id=func.id,
                    funcionario_nome=func.nome,
                    ad_username=match.sAMAccountName.value,
                    ad_display_name=match.displayName.value,
                    pontuacao=pontuacao
                )
                db.session.add(nova_sugestao)
                contagem_sugestoes += 1
        
        db.session.commit()
        flash(f"Análise concluída! {contagem_sugestoes} sugestões de vínculo foram geradas para revisão.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Ocorreu um erro durante a análise: {str(e)}", "danger")

    return redirect(url_for('vinculo_ad.revisao_vinculos'))

@vinculo_bp.route('/api/vinculo/confirmar/<int:sugestao_id>', methods=['POST'])
@login_required
@permission_required(['admin_ti'])
def confirmar_vinculo(sugestao_id):
    sugestao = VinculoADSugestao.query.get_or_404(sugestao_id)
    
    # --- LÓGICA ALTERADA ---
    # Em vez de criar um novo usuário, atualizamos o existente.
    usuario_para_atualizar = Usuario.query.filter_by(funcionario_id=sugestao.funcionario_id).first()

    if not usuario_para_atualizar:
        return jsonify({'success': False, 'message': 'Erro: Usuário associado ao funcionário não foi encontrado.'})

    # Atualiza o username com o sAMAccountName do AD
    usuario_para_atualizar.username = sugestao.ad_username
    
    db.session.delete(sugestao)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Vínculo confirmado e usuário atualizado com sucesso!'})

@vinculo_bp.route('/api/vinculo/rejeitar/<int:sugestao_id>', methods=['POST'])
@login_required
@permission_required(['admin_ti'])
def rejeitar_vinculo(sugestao_id):
    sugestao = VinculoADSugestao.query.get_or_404(sugestao_id)
    db.session.delete(sugestao)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Sugestão rejeitada.'})

def encontrar_melhor_correspondencia(nome_funcionario, lista_usuarios_ad):
    """Função auxiliar para encontrar a melhor correspondência por similaridade de nome."""
    nome_norm_func = normalizar_nome(nome_funcionario)
    melhor_pontuacao = 0
    melhor_match = None

    for usuario_ad in lista_usuarios_ad:
        if 'displayName' not in usuario_ad.entry_attributes_as_dict or not usuario_ad.displayName.value:
            continue
            
        nome_ad = usuario_ad.displayName.value
        nome_norm_ad = normalizar_nome(nome_ad)
        
        pontuacao = fuzz.token_sort_ratio(nome_norm_func, nome_norm_ad)
        
        if pontuacao > melhor_pontuacao:
            melhor_pontuacao = pontuacao
            melhor_match = usuario_ad
            
    return melhor_match, melhor_pontuacao


@vinculo_bp.route('/unificar-contas', methods=['POST'])
@login_required
@permission_required(['admin_ti']) # Permissão corrigida
def unificar_contas():
    """
    Unifica duas contas de funcionário duplicadas.
    FLUXO CORRETO E DEFINITIVO (Baseado no app/models.py):
    - Mantém a conta "Correta" (a nova, do AD).
    - Move todos os dados e histórico da conta "Duplicada" (a antiga, manual) PARA a conta do AD.
    - Apaga a conta "Duplicada" (a antiga, manual).
    """
    
    id_antigo_remover = request.form.get('id_duplicado')
    id_novo_manter = request.form.get('id_correto')

    if not id_antigo_remover or not id_novo_manter:
        flash('São necessárias ambas as contas (a antiga e a nova).', 'danger')
        return redirect(url_for('vinculo_ad.revisao_vinculos'))

    if id_antigo_remover == id_novo_manter:
        flash('As contas devem ser diferentes.', 'danger')
        return redirect(url_for('vinculo_ad.revisao_vinculos'))

    try:
        # 1. Obter os objectos
        func_antigo = Funcionario.query.get(id_antigo_remover)
        func_novo_ad = Funcionario.query.get(id_novo_manter)
        user_antigo = func_antigo.usuario
        user_novo_ad = func_novo_ad.usuario

        if not all([func_antigo, func_novo_ad, user_antigo, user_novo_ad]):
            msg = f"Erro: Uma das contas de funcionário ou utilizador não foi encontrada."
            flash(msg, 'danger')
            return redirect(url_for('vinculo_ad.revisao_vinculos'))

        # --- LÓGICA DE UNIFICAÇÃO CORRIGIDA ---

        # 2. Copiar dados de RH (da conta antiga para a nova)
        
        # Primeiro, guardar os dados da conta antiga em variáveis
        cpf_antigo = func_antigo.cpf
        data_nascimento_antiga = func_antigo.data_nascimento
        cargo_antigo = func_antigo.cargo 
        setor_antigo = func_antigo.setor 
        status_antigo = func_antigo.status
        data_desligamento_antiga = func_antigo.data_desligamento
        email_antigo = func_antigo.email
        telefone_antigo = func_antigo.telefone

        ctt_emerg_antigo = func_antigo.contato_emergencia_nome 
        nmr_emerg_antigo = func_antigo.contato_emergencia_telefone 
        
        # --- CORREÇÃO (NotNullViolation E UniqueViolation no CPF) ---
        # 1. Libertar o CPF da conta antiga (func_antigo),
        #    atribuindo um valor temporário e único (ex: "temp_19").
        func_antigo.cpf = f"temp_{func_antigo.id}" 
        
        # 2. Forçar a BD a executar este UPDATE (libertar o CPF) imediatamente
        db.session.flush()

        # 3. Agora que o CPF real está livre, 
        #    atribuir todos os dados antigos à nova conta
        func_novo_ad.cpf = cpf_antigo
        func_novo_ad.data_nascimento = data_nascimento_antiga
        func_novo_ad.email = email_antigo
        func_novo_ad.cargo = cargo_antigo
        func_novo_ad.setor = setor_antigo
        func_novo_ad.status = status_antigo
        func_novo_ad.data_desligamento = data_desligamento_antiga
        func_novo_ad.telefone = telefone_antigo
        func_novo_ad.contato_emergencia_nome = ctt_emerg_antigo
        func_novo_ad.contato_emergencia_telefone = nmr_emerg_antigo
        
        # 3. Copiar dados de UTILIZADOR (da conta antiga para a nova)
        # (Apenas campos que existem em app/models.py e migrações)
        # REMOVIDOS 'is_admin' e 'is_depto_pessoal' PORQUE NÃO EXISTEM
        
        # 4. Mover dependências (Pontos, Documentos, Logs, Permissões)
        db.session.query(Ponto).filter(
            Ponto.funcionario_id == func_antigo.id
        ).update({'funcionario_id': func_novo_ad.id})
        
        db.session.query(Documento).filter(
            Documento.funcionario_id == func_antigo.id
        ).update({'funcionario_id': func_novo_ad.id})
        
        db.session.query(LogAtividade).filter(
            LogAtividade.usuario_id == user_antigo.id
        ).update({'usuario_id': user_novo_ad.id})
        
        db.session.query(Ponto).filter(
            Ponto.solicitante_id == user_antigo.id
        ).update({'solicitante_id': user_novo_ad.id})
        
        db.session.query(Ponto).filter(
            Ponto.revisor_id == user_antigo.id
        ).update({'revisor_id': user_novo_ad.id})

        # 5. Transferir Permissões
        # (Isto é o que transfere 'admin', 'depto_pessoal', etc.)
        for perm in user_antigo.permissoes:
            if perm not in user_novo_ad.permissoes:
                user_novo_ad.permissoes.append(perm)
        
        # 6. Apagar os registos antigos (ordem inversa)
        db.session.delete(user_antigo)
        db.session.delete(func_antigo)
        
        # 7. Commit
        db.session.commit()

        # 8. Log
        log_msg = f"Unificou a conta antiga '{func_antigo.nome}' (FuncID: {func_antigo.id}) na conta AD '{func_novo_ad.nome}' (FuncID: {func_novo_ad.id}). A conta antiga foi removida."
        registrar_log(log_msg)
        
        flash(f"Contas unificadas com sucesso! Os dados de '{func_antigo.nome}' foram movidos para '{func_novo_ad.nome}'.", 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao unificar contas: {e}")
        flash(f'Erro ao unificar contas: {str(e)}', 'danger')
    
    return redirect(url_for('vinculo_ad.revisao_vinculos'))