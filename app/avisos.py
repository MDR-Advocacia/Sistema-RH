from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import or_
from . import db
from .models import Aviso, Setor, AvisoAnexo, LogCienciaAviso, Usuario

avisos_bp = Blueprint('avisos', __name__, url_prefix='/avisos')

# Grupos de Acesso
# Ajuste conforme os nomes reais no seu AD ou Tabela Permissao
GRUPOS_DIRETORIA = ['diretoria', 'G_Intranet_Diretoria', 'admin_master']
GRUPOS_GESTAO = ['admin_ti', 'admin_rh', 'G_Intranet_TI', 'G_Intranet_RH_DP', 'supervisor_ti', 'supervisor_rh'] # TI e RH entram aqui
GRUPOS_SUPERVISAO = ['supervisor', 'G_Intranet_Supervisores']

def get_nivel_acesso():
    """
    Define o perfil do usuário para lógica de avisos.
    Retorna: 'DIRETORIA', 'GESTAO', 'SUPERVISOR' ou 'COLABORADOR'
    """
    if current_user.tem_permissao(GRUPOS_DIRETORIA):
        return 'DIRETORIA' 
    
    # Verifica permissão explícita OU combinação de Cargo + Setor
    is_supervisor = current_user.tem_permissao(['supervisor', 'G_Intranet_Supervisores'])
    is_ti_rh = False
    
    if current_user.funcionario and current_user.funcionario.setor:
        setor_nome = current_user.funcionario.setor.nome.upper()
        # Lista de palavras-chave para identificar setores de Gestão
        if any(s in setor_nome for s in ['TI', 'TECNOLOGIA', 'RH', 'RECURSOS HUMANOS', 'PESSOAL']):
            is_ti_rh = True

    if current_user.tem_permissao(GRUPOS_GESTAO) or (is_supervisor and is_ti_rh):
        return 'GESTAO' 
    
    if is_supervisor:
        return 'SUPERVISOR' 
    
    return 'COLABORADOR'

@avisos_bp.route('/')
@login_required
def listar_avisos():
    nivel = get_nivel_acesso()
    
    query = Aviso.query.filter_by(arquivado=False)
    filtros = []
    
    # 1. Avisos Gerais (Todos veem)
    filtros.append(Aviso.publico_geral == True)
    
    # 2. Mural da Diretoria (Apenas Diretores veem)
    if nivel == 'DIRETORIA':
        filtros.append(Aviso.target_diretoria == True)
    
    # 3. Mural de Supervisores (Diretores, Gestão e Supervisores veem)
    if nivel in ['DIRETORIA', 'GESTAO', 'SUPERVISOR']:
        filtros.append(Aviso.target_supervisores == True)
        
    # 4. Avisos Setorizados (Se eu sou do setor X, vejo avisos para X)
    if current_user.funcionario and current_user.funcionario.setor_id:
        meu_setor_id = current_user.funcionario.setor_id
        filtros.append(Aviso.setores_alvo.any(Setor.id == meu_setor_id))
    
    # 5. Meus Próprios Avisos (Sempre vejo o que criei)
    filtros.append(Aviso.autor_id == current_user.id)

    query = query.filter(or_(*filtros))
    
    # Ordenação: Diretoria > Supervisores > Geral > Data
    avisos = query.order_by(
        Aviso.target_diretoria.desc(),
        Aviso.target_supervisores.desc(),
        Aviso.data_publicacao.desc()
    ).all()
    
    return render_template('avisos/listar_avisos.html', avisos=avisos, nivel_acesso=nivel)

@avisos_bp.route('/criar', methods=['GET', 'POST'])
@login_required
def criar_aviso():
    nivel = get_nivel_acesso()
    
    if nivel == 'COLABORADOR':
        flash('Sem permissão para publicar avisos.', 'danger')
        return redirect(url_for('avisos.listar_avisos'))

    if request.method == 'POST':
        titulo = request.form.get('titulo')
        conteudo = request.form.get('conteudo')
        
        # Flags do Formulário
        publico_geral = request.form.get('publico_geral') == 'on'
        target_diretoria = request.form.get('target_diretoria') == 'on'
        target_supervisores = request.form.get('target_supervisores') == 'on'
        setores_ids = request.form.getlist('setores')

        # --- REGRAS DE NEGÓCIO (BACKEND) ---
        # Impede que níveis inferiores postem onde não devem, mesmo se manipularem o HTML
        
        if nivel == 'SUPERVISOR':
            # Supervisor comum SÓ posta no setor dele
            publico_geral = False
            target_diretoria = False
            target_supervisores = False 
            # Força apenas o setor dele
            if current_user.funcionario and current_user.funcionario.setor_id:
                setores_ids = [str(current_user.funcionario.setor_id)]
        
        elif nivel == 'GESTAO':
            # TI/RH não posta no mural exclusivo da Diretoria
            target_diretoria = False

        # Correção do Erro: Usando os campos corretos do model atualizado
        novo_aviso = Aviso(
            titulo=titulo,
            conteudo=conteudo,
            autor_id=current_user.id,
            publico_geral=publico_geral,
            target_diretoria=target_diretoria,       # Novo campo
            target_supervisores=target_supervisores, # Novo campo
            data_publicacao=datetime.utcnow()
        )

        if setores_ids:
            for sid in setores_ids:
                setor = db.session.get(Setor, int(sid))
                if setor: novo_aviso.setores_alvo.append(setor)

        db.session.add(novo_aviso)
        db.session.commit()
        
        flash('Aviso publicado com sucesso!', 'success')
        return redirect(url_for('avisos.listar_avisos'))

    # Preparação para o Template (GET)
    todos_setores = Setor.query.order_by(Setor.nome).all()
    setores_visiveis = todos_setores
    
    # Se for supervisor comum, só vê o próprio setor na lista
    if nivel == 'SUPERVISOR' and current_user.funcionario and current_user.funcionario.setor_id:
        setores_visiveis = [s for s in todos_setores if s.id == current_user.funcionario.setor_id]

    return render_template('avisos/criar_aviso.html', setores=setores_visiveis, nivel_acesso=nivel)

@avisos_bp.route('/<int:aviso_id>/arquivar', methods=['POST'])
@login_required
def arquivar_aviso(aviso_id):
    aviso = Aviso.query.get_or_404(aviso_id)
    nivel = get_nivel_acesso()
    
    # Autor, Diretoria ou Gestão (TI/RH) podem arquivar
    if aviso.autor_id == current_user.id or nivel in ['DIRETORIA', 'GESTAO']:
        aviso.arquivado = True
        db.session.commit()
        flash('Aviso arquivado.', 'success')
    else:
        flash('Sem permissão.', 'danger')
        
    return redirect(url_for('avisos.listar_avisos'))