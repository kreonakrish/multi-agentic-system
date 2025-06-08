from flask import Blueprint, request, jsonify
from app.services.document_service import (
    get_all_documents,
    get_document,
    create_document,
    update_document,
    delete_document,
    upload_document,
    get_document_content
)
from app.utils.decorators import log_execution
from app.utils.logger import logger
from typing import Dict, Any

# Create blueprint with url_prefix
bp = Blueprint('document', __name__, url_prefix='/api/ml/documents')

@bp.route('/', methods=['GET'])
@log_execution
def get_documents_route():
    """Get all documents"""
    try:
        result = get_all_documents()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_documents route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get documents: {str(e)}'
        }), 500

@bp.route('/<int:document_id>', methods=['GET'])
@log_execution
def get_document_route(document_id: int):
    """Get a specific document by ID"""
    try:
        result = get_document(document_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_document route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get document: {str(e)}'
        }), 500

@bp.route('/', methods=['POST'])
@log_execution
def create_document_route():
    """Create a new document"""
    try:
        data = request.get_json()
        result = create_document(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in create_document route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to create document: {str(e)}'
        }), 500

@bp.route('/<int:document_id>', methods=['PUT'])
@log_execution
def update_document_route(document_id: int):
    """Update a document"""
    try:
        data = request.get_json()
        result = update_document(document_id, data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in update_document route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to update document: {str(e)}'
        }), 500

@bp.route('/<int:document_id>', methods=['DELETE'])
@log_execution
def delete_document_route(document_id: int):
    """Delete a document"""
    try:
        result = delete_document(document_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in delete_document route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to delete document: {str(e)}'
        }), 500

@bp.route('/upload', methods=['POST'])
@log_execution
def upload_document_route():
    """Upload a new document file"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file part in the request'
            }), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No selected file'
            }), 400
            
        metadata = request.form.to_dict()
        result = upload_document(file, metadata)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in upload_document route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to upload document: {str(e)}'
        }), 500

@bp.route('/<int:document_id>/content', methods=['GET'])
@log_execution
def get_document_content_route(document_id: int):
    """Get the content of a document"""
    try:
        result = get_document_content(document_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_document_content route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get document content: {str(e)}'
        }), 500 