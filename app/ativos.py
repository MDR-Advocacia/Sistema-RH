from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import or_
from . import db
from .models import Ativo, Emprestimo, Funcionario, Usuario
from .decorators import permission_required
from .utils import registrar_log

ativos_bp = Blueprint('ativos', __name__, url_prefix='/ativos')

PERMISSOES_TI = ['admin_ti', 'supervisor_ti', 'tecnico_ti']

@ativos_bp.route('/')
@login_required
@permission_required(PERMISSOES_TI)
def listar_ativos():
    """Listagem geral do inventário (CMDB)."""
    q = request.args.get('q', '').strip()
    query = Ativo.query

    if q:
        query = query.filter(
            or_(
                Ativo.nome.ilike(f"%{q}%"),
                Ativo.hostname.ilike(f"%{q}%"),
                Ativo.tag_patrimonio.ilike(f"%{q}%")
            )
        )
    
    # Ordena por status (Em Uso primeiro) e depois nome
    ativos = query.order_by(Ativo.status.asc(), Ativo.nome.asc()).all()
    
    return render_template('ativos/listar.html', ativos=ativos)

# --- GESTÃO DE CAUTELA (EMPRÉSTIMOS) ---

@ativos_bp.route('/cautela', methods=['GET'])
@login_required
@permission_required(PERMISSOES_TI)
def gestao_cautela():
    """Dashboard de Empréstimos Ativos e Histórico."""
    
    # Empréstimos "Em Aberto" (Ativo não devolvido)
    emprestimos_ativos = Emprestimo.query.filter_by(status='Ativo')\
        .join(Funcionario).order_by(Emprestimo.data_emprestimo.desc()).all()
    
    # Histórico recente (últimos 20 devolvidos)
    historico_devolucoes = Emprestimo.query.filter_by(status='Devolvido')\
        .order_by(Emprestimo.data_devolucao_real.desc()).limit(20).all()

    # Dados para os modais (Ativos disponíveis e Funcionários)
    # Apenas ativos que NÃO estão em um empréstimo Ativo
    ids_em_uso = db.session.query(Emprestimo.ativo_id).filter(Emprestimo.status == 'Ativo')
    ativos_disponiveis = Ativo.query.filter(Ativo.id.notin_(ids_em_uso)).filter(Ativo.status != 'Baixado').order_by(Ativo.nome).all()
    
    funcionarios = Funcionario.query.filter_by(status='Ativo').order_by(Funcionario.nome).all()

    return render_template(
        'ativos/cautela.html',
        emprestimos_ativos=emprestimos_ativos,
        historico=historico_devolucoes,
        ativos_disponiveis=ativos_disponiveis,
        funcionarios=funcionarios
    )

@ativos_bp.route('/cautela/novo', methods=['POST'])
@login_required
@permission_required(PERMISSOES_TI)
def novo_emprestimo():
    """Registra a saída (Check-out) de um equipamento."""
    ativo_id = request.form.get('ativo_id')
    funcionario_id = request.form.get('funcionario_id')
    data_prevista = request.form.get('data_prevista_devolucao')

    if not all([ativo_id, funcionario_id]):
        flash('Selecione o Ativo e o Funcionário.', 'danger')
        return redirect(url_for('ativos.gestao_cautela'))

    ativo = Ativo.query.get(ativo_id)
    funcionario = Funcionario.query.get(funcionario_id)

    # Validação extra: O ativo já está emprestado?
    if Emprestimo.query.filter_by(ativo_id=ativo.id, status='Ativo').first():
        flash(f'O ativo {ativo.nome} já consta como emprestado!', 'warning')
        return redirect(url_for('ativos.gestao_cautela'))

    novo_cautela = Emprestimo(
        ativo_id=ativo.id,
        funcionario_id=funcionario.id,
        tecnico_responsavel_id=current_user.id,
        data_emprestimo=datetime.utcnow(),
        status='Ativo'
    )

    if data_prevista:
        novo_cautela.data_prevista_devolucao = datetime.strptime(data_prevista, '%Y-%m-%d').date()

    # Atualiza status do ativo
    ativo.status = 'Empréstimo'
    
    # Se o ativo não tinha setor, atribui temporariamente o setor do funcionário
    if not ativo.setor_id and funcionario.setor_id:
        ativo.setor_id = funcionario.setor_id

    db.session.add(novo_cautela)
    db.session.commit()
    
    registrar_log(f"Realizou empréstimo do ativo '{ativo.tag_patrimonio or ativo.nome}' para '{funcionario.nome}'.", current_user.id)
    flash('Empréstimo registrado com sucesso!', 'success')

    return redirect(url_for('ativos.gestao_cautela'))

@ativos_bp.route('/cautela/<int:emprestimo_id>/devolver', methods=['POST'])
@login_required
@permission_required(PERMISSOES_TI)
def devolver_emprestimo(emprestimo_id):
    """Registra a entrada (Check-in) de um equipamento."""
    emprestimo = Emprestimo.query.get_or_404(emprestimo_id)
    
    if emprestimo.status == 'Devolvido':
        flash('Este empréstimo já foi baixado.', 'info')
        return redirect(url_for('ativos.gestao_cautela'))

    emprestimo.status = 'Devolvido'
    emprestimo.data_devolucao_real = datetime.utcnow()
    
    # Libera o ativo
    ativo = emprestimo.ativo
    ativo.status = 'Disponível' # Ou volta para "Em Uso" dependendo da sua regra de negócio

    db.session.commit()
    
    registrar_log(f"Recebeu devolução do ativo '{ativo.tag_patrimonio or ativo.nome}' de '{emprestimo.funcionario.nome}'.", current_user.id)
    flash('Devolução registrada com sucesso. Ativo liberado.', 'success')

    return redirect(url_for('ativos.gestao_cautela'))