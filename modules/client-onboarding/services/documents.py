"""
Document Upload Service for Client Onboarding

Handles file uploads for KYC documents, storing them in Google Drive
or locally in demo mode.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}

# Demo mode storage
DEMO_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
_demo_documents: List[Dict] = []


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_document(
    file,
    onboarding_id: str,
    document_type: str,
    uploaded_by: str = 'system'
) -> Dict[str, Any]:
    """
    Upload a document for an onboarding.

    Args:
        file: Flask FileStorage object
        onboarding_id: ID of the onboarding
        document_type: Type of document (e.g., 'id_proof', 'address_proof', 'corporate_doc')
        uploaded_by: Username of uploader

    Returns:
        Dict with upload status and document metadata
    """
    if not file or not file.filename:
        return {'status': 'error', 'message': 'No file provided'}

    if not allowed_file(file.filename):
        return {'status': 'error', 'message': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'}

    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    stored_filename = f"{onboarding_id}_{document_type}_{timestamp}_{filename}"

    # Create document record
    doc_record = {
        'document_id': f"DOC-{timestamp}-{onboarding_id[:8]}",
        'onboarding_id': onboarding_id,
        'document_type': document_type,
        'original_filename': filename,
        'stored_filename': stored_filename,
        'uploaded_by': uploaded_by,
        'uploaded_at': datetime.now().isoformat(),
        'file_size': 0,
        'storage_location': 'demo'
    }

    # Try Google Drive upload first
    try:
        from services.gdrive_audit import upload_file, DEMO_MODE as GDRIVE_DEMO_MODE

        if not GDRIVE_DEMO_MODE:
            # Save temp file for GDrive upload
            temp_path = os.path.join('/tmp', stored_filename)
            file.save(temp_path)
            doc_record['file_size'] = os.path.getsize(temp_path)

            # Upload to Drive
            drive_result = upload_file(
                temp_path,
                folder_name=f"onboarding_{onboarding_id}",
                filename=stored_filename
            )

            os.remove(temp_path)  # Clean up temp file

            if drive_result.get('status') == 'success':
                doc_record['storage_location'] = 'gdrive'
                doc_record['gdrive_file_id'] = drive_result.get('file_id')
                logger.info(f"Document uploaded to GDrive: {stored_filename}")
            else:
                raise Exception(drive_result.get('message', 'GDrive upload failed'))
        else:
            raise Exception("GDrive in demo mode")

    except Exception as e:
        logger.info(f"GDrive unavailable ({e}), using local storage")

        # Fall back to local storage (demo mode)
        os.makedirs(DEMO_UPLOAD_FOLDER, exist_ok=True)
        local_path = os.path.join(DEMO_UPLOAD_FOLDER, stored_filename)
        file.save(local_path)
        doc_record['file_size'] = os.path.getsize(local_path)
        doc_record['storage_location'] = 'local'
        doc_record['local_path'] = local_path

    # Store document record
    _demo_documents.append(doc_record)

    logger.info(f"Document uploaded: {doc_record['document_id']} for {onboarding_id}")

    return {
        'status': 'success',
        'message': 'Document uploaded successfully',
        'document': doc_record
    }


def get_documents(onboarding_id: str) -> List[Dict]:
    """Get all documents for an onboarding."""
    return [d for d in _demo_documents if d['onboarding_id'] == onboarding_id]


def get_document(document_id: str) -> Optional[Dict]:
    """Get a specific document by ID."""
    for doc in _demo_documents:
        if doc['document_id'] == document_id:
            return doc
    return None


def delete_document(document_id: str) -> Dict[str, Any]:
    """Delete a document."""
    global _demo_documents

    doc = get_document(document_id)
    if not doc:
        return {'status': 'error', 'message': 'Document not found'}

    # Delete from storage
    if doc.get('storage_location') == 'local' and doc.get('local_path'):
        try:
            os.remove(doc['local_path'])
        except OSError:
            pass

    # Remove from records
    _demo_documents = [d for d in _demo_documents if d['document_id'] != document_id]

    return {'status': 'success', 'message': 'Document deleted'}


# Document type labels
DOCUMENT_TYPES = {
    'id_proof': 'ID Proof (Passport/Driving License)',
    'address_proof': 'Address Proof',
    'source_of_wealth': 'Source of Wealth',
    'corporate_doc': 'Corporate Documentation',
    'bank_reference': 'Bank Reference',
    'source_of_funds': 'Source of Funds Declaration',
    'other': 'Other Document'
}
