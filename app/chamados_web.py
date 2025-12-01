import os
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, current_app, send_file, jsonify, abort
)
from flask_login import login_required, current_user
from datetime import datetime
from werkzeug.utils import secure_filename
from sqlalchemy import or_

from . import db
from .models import ChamadoTI, CategoriaTI, Ativo, ChamadoComentario, Usuario, ChamadoAnexo, Setor
from .decorators import permission_required
from .utils import registrar_log

chamados_web_bp = Blueprint('chamados_web', __name__, url_prefix='/chamados')

# --- LOGICA DE ACESSO (PERMISSÃO + SETOR) ---
def is_equipe_ti():
    """
    Verifica se o usuário tem acesso técnico aos chamados.
    Critério: Ter permissão explícita OU estar lotado no setor de TI.
    """
    # 1. Verifica Permissões de Sistema (Admins/Supervisores)
    if current_user.tem_permissao(['admin_ti', 'supervisor_ti', 'tecnico_ti']):
        return True
    
    # 2. Verifica Setor (Membros da OU TI)
    if current_user.funcionario and current_user.funcionario.setor:
        nome_setor = current_user.funcionario.setor.nome.upper()
        # Palavras-chave que identificam o setor de TI no seu AD
        termos_ti = ['TI', 'TECNOLOGIA', 'SUPORTE', 'INFRAESTRUTURA', 'SISTEMAS']
        if any(termo in nome_setor for termo in termos_ti):
            return True
            
    return False

def verificar_acesso_ti():
    """Atalha o request se não for TI"""
    if not is_equipe_ti():
        flash('Acesso restrito à equipe técnica.', 'danger')
        abort(403)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'txt', 'doc', 'docx', 'xls', 'xlsx'}

def get_upload_path_chamado(chamado_id):
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'chamados', str(chamado_id))
    os.makedirs(path, exist_ok=True)
    return path

# --- ROTAS PRINCIPAIS ---

@chamados_web_bp.route('/abrir', methods=['GET', 'POST'])
@login_required
def abrir_chamado():
    ativo_id = request.args.get('ativo_id', type=int)
    ativo_preenchido = None
    if ativo_id:
        ativo_preenchido = db.session.get(Ativo, ativo_id)

    if request.method == 'POST':
        titulo = request.form.get('titulo')
        conteudo = request.form.get('conteudo')
        categoria_id = request.form.get('categoria_id')
        ativo_input = request.form.get('ativo_id') 

        if not all([titulo, conteudo, categoria_id]):
            flash('Título, Conteúdo e Categoria são obrigatórios.', 'danger')
            return redirect(url_for('.abrir_chamado', ativo_id=ativo_id))
        
        try:
            agora = datetime.now()
            hoje_inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
            hoje_str = agora.strftime('%Y%m%d')
            count_hoje = ChamadoTI.query.filter(ChamadoTI.data_abertura >= hoje_inicio).count()
            seq = count_hoje + 1
            protocolo_gerado = f"{hoje_str}{seq:04d}"

            novo_chamado = ChamadoTI(
                titulo=titulo,
                conteudo=conteudo,
                categoria_ti_id=int(categoria_id),
                solicitante_id=current_user.id,
                status='Aberto',
                protocolo=protocolo_gerado
            )

            if ativo_input and ativo_input.isdigit():
                ativo_encontrado = db.session.get(Ativo, int(ativo_input))
                if ativo_encontrado:
                    novo_chamado.ativo_associado_id = ativo_encontrado.id

            db.session.add(novo_chamado)
            db.session.flush() 
            
            file = request.files.get('arquivo')
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                safe_filename = f"{int(datetime.utcnow().timestamp())}_{filename}"
                upload_path = get_upload_path_chamado(novo_chamado.id)
                caminho_relativo = os.path.join('chamados', str(novo_chamado.id), safe_filename)
                file.save(os.path.join(upload_path, safe_filename))
                novo_anexo = ChamadoAnexo(nome_arquivo_original=filename, path_armazenamento=caminho_relativo, chamado_id=novo_chamado.id)
                db.session.add(novo_anexo)

            db.session.commit()
            registrar_log(f'Abriu o chamado de TI #{novo_chamado.protocolo}: "{titulo}"', current_user.id)
            flash(f'Chamado {novo_chamado.protocolo} aberto com sucesso!', 'success')
            return redirect(url_for('.meus_chamados'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao abrir chamado: {e}")
            flash(f'Erro ao abrir chamado: {e}', 'danger')
    
    categorias = CategoriaTI.query.order_by(CategoriaTI.nome).all()
    setores = Setor.query.order_by(Setor.nome).all() 
    return render_template('chamados/abrir.html', categorias=categorias, setores=setores, ativo_preenchido=ativo_preenchido)

@chamados_web_bp.route('/meus-chamados')
@login_required
def meus_chamados():
    chamados = ChamadoTI.query.filter_by(solicitante_id=current_user.id, arquivado=False).order_by(ChamadoTI.data_abertura.desc()).all()
    return render_template('chamados/meus_chamados.html', chamados=chamados)

@chamados_web_bp.route('/<int:chamado_id>/detalhes', methods=['GET', 'POST'])
@login_required
def detalhes_chamado(chamado_id):
    chamado = ChamadoTI.query.get_or_404(chamado_id)
    
    # Verifica se é TI usando a nova lógica
    is_tecnico = is_equipe_ti()

    if chamado.solicitante_id != current_user.id and not is_tecnico:
        flash('Você não tem permissão para ver este chamado.', 'danger')
        return redirect(url_for('.meus_chamados'))

    if request.method == 'POST':
        comentario_texto = request.form.get('comentario')
        if comentario_texto:
            novo_comentario = ChamadoComentario(
                comentario=comentario_texto, chamado_id=chamado_id, usuario_id=current_user.id
            )
            if chamado.status in ['Pendente', 'Fechado'] and chamado.solicitante_id == current_user.id:
                chamado.status = 'Em Andamento'
                flash('O chamado foi reaberto devido à sua interação.', 'info')
            db.session.add(novo_comentario)
            db.session.commit()
            flash('Comentário adicionado.', 'success')
            return redirect(url_for('.detalhes_chamado', chamado_id=chamado_id))

    comentarios = ChamadoComentario.query.filter_by(chamado_id=chamado_id).order_by(ChamadoComentario.data_comentario.asc()).all()
    
    # Dados para os modais
    categorias = []
    tecnicos = []
    todos_ativos = []
    
    if is_tecnico:
        categorias = CategoriaTI.query.order_by(CategoriaTI.nome).all()
        # Busca técnicos: Agora listamos todos do setor TI + Admins
        # Simplificação: Lista todos os usuários, ou filtra melhor se tiver muitos
        # Idealmente: Filtrar usuários onde is_equipe_ti(u) é True, mas isso é pesado no banco.
        # Mantendo filtro por permissão por enquanto para popular o select:
        from .models import Permissao
        permissoes_ti = ['tecnico_ti', 'supervisor_ti', 'admin_ti']
        tecnicos = Usuario.query.join(Usuario.permissoes).filter(Permissao.nome.in_(permissoes_ti)).distinct().all()
        
        todos_ativos = Ativo.query.order_by(Ativo.nome).limit(500).all()

    return render_template(
        'chamados/detalhes.html', 
        chamado=chamado, 
        comentarios=comentarios,
        categorias=categorias,
        tecnicos=tecnicos,
        todos_ativos=todos_ativos,
        is_tecnico=is_tecnico # Passa para o template
    )

# --- ROTAS DE GESTÃO (AGORA ABERTAS PARA A OU TI) ---

@chamados_web_bp.route('/gestao')
@login_required
def gestao_chamados_react():
    # Substitui o decorator @permission_required pela verificação de setor
    verificar_acesso_ti()
    return render_template('chamados/gestao_react.html')

@chamados_web_bp.route('/<int:chamado_id>/repassar', methods=['POST'])
@login_required
def repassar_chamado(chamado_id):
    verificar_acesso_ti()
    chamado = ChamadoTI.query.get_or_404(chamado_id)
    
    novo_tecnico_id = request.form.get('novo_tecnico_id')
    motivo = request.form.get('motivo_repasse')

    alteracoes = []

    if novo_tecnico_id:
        if novo_tecnico_id == 'nenhum':
            if chamado.tecnico_atribuido:
                alteracoes.append(f"Técnico removido (era {chamado.tecnico_atribuido.funcionario.nome})")
                chamado.tecnico_atribuido_id = None
        elif int(novo_tecnico_id) != (chamado.tecnico_atribuido_id or 0):
            tec_novo = Usuario.query.get(int(novo_tecnico_id))
            chamado.tecnico_atribuido_id = tec_novo.id
            alteracoes.append(f"Técnico alterado para: {tec_novo.funcionario.nome}")

    if alteracoes:
        texto_comentario = f"🔄 **Repasse de Chamado**\n" + "\n".join(alteracoes)
        if motivo:
            texto_comentario += f"\nMotivo: {motivo}"
            
        log_sistema = ChamadoComentario(comentario=texto_comentario, chamado_id=chamado.id, usuario_id=current_user.id)
        db.session.add(log_sistema)
        db.session.commit()
        registrar_log(f'Repassou chamado #{chamado.protocolo}', current_user.id)
        flash('Chamado repassado com sucesso.', 'success')
    else:
        flash('Nenhuma alteração realizada.', 'info')

    return redirect(url_for('.detalhes_chamado', chamado_id=chamado_id))

@chamados_web_bp.route('/<int:chamado_id>/atualizar_info', methods=['POST'])
@login_required
def atualizar_info_chamado(chamado_id):
    verificar_acesso_ti()
    chamado = ChamadoTI.query.get_or_404(chamado_id)
    
    nova_categoria_id = request.form.get('categoria_id')
    novo_ativo_nome = request.form.get('ativo_nome') 
    
    alteracoes = []

    if nova_categoria_id and int(nova_categoria_id) != chamado.categoria_ti_id:
        cat_nova = CategoriaTI.query.get(int(nova_categoria_id))
        if cat_nova:
            chamado.categoria_ti_id = cat_nova.id
            alteracoes.append(f"Categoria alterada para: {cat_nova.nome}")

    if novo_ativo_nome:
        ativo_existente = Ativo.query.filter(
            or_(Ativo.nome.ilike(novo_ativo_nome), Ativo.tag_patrimonio.ilike(novo_ativo_nome))
        ).first()

        if ativo_existente:
            if chamado.ativo_associado_id != ativo_existente.id:
                chamado.ativo_associado_id = ativo_existente.id
                alteracoes.append(f"Ativo vinculado: {ativo_existente.nome}")
        else:
            novo_ativo = Ativo(
                nome=novo_ativo_nome,
                tag_patrimonio=f"MANUAL-{int(datetime.utcnow().timestamp())}", 
                tipo="Outro",
                status="Em Uso"
            )
            db.session.add(novo_ativo)
            db.session.flush() 
            chamado.ativo_associado_id = novo_ativo.id
            alteracoes.append(f"Novo ativo criado e vinculado: {novo_ativo_nome}")

    elif 'ativo_nome' in request.form and not novo_ativo_nome:
        if chamado.ativo_associado_id:
            chamado.ativo_associado_id = None
            alteracoes.append("Ativo desvinculado.")

    if alteracoes:
        texto_comentario = f"📝 **Atualização de Cadastro**\n" + "\n".join(alteracoes)
        log_sistema = ChamadoComentario(comentario=texto_comentario, chamado_id=chamado.id, usuario_id=current_user.id)
        db.session.add(log_sistema)
        db.session.commit()
        flash('Informações atualizadas com sucesso.', 'success')
    
    return redirect(url_for('.detalhes_chamado', chamado_id=chamado_id))

@chamados_web_bp.route('/<int:chamado_id>/assumir', methods=['POST'])
@login_required
def assumir_chamado_web(chamado_id):
    verificar_acesso_ti()
    chamado = ChamadoTI.query.get_or_404(chamado_id)
    chamado.tecnico_atribuido_id = current_user.id
    if chamado.status == 'Aberto':
        chamado.status = 'Em Andamento'
    db.session.commit()
    registrar_log(f'Assumiu o chamado #{chamado.protocolo}', current_user.id)
    flash('Você assumiu este chamado.', 'success')
    return redirect(url_for('.detalhes_chamado', chamado_id=chamado_id))

@chamados_web_bp.route('/<int:chamado_id>/status', methods=['POST'])
@login_required
def mudar_status_web(chamado_id):
    verificar_acesso_ti()
    chamado = ChamadoTI.query.get_or_404(chamado_id)
    novo_status = request.form.get('novo_status')
    if novo_status in ['Aberto', 'Em Andamento', 'Pendente', 'Fechado']:
        chamado.status = novo_status
        if novo_status == 'Fechado':
            chamado.data_fechamento = datetime.utcnow()
        db.session.commit()
        registrar_log(f'Alterou status do chamado #{chamado.protocolo} para {novo_status}', current_user.id)
        flash(f'Status alterado para {novo_status}.', 'success')
    else:
        flash('Status inválido.', 'danger')
    return redirect(url_for('.detalhes_chamado', chamado_id=chamado_id))

@chamados_web_bp.route('/<int:chamado_id>/anexar', methods=['POST'])
@login_required
def anexar_arquivo(chamado_id):
    chamado = ChamadoTI.query.get_or_404(chamado_id)
    
    # TI pode anexar em qualquer chamado; Usuário só no dele
    is_tecnico = is_equipe_ti()
    if chamado.solicitante_id != current_user.id and not is_tecnico:
        flash('Sem permissão.', 'danger')
        return redirect(url_for('.meus_chamados'))
        
    file = request.files.get('arquivo')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        safe_filename = f"{int(datetime.utcnow().timestamp())}_{filename}"
        upload_path = get_upload_path_chamado(chamado_id)
        caminho_relativo = os.path.join('chamados', str(chamado_id), safe_filename)
        file.save(os.path.join(upload_path, safe_filename))
        novo_anexo = ChamadoAnexo(nome_arquivo_original=filename, path_armazenamento=caminho_relativo, chamado_id=chamado.id)
        db.session.add(novo_anexo)
        db.session.commit()
        flash('Arquivo anexado com sucesso.', 'success')
    else:
        flash('Arquivo inválido.', 'warning')
    return redirect(url_for('.detalhes_chamado', chamado_id=chamado_id))

@chamados_web_bp.route('/anexo/<int:anexo_id>')
@login_required
def baixar_anexo(anexo_id):
    anexo = ChamadoAnexo.query.get_or_404(anexo_id)
    chamado = ChamadoTI.query.get(anexo.chamado_id)
    is_tecnico = is_equipe_ti()
    
    if chamado.solicitante_id != current_user.id and not is_tecnico:
        return "Acesso negado", 403
    path_completo = os.path.join(current_app.config['UPLOAD_FOLDER'], anexo.path_armazenamento)
    return send_file(path_completo, as_attachment=True, download_name=anexo.nome_arquivo_original)

@chamados_web_bp.route('/<int:chamado_id>/arquivar', methods=['POST'])
@login_required
@permission_required(['admin_ti', 'supervisor_ti']) # Arquivar mantém só pra chefia
def arquivar_chamado(chamado_id):
    chamado = ChamadoTI.query.get_or_404(chamado_id)
    chamado.arquivado = True
    db.session.commit()
    registrar_log(f'Arquivou o chamado #{chamado.protocolo}', current_user.id)
    flash('Chamado arquivado com sucesso.', 'warning')
    return redirect(url_for('.gestao_chamados_react'))

@chamados_web_bp.route('/api/ativos/setor/<int:setor_id>')
@login_required
def get_ativos_por_setor(setor_id):
    ativos = Ativo.query.filter_by(setor_id=setor_id).order_by(Ativo.nome).all()
    return jsonify([{'id': a.id, 'nome': a.nome, 'patrimonio': a.tag_patrimonio} for a in ativos])

@chamados_web_bp.route('/categorias', methods=['GET', 'POST'])
@login_required
@permission_required(['admin_ti', 'supervisor_ti']) # Gestão de Categorias mantém restrito
def gerenciar_categorias():
    if request.method == 'POST':
        nome_categoria = request.form.get('nome')
        if nome_categoria:
            if CategoriaTI.query.filter_by(nome=nome_categoria).first():
                flash(f'A categoria "{nome_categoria}" já existe.', 'warning')
            else:
                nova_cat = CategoriaTI(nome=nome_categoria)
                db.session.add(nova_cat)
                db.session.commit()
                registrar_log(f'Criou a categoria de TI: "{nome_categoria}"', current_user.id)
                flash('Categoria criada com sucesso!', 'success')
        return redirect(url_for('.gerenciar_categorias'))
    categorias = CategoriaTI.query.order_by(CategoriaTI.nome).all()
    return render_template('chamados/categorias.html', categorias=categorias)

@chamados_web_bp.route('/categorias/<int:id>/excluir', methods=['POST'])
@login_required
@permission_required(['admin_ti', 'supervisor_ti'])
def excluir_categoria(id):
    categoria = CategoriaTI.query.get_or_404(id)
    if categoria.chamados:
        flash('Não é possível excluir pois há chamados vinculados.', 'danger')
    else:
        db.session.delete(categoria)
        db.session.commit()
        registrar_log(f'Excluiu a categoria de TI: "{categoria.nome}"', current_user.id)
        flash('Categoria excluída.', 'success')
    return redirect(url_for('.gerenciar_categorias'))

@chamados_web_bp.route('/relatorios')
@login_required
@permission_required(['admin_ti', 'supervisor_ti'])
def relatorios():
    return render_template('chamados/relatorios.html')