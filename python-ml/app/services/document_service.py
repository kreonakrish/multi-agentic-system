from typing import Dict, Any, List
from werkzeug.datastructures import FileStorage
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import logger
import os
from datetime import datetime
import json

def get_all_documents() -> Dict[str, Any]:
    """Get all documents from the database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM documents ORDER BY created_at DESC")
        documents = cursor.fetchall()
        return {
            'status': 'success',
            'documents': documents
        }
    except Exception as e:
        logger.error(f"Error in get_all_documents: {str(e)}", exc_info=True)
        raise
    finally:
        safe_close_connection(conn)

def get_document(document_id: int) -> Dict[str, Any]:
    """Get a specific document by ID"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
        document = cursor.fetchone()
        if not document:
            return {
                'status': 'error',
                'message': f'Document {document_id} not found'
            }, 404
        return {
            'status': 'success',
            'document': document
        }
    except Exception as e:
        logger.error(f"Error in get_document: {str(e)}", exc_info=True)
        raise
    finally:
        safe_close_connection(conn)

def create_document(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new document in the database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Extract fields from data
        name = data.get('name')
        team_id = data.get('team_id')
        conversation_id = data.get('conversation_id')
        doc_type = data.get('type', 'unknown')
        content = data.get('content')
        metadata = data.get('metadata', {})
        
        # Insert document
        cursor.execute("""
            INSERT INTO documents (name, team_id, conversation_id, type, content, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, team_id, conversation_id, doc_type, content, json.dumps(metadata)))
        
        document_id = cursor.lastrowid
        conn.commit()
        
        # Get the created document
        cursor.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
        document = cursor.fetchone()
        
        return {
            'status': 'success',
            'message': 'Document created successfully',
            'document': document
        }
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in create_document: {str(e)}", exc_info=True)
        raise
    finally:
        safe_close_connection(conn)

def update_document(document_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a document in the database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if document exists
        cursor.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
        if not cursor.fetchone():
            return {
                'status': 'error',
                'message': f'Document {document_id} not found'
            }, 404
        
        # Build update query dynamically based on provided fields
        update_fields = []
        params = []
        for key, value in data.items():
            if key in ['name', 'team_id', 'conversation_id', 'type', 'content']:
                update_fields.append(f"{key} = %s")
                params.append(value)
            elif key == 'metadata':
                update_fields.append("metadata = %s")
                params.append(json.dumps(value))
        
        params.append(document_id)
        update_query = f"""
            UPDATE documents 
            SET {', '.join(update_fields)}
            WHERE id = %s
        """
        
        cursor.execute(update_query, tuple(params))
        conn.commit()
        
        # Get updated document
        cursor.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
        document = cursor.fetchone()
        
        return {
            'status': 'success',
            'message': 'Document updated successfully',
            'document': document
        }
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in update_document: {str(e)}", exc_info=True)
        raise
    finally:
        safe_close_connection(conn)

def delete_document(document_id: int) -> Dict[str, Any]:
    """Delete a document from the database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if document exists
        cursor.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
        document = cursor.fetchone()
        if not document:
            return {
                'status': 'error',
                'message': f'Document {document_id} not found'
            }, 404
        
        # Delete document
        cursor.execute("DELETE FROM documents WHERE id = %s", (document_id,))
        conn.commit()
        
        return {
            'status': 'success',
            'message': 'Document deleted successfully'
        }
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in delete_document: {str(e)}", exc_info=True)
        raise
    finally:
        safe_close_connection(conn)

def upload_document(file: FileStorage, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Upload a document file and store its information"""
    conn = None
    try:
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(os.getcwd(), 'uploads', 'documents')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        filename = file.filename
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Get file info
        file_size = os.path.getsize(file_path)
        file_type = file.content_type or 'application/octet-stream'
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Insert document record
        cursor.execute("""
            INSERT INTO documents (
                name, team_id, conversation_id, type,
                size, file_type, file_size, file_path,
                metadata, uploaded_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            filename,
            metadata.get('team_id'),
            metadata.get('conversation_id'),
            metadata.get('type', 'file'),
            file_size,
            file_type,
            file_size,
            file_path,
            json.dumps(metadata),
            datetime.now()
        ))
        
        document_id = cursor.lastrowid
        conn.commit()
        
        # Get created document
        cursor.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
        document = cursor.fetchone()
        
        return {
            'status': 'success',
            'message': 'Document uploaded successfully',
            'document': document
        }
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in upload_document: {str(e)}", exc_info=True)
        raise
    finally:
        safe_close_connection(conn)

def get_document_content(document_id: int) -> Dict[str, Any]:
    """Get the content of a document"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get document
        cursor.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
        document = cursor.fetchone()
        
        if not document:
            return {
                'status': 'error',
                'message': f'Document {document_id} not found'
            }, 404
            
        # If it's a file, read its content
        if document.get('file_path'):
            try:
                with open(document['file_path'], 'r') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading file content: {str(e)}", exc_info=True)
                content = None
        else:
            content = document.get('content')
            
        return {
            'status': 'success',
            'content': content,
            'document': document
        }
    except Exception as e:
        logger.error(f"Error in get_document_content: {str(e)}", exc_info=True)
        raise
    finally:
        safe_close_connection(conn) 