import os
import uuid
import json
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, send_from_directory, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .email import send_email
from .utils import registrar_log
from . import db
from .decorators import permission_required
from .models import (Funcionario, Documento, RequisicaoDocumento, TipoDocumento, 
                     Solicitacao, SolicitacaoAprovador, Usuario, DocumentoAprovacao, 
                     Setor, Cargo)
from app.forms import TipoDocumentoForm

documentos_bp = Blueprint('documentos', __name__)

# Configurações
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx'}

# Permissões permitidas para GESTÃO de documentos
PERMISSOES_DOCS = ['admin_rh', 'depto_pessoal', 'admin_ti', 'supervisor', 'financeiro', 'diretoria']

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@documentos_bp.route('/gestao', methods=['GET', 'POST'])
@login_required
@permission_required(PERMISSOES_DOCS)
def gestao_documentos():
    """Página unificada para gestão de documentos (Com suporte a React)."""
    
    if request.method == 'POST':
        return solicitar_documento_legado()

    # --- PREPARAÇÃO DE DADOS ---
    
    # 1. Filtros de Hierarquia
    funcionarios_query = Funcionario.query.filter_by(status='Ativo')
    is_global_admin = current_user.tem_permissao(['admin_rh', 'depto_pessoal', 'admin_ti', 'financeiro', 'diretoria'])
    is_supervisor = current_user.tem_permissao('supervisor')

    if not is_global_admin and is_supervisor:
        if current_user.funcionario and current_user.funcionario.setor_id:
            funcionarios_query = funcionarios_query.filter_by(setor_id=current_user.funcionario.setor_id)
        else:
            funcionarios_query = funcionarios_query.filter_by(id=-1) 

    funcionarios = funcionarios_query.order_by(Funcionario.nome).all()
    tipos_documento = TipoDocumento.query.order_by(TipoDocumento.nome).all()
    setores = Setor.query.order_by(Setor.nome).all()
    cargos = Cargo.query.order_by(Cargo.nome).all()
    aprovadores_disponiveis = Usuario.query.join(Funcionario).filter(Funcionario.status=='Ativo').order_by(Funcionario.nome).all()
    
    # 2. Documentos para Revisão (Minhas Pendências de Aprovação)
    # Busca aprovações onde EU sou o aprovador e está pendente
    minhas_aprovacoes = DocumentoAprovacao.query.filter_by(
        aprovador_id=current_user.id, 
        status='Pendente'
    ).all()
    ids_docs_para_mim = [a.documento_id for a in minhas_aprovacoes]

    # FIX DEFINITIVO: Voltamos a usar CLASSE.ATRIBUTO pois o models.py já foi corrigido e possui 'funcionario'.
    # Isso resolve o ArgumentError das strings e o AttributeError pois a relação existe.
    doc_query = Documento.query.options(joinedload(Documento.funcionario).joinedload(Funcionario.setor))
    
    if is_global_admin:
        doc_query = doc_query.filter(or_(
            Documento.id.in_(ids_docs_para_mim),
            Documento.status == 'Pendente de Revisão'
        ))
    else:
        doc_query = doc_query.filter(Documento.id.in_(ids_docs_para_mim))
        
    documentos_revisao = doc_query.order_by(Documento.data_upload.asc()).all()

    # 3. Solicitações para Gestão (Aba "Gestão")
    ids_sol_aprovador = db.session.query(SolicitacaoAprovador.solicitacao_id).filter_by(aprovador_id=current_user.id).all()
    ids_sol_aprovador = [i[0] for i in ids_sol_aprovador]

    # FIX: Usando CLASSE.ATRIBUTO aqui também
    req_query = RequisicaoDocumento.query.options(
        joinedload(RequisicaoDocumento.solicitacao_pai),
        joinedload(RequisicaoDocumento.destinatario),
        joinedload(RequisicaoDocumento.tipo),
        joinedload(RequisicaoDocumento.solicitante).joinedload(Usuario.funcionario)
    ).join(Solicitacao).filter(
        or_(
            Solicitacao.solicitante_id == current_user.id,
            Solicitacao.id.in_(ids_sol_aprovador)
        )
    ).order_by(Solicitacao.data_criacao.desc()).limit(100).all()

    lista_gestao = []
    for req in req_query:
        sou_aprovador = False
        # FIX: Usando CLASSE.ATRIBUTO
        doc_anexado = Documento.query.options(joinedload(Documento.funcionario)).filter_by(requisicao_id=req.id).order_by(Documento.id.desc()).first()
        
        if doc_anexado:
            aprov_pendente = DocumentoAprovacao.query.filter_by(documento_id=doc_anexado.id, aprovador_id=current_user.id, status='Pendente').first()
            if aprov_pendente: sou_aprovador = True
            elif is_global_admin and doc_anexado.status == 'Pendente de Revisão': sou_aprovador = True
        
        solicitante_nome = "Sistema"
        if req.solicitante and req.solicitante.funcionario:
            solicitante_nome = req.solicitante.funcionario.nome
        elif req.solicitacao_pai and req.solicitacao_pai.solicitante and req.solicitacao_pai.solicitante.funcionario:
            solicitante_nome = req.solicitacao_pai.solicitante.funcionario.nome

        lista_gestao.append({
            'id': doc_anexado.id if doc_anexado else 0,
            'req_id': req.id,
            'solicitacao_id': req.solicitacao_id,
            'titulo': req.solicitacao_pai.titulo if req.solicitacao_pai else "Solicitação Avulsa",
            'data_criacao': req.data_requisicao.strftime('%d/%m/%Y'),
            'destinatario_nome': req.destinatario.nome if req.destinatario else "Desconhecido",
            'documento_tipo': req.tipo.nome if req.tipo else "Documento",
            'status': doc_anexado.status if doc_anexado else req.status,
            'prazo': None,
            'solicitante_id': req.solicitante_id,
            'solicitante_nome': solicitante_nome,
            'is_aprovador': sou_aprovador,
            'recorrente': req.solicitacao_pai.recorrente if req.solicitacao_pai else False,
            'url_download': url_for('documentos.download_documento', filename=doc_anexado.path_armazenamento) if doc_anexado else None
        })

    # --- MONTAGEM DA LISTA DE REVISÃO ---
    lista_docs_revisao = []
    for d in documentos_revisao:
        # Acesso seguro
        if d.funcionario:
            f_nome = d.funcionario.nome
            s_nome = d.funcionario.setor.nome if d.funcionario.setor else '-'
        else:
            f_nome = "Funcionário Desconhecido"
            s_nome = "-"

        lista_docs_revisao.append({
            'id': d.id,
            'funcionario_nome': f_nome,
            'setor_nome': s_nome,
            'tipo': d.tipo_documento,
            'data_envio': d.data_upload.strftime('%d/%m/%Y %H:%M'),
            'status': d.status,
            'url_download': url_for('documentos.download_documento', filename=d.path_armazenamento)
        })

    # --- JSON PARA O REACT ---
    initial_data = {
        'funcionarios': [{'id': f.id, 'nome': f.nome, 'setor': f.setor.nome if f.setor else 'N/A'} for f in funcionarios],
        'tipos_documento': [{'id': t.id, 'nome': t.nome} for t in tipos_documento],
        'setores': [{'id': s.id, 'nome': s.nome} for s in setores],
        'cargos': [{'id': c.id, 'nome': c.nome} for c in cargos],
        'aprovadores': [{'id': u.id, 'nome': u.funcionario.nome} for u in aprovadores_disponiveis],
        'documentos_revisao': lista_docs_revisao,
        'solicitacoes_acompanhamento': lista_gestao,
        'usuario_atual': {
            'id': current_user.id,
            'nome': current_user.funcionario.nome if current_user.funcionario else current_user.username,
            'is_admin': is_global_admin
        }
    }

    return render_template(
        'documentos/gestao.html',
        initial_data=initial_data
    )

def solicitar_documento_legado():
    """Extrai lógica legada do POST para manter a função principal limpa."""
    try:
        funcionario_id = request.form.get('funcionario_id')
        tipo_documento = request.form.get('tipo_documento_solicitado')
        
        if not funcionario_id or not tipo_documento:
            flash('Erro: Funcionário e Tipo de Documento são obrigatórios.', 'danger')
            return redirect(url_for('documentos.gestao_documentos'))

        funcionario = db.session.get(Funcionario, int(funcionario_id))
        if not funcionario:
            flash('Erro: Funcionário selecionado não foi encontrado.', 'danger')
            return redirect(url_for('documentos.gestao_documentos'))
        
        tipo_obj = TipoDocumento.query.filter_by(nome=tipo_documento).first()
        tipo_id = tipo_obj.id if tipo_obj else 1
        
        nova_requisicao = RequisicaoDocumento(
            tipo_documento_id=tipo_id,
            solicitante_id=current_user.id,
            destinatario_id=int(funcionario_id),
            status='Pendente'
        )
        db.session.add(nova_requisicao)
        db.session.commit()

        registrar_log(f"Solicitou (Legado) o documento '{tipo_documento}' para '{funcionario.nome}'.")
        flash(f'Solicitação enviada com sucesso para {funcionario.nome}!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao criar requisição (legado): {e}", exc_info=True)
        flash('Ocorreu um erro inesperado.', 'danger')

    return redirect(url_for('documentos.gestao_documentos'))

# --- NOVAS ROTAS API (REACT / WORKFLOW) ---

@documentos_bp.route('/criar-solicitacao', methods=['POST'])
@login_required
@permission_required(PERMISSOES_DOCS)
def criar_solicitacao_complexa():
    data = request.get_json()
    
    titulo = data.get('titulo')
    descricao = data.get('descricao')
    mode = data.get('mode', 'individual') 
    
    # Recorrência
    recorrente = data.get('recorrente', False)
    data_base_str = data.get('data_base')
    intervalo = data.get('intervalo')
    prazo_str = data.get('prazo')

    ids_funcionarios = data.get('funcionarios', []) 
    ids_setores = data.get('setores', [])           
    ids_cargos = data.get('cargos', [])             
    ids_tipos_doc = data.get('documentos', [])
    ids_aprovadores = data.get('aprovadores', [])

    if not titulo or not ids_tipos_doc:
        return jsonify({'success': False, 'message': 'Título e documentos são obrigatórios.'}), 400

    # --- 1. IDENTIFICAR O PÚBLICO ALVO ---
    destinatarios_finais = set()

    if mode == 'individual':
        for uid in ids_funcionarios:
            destinatarios_finais.add(int(uid))     
    elif mode == 'lote':
        query = Funcionario.query.filter_by(status='Ativo')
        filtros_aplicados = False
        if ids_setores:
            query = query.filter(Funcionario.setor_id.in_(ids_setores))
            filtros_aplicados = True
        if ids_cargos:
            query = query.filter(Funcionario.cargo_id.in_(ids_cargos))
            filtros_aplicados = True
        if not filtros_aplicados:
            return jsonify({'success': False, 'message': 'No modo lote, selecione ao menos um Setor ou Cargo.'}), 400
        candidatos = query.all()
        for f in candidatos:
            destinatarios_finais.add(f.id)

    if not destinatarios_finais:
        return jsonify({'success': False, 'message': 'Nenhum funcionário encontrado.'}), 400

    try:
        # --- 2. CRIAR ESTRUTURA NO BANCO ---
        
        nova_solicitacao = Solicitacao(
            titulo=titulo,
            descricao=descricao,
            solicitante_id=current_user.id,
            status_geral='Aberta',
            recorrente=recorrente
        )

        if recorrente and data_base_str and intervalo:
            nova_solicitacao.data_base = datetime.strptime(data_base_str, '%Y-%m-%d').date()
            nova_solicitacao.intervalo_dias = int(intervalo)
            nova_solicitacao.ativa = True
        
        db.session.add(nova_solicitacao)
        db.session.flush()

        # Workflow de Aprovação
        for aprovador_id in ids_aprovadores:
            if aprovador_id:
                aprov_link = SolicitacaoAprovador(
                    solicitacao_id=nova_solicitacao.id,
                    aprovador_id=int(aprovador_id)
                )
                db.session.add(aprov_link)

        # Requisições Individuais
        count_reqs = 0
        for func_id in destinatarios_finais:
            for doc_type_id in ids_tipos_doc:
                existe = RequisicaoDocumento.query.filter_by(
                    destinatario_id=func_id,
                    tipo_documento_id=int(doc_type_id),
                    status='Pendente'
                ).first()
                
                if not existe:
                    req = RequisicaoDocumento(
                        solicitacao_id=nova_solicitacao.id,
                        tipo_documento_id=int(doc_type_id),
                        destinatario_id=func_id,
                        solicitante_id=current_user.id,
                        status='Pendente',
                        observacoes_rh=descricao 
                    )
                    db.session.add(req)
                    count_reqs += 1
        
        db.session.commit()
        registrar_log(f"Criou solicitação '{titulo}' (Recorrente: {recorrente}) para {len(destinatarios_finais)} colaboradores.")
        return jsonify({'success': True, 'message': f'Sucesso! {count_reqs} solicitações geradas.'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao criar solicitação: {e}")
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500

# --- ROTAS API: RESPONDER (MULTI-UPLOAD) ---

@documentos_bp.route('/requisicao/<int:req_id>/responder', methods=['POST'])
@login_required
def responder_requisicao(req_id):
    requisicao = RequisicaoDocumento.query.get_or_404(req_id)
    if requisicao.destinatario_id != current_user.funcionario.id:
        return jsonify({'success': False, 'message': 'Acesso não autorizado.'}), 403
    
    # SUPORTE A MÚLTIPLOS ARQUIVOS
    files = request.files.getlist('arquivo') # Pega lista de arquivos
    if not files or files[0].filename == '':
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado.'}), 400

    try:
        count_saved = 0
        for file in files:
            if file and allowed_file(file.filename):
                filename_seguro = secure_filename(file.filename)
                extensao = filename_seguro.rsplit('.', 1)[1]
                nome_unico = f"{uuid.uuid4()}.{extensao}"
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'])
                file.save(os.path.join(upload_path, nome_unico))

                novo_documento = Documento(
                    nome_arquivo=filename_seguro,
                    tipo_documento=requisicao.tipo.nome,
                    path_armazenamento=nome_unico,
                    funcionario_id=current_user.funcionario.id,
                    requisicao_id=requisicao.id,
                    status='Pendente de Aprovação'
                )
                db.session.add(novo_documento)
                db.session.flush()

                # Lógica de Workflow para CADA documento
                if requisicao.solicitacao_pai:
                    aprovadores = requisicao.solicitacao_pai.aprovadores_previstos.all()
                    if aprovadores:
                        for ap in aprovadores:
                            tarefa = DocumentoAprovacao(
                                documento_id=novo_documento.id,
                                aprovador_id=ap.aprovador_id,
                                status='Pendente'
                            )
                            db.session.add(tarefa)
                    else:
                        novo_documento.status = 'Pendente de Revisão'
                else:
                    novo_documento.status = 'Pendente de Revisão'
                
                count_saved += 1

        if count_saved > 0:
            requisicao.status = 'Em Revisão' # Atualiza status da requisição pai
            requisicao.observacao = None
            db.session.commit()
            return jsonify({'success': True, 'message': f'{count_saved} arquivos enviados com sucesso!'})
        else:
            return jsonify({'success': False, 'message': 'Nenhum arquivo válido.'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# --- ROTAS API: APROVAÇÃO / REPROVAÇÃO ---

@documentos_bp.route('/api/aprovar-documento/<int:doc_id>', methods=['POST'])
@login_required
def api_aprovar_documento(doc_id):
    documento = Documento.query.get_or_404(doc_id)
    aprovacao_pendente = DocumentoAprovacao.query.filter_by(documento_id=doc_id, aprovador_id=current_user.id, status='Pendente').first()
    is_super_admin = current_user.tem_permissao(['admin_rh', 'admin_ti'])

    if not aprovacao_pendente and not is_super_admin and documento.status != 'Pendente de Revisão':
        return jsonify({'success': False, 'message': 'Sem permissão ou nada a aprovar.'}), 403

    try:
        if aprovacao_pendente:
            aprovacao_pendente.status = 'Aprovado'
            aprovacao_pendente.data_acao = datetime.utcnow()
        
        # Verifica se TODOS aprovaram
        todas = DocumentoAprovacao.query.filter_by(documento_id=doc_id).all()
        todos_aprovaram = all(a.status == 'Aprovado' for a in todas)
        
        if (todas and todos_aprovaram) or is_super_admin:
            documento.status = 'Aprovado'
            documento.data_revisao = datetime.utcnow()
            documento.revisor_id = current_user.id
            if documento.requisicao:
                documento.requisicao.status = 'Concluído'
                documento.requisicao.data_conclusao = datetime.utcnow()
            msg = "Aprovado e Finalizado."
        else:
            msg = "Aprovado (Aguardando demais aprovadores)."
        
        db.session.commit()
        return jsonify({'success': True, 'message': msg})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@documentos_bp.route('/api/rejeitar-documento/<int:doc_id>', methods=['POST'])
@login_required
def api_rejeitar_documento(doc_id):
    documento = Documento.query.get_or_404(doc_id)
    motivo = request.get_json().get('motivo')
    if not motivo: return jsonify({'success': False, 'message': 'Motivo obrigatório'}), 400
    
    aprovacao_pendente = DocumentoAprovacao.query.filter_by(documento_id=doc_id, aprovador_id=current_user.id).first()
    is_super_admin = current_user.tem_permissao(['admin_rh', 'admin_ti'])
    
    if not aprovacao_pendente and not is_super_admin:
        return jsonify({'success': False, 'message': 'Sem permissão.'}), 403

    try:
        if aprovacao_pendente:
            aprovacao_pendente.status = 'Rejeitado'
            aprovacao_pendente.observacao = motivo
            aprovacao_pendente.data_acao = datetime.utcnow()
        
        documento.status = 'Rejeitado'
        if documento.requisicao:
            documento.requisicao.status = 'Rejeitado' # Usar status Rejeitado na req também para aparecer vermelho no front
            documento.requisicao.observacoes_rh = f"Rejeitado por {current_user.funcionario.nome}: {motivo}"
            
        db.session.commit()
        return jsonify({'success': True, 'message': 'Documento rejeitado.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# --- NOVAS ROTAS: CANCELAMENTO E PARAR RECORRÊNCIA ---

@documentos_bp.route('/api/solicitacao/<int:sol_id>/cancelar', methods=['POST'])
@login_required
@permission_required(PERMISSOES_DOCS)
def cancelar_solicitacao(sol_id):
    """Cancela uma solicitação específica (Requisição)"""
    # Como o front manda o ID da requisicao (req_id), carregamos a requisição
    req = RequisicaoDocumento.query.get_or_404(sol_id)
    
    try:
        req.status = 'Cancelado'
        docs = Documento.query.filter_by(requisicao_id=req.id).all()
        for d in docs:
            d.status = 'Cancelado'
            
        db.session.commit()
        return jsonify({'success': True, 'message': 'Solicitação cancelada.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@documentos_bp.route('/api/solicitacao/<int:sol_id>/parar-recorrencia', methods=['POST'])
@login_required
@permission_required(PERMISSOES_DOCS)
def parar_recorrencia(sol_id):
    """Para a recorrência de uma solicitação PAI."""
    sol = Solicitacao.query.get_or_404(sol_id)
    if not sol.recorrente:
        return jsonify({'success': False, 'message': 'Esta solicitação não é recorrente.'}), 400
        
    try:
        sol.ativa = False
        db.session.commit()
        return jsonify({'success': True, 'message': 'Recorrência interrompida com sucesso.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@documentos_bp.route('/download/<path:filename>')
@login_required
def download_documento(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# --- ROTAS LEGADAS (MANTIDAS) ---
@documentos_bp.route('/tipos', methods=['GET', 'POST'])
@login_required
def gerenciar_tipos_documento():
    form = TipoDocumentoForm()
    if form.validate_on_submit():
        db.session.add(TipoDocumento(nome=form.nome.data, descricao=form.descricao.data, obrigatorio_na_admissao=form.obrigatorio_na_admissao.data))
        db.session.commit()
        return redirect(url_for('documentos.gerenciar_tipos_documento'))
    return render_template('documentos/gerenciar_tipos.html', form=form, tipos=TipoDocumento.query.all())

@documentos_bp.route('/tipos/<int:id>/editar', methods=['POST'])
@login_required
def editar_tipo_documento(id): return redirect(url_for('documentos.gerenciar_tipos_documento'))

@documentos_bp.route('/tipos/<int:id>/deletar', methods=['POST'])
@login_required
def deletar_tipo_documento(id): return redirect(url_for('documentos.gerenciar_tipos_documento'))

@documentos_bp.route('/solicitar-em-lote', methods=['POST'])
@login_required
def solicitar_em_lote(): return redirect(url_for('documentos.gestao_documentos'))

@documentos_bp.route('/upload-manual', methods=['POST'])
@login_required
def upload_manual_documento(): return redirect(url_for('documentos.gestao_documentos'))

@documentos_bp.route('/api/funcionario/<int:funcionario_id>/documentos')
@login_required
def historico_documentos_funcionario(funcionario_id): return jsonify([])

@documentos_bp.route('/funcionario/<int:funcionario_id>')
@login_required
@permission_required(['admin_rh', 'depto_pessoal'])
def ver_documentos_funcionario(funcionario_id):
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    requisicoes_pendentes = RequisicaoDocumento.query.filter_by(
        destinatario_id=funcionario.id, status='Pendente'
    ).order_by(RequisicaoDocumento.data_requisicao.desc()).all()
    return render_template('documentos/ver_documentos.html', funcionario=funcionario, pendentes=requisicoes_pendentes)

@documentos_bp.route('/funcionario/<int:funcionario_id>/solicitar', methods=['POST'])
@login_required
@permission_required(['admin_rh', 'depto_pessoal'])
def solicitar_documento(funcionario_id):
    return redirect(url_for('documentos.ver_documentos_funcionario', funcionario_id=funcionario_id))

@documentos_bp.route('/funcionario/<int:funcionario_id>/upload', methods=['POST'])
@login_required
@permission_required(['admin_rh', 'depto_pessoal'])
def upload_documento(funcionario_id):
    return redirect(url_for('documentos.ver_documentos_funcionario', funcionario_id=funcionario_id))

@documentos_bp.route('/requisicao/<int:req_id>/remover', methods=['POST'])
@login_required
@permission_required(['admin_rh', 'depto_pessoal'])
def remover_requisicao(req_id):
    requisicao = RequisicaoDocumento.query.get_or_404(req_id)
    funcionario_id = requisicao.destinatario_id
    db.session.delete(requisicao)
    db.session.commit()
    return redirect(url_for('documentos.ver_documentos_funcionario', funcionario_id=funcionario_id))

@documentos_bp.route('/api/documento/<int:documento_id>/remover', methods=['DELETE'])
@login_required
@permission_required(['admin_rh', 'depto_pessoal'])
def remover_documento_api(documento_id):
    documento = Documento.query.get_or_404(documento_id)
    db.session.delete(documento)
    db.session.commit()
    return jsonify({'success': True})