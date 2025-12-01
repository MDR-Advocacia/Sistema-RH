# app/chamados_api.py
from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from datetime import datetime

from . import db
from .models import ChamadoTI, ChamadoComentario, Usuario

chamados_api_bp = Blueprint('chamados_api', __name__, url_prefix='/api/chamados')

def is_equipe_ti():
    """Duplicação da lógica para evitar circular import complexo"""
    if current_user.tem_permissao(['admin_ti', 'supervisor_ti', 'tecnico_ti']):
        return True
    if current_user.funcionario and current_user.funcionario.setor:
        nome = current_user.funcionario.setor.nome.upper()
        if any(t in nome for t in ['TI', 'TECNOLOGIA', 'SUPORTE', 'INFRA']):
            return True
    return False

def verificar_api_ti():
    if not is_equipe_ti():
        abort(403, description="Acesso restrito à TI")

def serialize_chamado(chamado):
    """Converte um objeto ChamadoTI em um dicionário para JSON."""
    return {
        'id': chamado.id,
        'protocolo': chamado.protocolo, # ADICIONADO AQUI
        'titulo': chamado.titulo,
        'status': chamado.status,
        'prioridade': chamado.prioridade,
        'data_abertura': chamado.data_abertura.isoformat(),
        'solicitante': {
            'id': chamado.solicitante.id,
            'nome': chamado.solicitante.funcionario.nome if chamado.solicitante.funcionario else 'Usuário Desconhecido'
        },
        'tecnico_atribuido': {
            'id': chamado.tecnico_atribuido.id,
            'nome': chamado.tecnico_atribuido.funcionario.nome if chamado.tecnico_atribuido.funcionario else 'N/A'
        } if chamado.tecnico_atribuido else None,
        'categoria': chamado.categoria.nome if chamado.categoria else 'N/A'
    }

@chamados_api_bp.route('/gestao')
@login_required
def get_chamados_gestao():
    """ Retorna todos os chamados não fechados para o dashboard React. """
    verificar_api_ti() 
    
    agora = datetime.utcnow()
    inicio_hoje = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    
    chamados = ChamadoTI.query.filter(
        (ChamadoTI.status != 'Fechado') | (ChamadoTI.data_fechamento >= inicio_hoje)
    ).order_by(ChamadoTI.data_abertura.desc()).all()
    
    return jsonify([serialize_chamado(c) for c in chamados])

@chamados_api_bp.route('/<int:chamado_id>/atribuir', methods=['POST'])
@login_required
def atribuir_chamado(chamado_id):
    verificar_api_ti()
    chamado = ChamadoTI.query.get_or_404(chamado_id)
    data = request.json
    tecnico_id = data.get('tecnico_id', current_user.id)

    tecnico = Usuario.query.get(tecnico_id)
    if not tecnico:
        return jsonify({'erro': 'Usuário inválido.'}), 400
    
    chamado.tecnico_atribuido_id = tecnico_id
    if chamado.status == 'Aberto':
        chamado.status = 'Em Andamento'
        
    db.session.commit()
    return jsonify({'sucesso': True, 'tecnico_atribuido': tecnico.funcionario.nome})

@chamados_api_bp.route('/<int:chamado_id>/status', methods=['POST'])
@login_required
def mudar_status_chamado(chamado_id):
    verificar_api_ti()
    chamado = ChamadoTI.query.get_or_404(chamado_id)
    data = request.json
    novo_status = data.get('status')

    if novo_status not in ['Aberto', 'Em Andamento', 'Pendente', 'Fechado']:
        return jsonify({'erro': 'Status inválido.'}), 400

    chamado.status = novo_status
    if novo_status == 'Fechado':
        chamado.data_fechamento = datetime.utcnow()

    db.session.commit()
    return jsonify({'sucesso': True, 'novo_status': novo_status})