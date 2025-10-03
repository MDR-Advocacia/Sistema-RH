from flask import Blueprint, render_template, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required
from .models import db, Funcionario, Usuario, VinculoADSugestao
from .ad_sync import get_ad_connection
from .utils import normalizar_nome
from thefuzz import fuzz
from .decorators import permission_required

vinculo_bp = Blueprint('vinculo_ad', __name__)

@vinculo_bp.route('/revisao', methods=['GET'])
@login_required
@permission_required(['admin_ti'])
def revisao_vinculos():
    sugestoes = VinculoADSugestao.query.order_by(VinculoADSugestao.pontuacao.desc()).all()
    return render_template('vinculo_ad/revisao.html', sugestoes=sugestoes)

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